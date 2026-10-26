"""push_collect.py — P2 first-class collect instrument for the WP1-③a push task.

Sibling of collect.py (P1 reach/L2), NEVER integrated back into it. Equivalence
with collect.py is audited in docs/p2_prereg/dual_collect_equivalence_ledger.md.

Observation rule (PI ruling 2026-10-05): the model sees IMAGE +
PROPRIOCEPTION only (stage-1 state = TCP grid + disclosed scaffold block of
the env's push_obs_rung). GT cube/goal is read here ONLY for the success
predicate and offline records (round_meta, replay metadata).

Rung 1b/2/3 (PI 2026-10-06) add a fixed top-down image after the front image
every round (extra_image_bytes), and Pin-12: the plateau counter arms only
after first contact.

Loop per round:
  RGB (+ top view) + proprio state → run_stage1_eef (teacher emits a left-TCP target:
    LEFT_TARGET_POS + optional LEFT_TARGET_ORI — A-spec v2)
  → de-normalize int→base-frame metric (TCP target); orientation =
    push_body.command_quat(q_rest, ORI): the live rest (Pin-7a standby)
    orientation rotated about BASE axes — nothing motion-dependent
  → iface.execute_push_segment(target_is_tcp=True) (TCP→hand with the live
    offset; OSC servo + τ monitor + ori error + contact report)
  → record round → Pin-11 termination → next round
End: shared _write_episode (+ push init fields/metadata) + push recap.

Memory (WP1-③a pilot step (c)): push_memory.PushMemoryRetriever = shared
RecapBuffer.retrieve keyed on DINOv2(start image) + init TCP, rung-gated
push preamble; injected on ROUND 1 ONLY via a fresh EpisodeConversation
(rounds 2+ stay stateless, as before). Post-episode recap →
push_memory.emit_push_recap (rung-gated prompt) → shared RecapBuffer.

Shared substrate imported (NOT copied): collect_common._write_episode (via
push_memory), ReplayBuffer, schema, RecapBuffer/RecapRecord, the DINOv2
embedder and retriever helpers. Push-specific: the loop glue, the success
predicate (cube displacement, not EE distance), and the push memory glue
(push_memory.py; every deviation ledgered).
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Optional

import numpy as np

from aiongenos.config import LevelConfig, WorkspaceBounds
from aiongenos.pipeline.stage1_reasoning import run_stage1_eef
from aiongenos.vlm.client import EpisodeConversation
from aiongenos.vlm.prompts import get_stage1_system_prompt
from aiongenos.vlm.scalar_guard import int_to_metric
from aiongenos.replay.buffer import ReplayBuffer
from aiongenos.replay.schema import EpisodeOutcome
from aiongenos.orchestrator import push_memory as pm
from aiongenos.orchestrator import push_body as pb
from aiongenos.orchestrator.push_feedback import format_round_feedback

logger = logging.getLogger(__name__)

# Pin-11 (sealed): success = cube within this of goal; round cap; plateau rule.
PUSH_SUCCESS_M = 0.05
PUSH_ROUND_CAP = 12
PUSH_PLATEAU_ROUNDS = 3
PUSH_PLATEAU_MIN_DISP_M = 0.01
# Env time-limit guard (ledger item 15): the inherited env timed out at 720 steps
# and IsaacLab auto-reset INSIDE env.step mid-episode. The env's own episode
# budget must exceed the push round budget by this margin.
PUSH_EP_LEN_MARGIN = 1.5
ORI_ERR_TAIL_STEPS = 20
# Pin-12 (PI 2026-10-06): from rung 1b on, the plateau counter ARMS only after
# first contact (a round whose contact report saw the cube start moving, or
# whose cube displacement ≥ PUSH_PLATEAU_MIN_DISP_M). Before that, rounds count
# only toward PUSH_ROUND_CAP. Rung 1 keeps the rule it was piloted under
# (armed from round 1).
PIN12_EXEMPT_RUNGS = frozenset({"1"})


def _plateau_arms_after_contact(obs_rung) -> bool:
    return pm.norm_rung(obs_rung) not in PIN12_EXEMPT_RUNGS


def _round_touched(contact: dict, cube_disp_m: float) -> bool:
    return contact.get("first_cube_move") is not None or cube_disp_m >= PUSH_PLATEAU_MIN_DISP_M   # ori_err max over the segment's last N steps (settled error)


def _env_unwrapped(env):
    """IsaacLabEnvInterface wraps the gym env as .env; .unwrapped is the
    ManagerBasedRLEnv carrying max_episode_length / episode_length_buf."""
    return getattr(env, "env", env).unwrapped


def _check_episode_budget(env, steps_per_segment: int) -> None:
    need = PUSH_ROUND_CAP * steps_per_segment * PUSH_EP_LEN_MARGIN
    try:
        mel = int(_env_unwrapped(env).max_episode_length)
    except Exception as e:
        raise RuntimeError(f"push_collect: cannot read env max_episode_length ({e}); "
                           f"refusing to run without the auto-reset budget check") from e
    if mel <= need:
        raise RuntimeError(
            f"push_collect: env max_episode_length={mel} steps <= required "
            f"{need:.0f} (= PUSH_ROUND_CAP {PUSH_ROUND_CAP} x steps_per_segment "
            f"{steps_per_segment} x {PUSH_EP_LEN_MARGIN}); IsaacLab would auto-reset "
            f"mid-episode. Raise episode_length_s in the push env cfg.")


def _episode_step_count(env) -> Optional[int]:
    try:
        return int(_env_unwrapped(env).episode_length_buf[0])
    except Exception:
        return None


def _make_eef_vlm_interaction(response, latency_ms: float):
    """VLMInteraction for the EEF push response (A-spec v2). Adapts to the SAME
    VLMInteraction schema: EEF target POS in the left-pos slot, ORI offset in
    the left-rpy slot (None → rest orientation), thought in full_response. A push-shaped
    shim, not a schema change — replay/recap consume it identically."""
    from aiongenos.replay.schema import VLMInteraction
    ori = response.target_ori
    return VLMInteraction(
        stage="stage1_eef",
        full_response=getattr(response, "thought", ""),
        parsed_left_pos=(response.target_pos.x, response.target_pos.y, response.target_pos.z),
        parsed_right_pos=(0, 0, 0),
        parsed_left_rpy=((ori.r, ori.p, ori.y) if ori is not None else None),
        parsed_right_rpy=None,
        parsed_left_gripper=response.grip,
        parsed_right_gripper=None,
        parsed_stop=response.stop,
        latency_ms=latency_ms,
    )


def run_push_collect_loop(
    env,                      # IsaacLabEnvInterface (push env)
    level_config: LevelConfig,
    teacher_url: str,
    replay: ReplayBuffer,
    num_episodes: int,
    env_seed_base: Optional[int] = None,
    episode_label: str = "pilot",   # pilot (smoke) | confirmatory (gen-0)
    recap_buffer: Optional[object] = None,
    steps_per_segment: int = 90,
    gif_frame_every: int = 0,   # >0: collect RGB frames every N steps → summary["gif_frames"]
    memory_retriever: Optional[object] = None,   # push_memory.PushMemoryRetriever
    recap_buffer_readonly: bool = False,         # read memory, never write recaps (collect.py gate)
    dump_images_root: Optional[Path] = None,     # {root}/{run_id}/{ep_id}/ round PNGs + meta.json
    round_feedback: bool = False,                # rung-2' (PI 2026-10-15): report of round r-1 in round r
    round_history: bool = False,                 # rung-2' full P1 condition: one EpisodeConversation per episode
    frame_convention: bool = False,              # d1 (PI 2026-10-22): frame convention line in stage-1 prompt
    verdict_contact_switch: bool = False,        # d2 (PI 2026-10-22): contact-switched P1 verdict
    geometry: str = "pin4b",                     # Pin-4b (default) or Pin-4c
    preamble_coords: str = "on",                 # Push preamble coords: on (default) or off
    scripted_targets: Optional[Sequence[Sequence[int]]] = None,  # Scripted blind-sweep mode
) -> dict:
    """Drive `num_episodes` push episodes. Returns a summary dict.

    Seed convention IDENTICAL to collect.py: env_seed_base + ep_idx (None →
    nondeterministic). Per-round records carry the push primitive's 3 numbers
    (requested/clamped disp, was_clamped) + the τ monitor summary."""
    _check_episode_budget(env, steps_per_segment)
    # disclosed-scaffold rung lives on the env (it shapes get_state); read it
    # once here so every record states which rung its data came from
    obs_rung = pm.norm_rung(env.push_obs_rung)
    top_view = pm.has_top_view(obs_rung)          # rung 1b/2/3: + fixed top-down camera
    pin12 = _plateau_arms_after_contact(obs_rung)
    # rung-2': the feedback shows the two distances only where the rung shows them
    fb_scalars = round_feedback and pm.oracle_level(obs_rung) >= 2
    if memory_retriever is not None and pm.norm_rung(memory_retriever.obs_rung) != obs_rung:
        raise RuntimeError(f"push_collect: retriever obs_rung={memory_retriever.obs_rung} "
                           f"!= env push_obs_rung={obs_rung}")
    bounds = level_config.workspace_bounds
    if hasattr(env, "push_frame_convention"):
        env.push_frame_convention = frame_convention
    from aiongenos.vlm.prompts import format_frame_convention_line
    frame_line = format_frame_convention_line(bounds) if frame_convention else None
    run_id = ReplayBuffer.new_run_id()
    logger.info(f"push_collect run_id={run_id} episodes={num_episodes} label={episode_label} obs_rung={obs_rung}")
    summary = {"run_id": run_id, "label": episode_label, "obs_rung": obs_rung, "episodes": [],
               "n_success": 0, "memory_on": memory_retriever is not None and scripted_targets is None,
               "top_view": top_view, "plateau_rule": "pin12_after_contact" if pin12 else "pin11_from_round1",
               "round_feedback": round_feedback, "round_history": round_history,
               "frame_convention": frame_convention, "verdict_contact_switch": verdict_contact_switch,
               "frame_line": frame_line,
               "geometry": geometry, "preamble_coords": preamble_coords,
               "scripted_policy": bool(scripted_targets is not None)}
    gif_frames = []   # PNG bytes across the run (if gif_frame_every>0)

    for ep_idx in range(num_episodes):
        ep_seed = None if env_seed_base is None else env_seed_base + ep_idx
        ep_id = ReplayBuffer.new_episode_id()
        ep_start = time.time()
        env.reset(seed=ep_seed)
        rgb_start = env.get_rgb()
        ep_dump_dir = pm.episode_dump_dir(dump_images_root, run_id, ep_id)
        pm.dump_png(ep_dump_dir, "episode_start.png", rgb_start)
        if top_view:
            rgb_start_top = env.get_rgb_top()
            if not rgb_start_top:
                raise RuntimeError(f"push_collect: obs_rung {obs_rung} needs the top-down camera "
                                   f"but get_rgb_top() is empty — build the TopCam env id")
            pm.dump_png(ep_dump_dir, "episode_start_top.png", rgb_start_top)
        # Reset-time snapshot (after reset, before any servo): init TCP
        # (proprio: retrieval key, recap) + GT cube/goal (offline records).
        init_snap = pm.snapshot_push_state(env, level_config)
        # Rest orientation = the live Pin-7a standby hand orientation; the
        # ONLY orientation source besides the teacher's ORI offset.
        q_rest = env.get_left_hand_quat_b()

        trajectory = []
        vlm_interactions = []
        flags = [f"label:{episode_label}"]
        if scripted_targets is not None:
            flags.append("scripted_policy")
        round_meta = []
        outcome = EpisodeOutcome.TIMEOUT
        plateau_count = 0
        # Pin-12: rung-1 armed from round 1 (pilot rule); 1b+ armed at first contact
        plateau_armed_round: Optional[int] = None if pin12 else 1
        cube0_b = env.get_cube_pose_b()
        last_step_count = _episode_step_count(env)   # auto-reset detector (ledger 15)
        auto_reset = False
        round_touched: list[bool] = []

        # Memory: retrieve once at ep start (query = start RGB + init TCP);
        # within-run retrieval allowed (this ep's recap does not exist yet).
        memory_text: Optional[str] = None
        memory_imgs: Optional[list[str]] = None
        memory_hits: list[dict] = []
        preamble_coord_redactions = 0
        if memory_retriever is not None and rgb_start and scripted_targets is None:
            try:
                pre = memory_retriever.retrieve_for_episode(rgb_start, init_snap.tcp_int)
                preamble_coord_redactions = getattr(pre, "preamble_coord_redactions", 0)
                if not pre.is_empty:
                    memory_text, memory_imgs = pre.prelude_text, pre.past_image_base64_list
                    memory_hits = [{"ep_id": r.ep_id, "run_id": r.run_id, "score": round(s, 4),
                                    "outcome": r.outcome, "lesson": r.text_lesson}
                                   for r, s in zip(pre.retrieved_records, pre.similarities)]
                    hit_ids = ",".join(h["ep_id"][:8] for h in memory_hits)
                    hit_scores = ",".join(f"{h['score']:.2f}" for h in memory_hits)
                    logger.info(f"  ep{ep_idx} memory: injected {len(memory_hits)} past eps "
                                f"[{hit_ids}] scores=[{hit_scores}]")
                else:
                    logger.info(f"  ep{ep_idx} memory: buffer empty or all filtered, no preamble")
            except Exception as e:
                logger.warning(f"  ep{ep_idx} memory retrieval failed (continuing without): {e}")

        prev_fb = None   # (target_int, tcp_start_int, scalars_cm or None) of the previous round
        max_rounds = len(scripted_targets) if scripted_targets is not None else PUSH_ROUND_CAP
        for round_idx in range(max_rounds):
            rgb = env.get_rgb()
            pm.dump_png(ep_dump_dir, f"round_{round_idx + 1:02d}_pre.png", rgb)
            rgb_top = env.get_rgb_top() if top_view else b""
            pm.dump_png(ep_dump_dir, f"round_{round_idx + 1:02d}_pre_top.png", rgb_top)
            state = env.get_state(level_config)
            pre_snap = pm.snapshot_push_state(env, level_config, state)
            cube_quat_b_pre = env.get_cube_quat_b() if hasattr(env, "get_cube_quat_b") else [1.0, 0.0, 0.0, 0.0]
            scalars_now = (tuple(round(v * 100, 1) for v in env.push_scalars_m()) if fb_scalars else None)
            critic_feedback = None
            verdict_metric = None
            if round_feedback and prev_fb is not None:
                contact_strictly_before = any(round_touched[:round_idx - 1])
                if fb_scalars:
                    verdict_metric = ("cube_goal" if contact_strictly_before else "tip_cube") if verdict_contact_switch else "cube_goal"
                critic_feedback = format_round_feedback(
                    prev_fb[0], prev_fb[1], pre_snap.tcp_int,
                    prev_fb[2], scalars_now,
                    verdict_metric=(verdict_metric if verdict_contact_switch else None),
                )
            # inject instruction (get_state doesn't; collect.py does the same
            # from task_instruction_template) — the PUSH prompt has {instruction}
            state["instruction"] = level_config.task_instruction_template

            if scripted_targets is not None:
                from aiongenos.vlm.parser import EEFStage1Response, PositionTarget
                st_tgt = scripted_targets[round_idx]
                parsed = EEFStage1Response(
                    thought="[scripted_policy]",
                    target_pos=PositionTarget(x=int(st_tgt[0]), y=int(st_tgt[1]), z=int(st_tgt[2])),
                    target_ori=None,
                    grip="close",
                    stop=False,
                )
            else:
                # Option A (ledger item 7): the memory preamble rides ROUND 1 only, in a
                # fresh single-turn EpisodeConversation (same payload layout as the
                # stateless call + preamble). Rounds 2+ — and every round when no
                # preamble — keep conversation=None (stateless, unchanged).
                if round_history:
                    # P1 collect.py: one conversation for the whole episode (first turn +
                    # last DEFAULT_RECENT_WINDOW pairs, older images stripped by client.py);
                    # the memory preamble still rides round 1 only.
                    if round_idx == 0:
                        ep_conv = EpisodeConversation(get_stage1_system_prompt())
                    r1_conv = ep_conv
                else:
                    r1_conv = (EpisodeConversation(get_stage1_system_prompt())
                               if round_idx == 0 and memory_text else None)
                parsed, latency_ms, err = run_stage1_eef(
                    level_config, teacher_url, rgb, state,
                    conversation=r1_conv,
                    memory_preamble_text=memory_text if r1_conv is not None and round_idx == 0 else None,
                    memory_preamble_images_b64=memory_imgs if r1_conv is not None and round_idx == 0 else None,
                    # rung 1b+: top-down view right after the front image
                    extra_image_bytes=[rgb_top] if top_view else None,
                    critic_feedback=critic_feedback,
                )
                if parsed is None:
                    flags.append("vlm_parse_fail")
                    outcome = EpisodeOutcome.VLM_PARSE_FAIL
                    logger.warning(f"  ep{ep_idx} round{round_idx+1} parse fail → bail ({err})")
                    break
                vlm_interactions.append(_make_eef_vlm_interaction(parsed, latency_ms))

            # A-spec v2: teacher emits a left-TCP target (base-frame grid).
            # De-normalize int→metric (same grid as the state). Orientation =
            # rest ∘ base-axis ORI offset (push_body.command_quat); the executor
            # converts the TCP target to the hand target with the live offset.
            import torch as _torch
            tx = int_to_metric(parsed.target_pos.x, bounds.x_bounds)
            ty = int_to_metric(parsed.target_pos.y, bounds.y_bounds)
            tz = int_to_metric(parsed.target_pos.z, bounds.z_bounds)
            target_t = _torch.tensor([tx, ty, tz], dtype=_torch.float32)
            ori = parsed.target_ori
            q_cmd = pb.command_quat(q_rest, ori)

            cube_before = env.get_cube_pose_b()
            seg = env.execute_push_segment(target_t, q_cmd, steps_per_segment,
                                           frame_every=gif_frame_every, target_is_tcp=True)
            # ledger 15: episode_length_buf must only grow within an episode. A drop
            # means IsaacLab auto-reset inside env.step — the post-segment state
            # belongs to a NEW episode, so this round is not recorded and the
            # episode ends here (outcome unchanged, flag recorded).
            step_count = _episode_step_count(env)
            if last_step_count is not None and step_count is not None and step_count < last_step_count:
                auto_reset = True
                flags.append("env_auto_reset")
                logger.warning(f"  ep{ep_idx} round{round_idx+1} env AUTO-RESET detected "
                               f"(episode_length_buf {last_step_count}→{step_count}) → end episode")
                break
            last_step_count = step_count
            cube_after = env.get_cube_pose_b()
            cube_disp = float(np.linalg.norm(np.array(cube_after) - np.array(cube_before)))

            goal_b = env.get_goal_pose_b()
            cube_goal_dist = float(np.linalg.norm(np.array(cube_after[:2]) - np.array(goal_b[:2])))

            contact = seg.get("contact") or {}
            first_move = contact.get("first_cube_move") or {}
            # GIF frames (human-eye gate, PI only — never a model input) tagged
            # with this round's GT cube→goal + contact anatomy; drawn in a
            # BOTTOM MARGIN STRIP below the scene, so no scene pixels are covered.
            if gif_frame_every and seg.get("frames"):
                tag = (f"R{round_idx+1}  cube->goal {cube_goal_dist*100:.1f}cm (GT)  "
                       f"contact: {first_move.get('anatomy', 'none')}")
                tops = seg.get("frames_top") or [b""] * len(seg["frames"])
                for f, t in zip(seg["frames"], tops):
                    gif_frames.append((f, t, tag))
            tcp_final = seg.get("tcp_final_b")
            tcp_reach_err_cm = (round(float(np.linalg.norm(np.array(tcp_final) - np.array([tx, ty, tz]))) * 100, 2)
                                if tcp_final is not None else None)
            ori_err = seg.get("ori_err_deg") or []

            round_meta.append({
                "round": round_idx + 1,
                # pre-action state: EE start = TCP (proprio) + GT cube/goal (offline)
                **pm.snapshot_to_round_fields(pre_snap),
                "cube_quat_b_pre": cube_quat_b_pre,
                "memory_preamble": round_idx == 0 and memory_text is not None and r1_conv is not None,
                "round_feedback": critic_feedback,          # rung-2': text shown this round (None = off / round 1)
                "verdict_metric": verdict_metric,            # d2: tip_cube | cube_goal | None
                # A-spec v2 EEF action = TCP target (r-tracking raw material)
                "eef_target_int": [parsed.target_pos.x, parsed.target_pos.y, parsed.target_pos.z],
                "eef_target_m": [round(tx, 4), round(ty, 4), round(tz, 4)],
                "ori_offset_deg": ([ori.p, ori.y, ori.r] if ori is not None else None),
                "ori_applied": ori is not None,     # did the brain exercise orientation?
                "hand_target_b": seg.get("hand_target_b"),
                "tcp_target_b": seg.get("tcp_target_b"),
                "tcp_final_b": tcp_final,
                "tcp_reach_err_cm": tcp_reach_err_cm,
                "ori_err_deg_final": seg.get("ori_err_deg_final"),
                "ori_err_deg_max_last20": (max(ori_err[-ORI_ERR_TAIL_STEPS:]) if ori_err else None),
                "contact": contact,                 # GT contact report (offline)
                "table_guard": seg.get("table_guard"),   # safety interlock events (ledger: safety)
                "grip": parsed.grip,
                "cube_disp_m": round(cube_disp, 4),               # GT offline
                "cube_goal_dist_m": round(cube_goal_dist, 4),     # GT offline (predicate)
                # τ monitor summary (Rule 9) incl. clamp flag
                "tau_peak_preclip": seg["tau_peak_preclip"],
                "tau_peak_postclip": seg["tau_peak_postclip"],
                "tau_warn_steps": seg["tau_warn_steps"],
                "tau_flag_steps": seg["tau_flag_steps"],
                "servo_min_err_cm": round(seg["min_err_cm"], 2),
                "vlm_thought": getattr(parsed, "thought", ""),
                "vlm_full_response": vlm_interactions[-1].full_response if vlm_interactions else "",
                "vlm_stop": parsed.stop,
            })
            prev_fb = ((parsed.target_pos.x, parsed.target_pos.y, parsed.target_pos.z),
                       pre_snap.tcp_int, scalars_now)
            touched = _round_touched(contact, cube_disp)
            round_touched.append(touched)
            # Pin-12 arming (before termination so the arming round itself counts)
            if plateau_armed_round is None and touched:
                plateau_armed_round = round_idx + 1
            round_meta[-1]["plateau_armed"] = plateau_armed_round is not None
            if seg["tau_flag_steps"] > 0:
                logger.warning(f"  ep{ep_idx} round{round_idx+1} τ SATURATED {seg['tau_flag_steps']} steps (pre-clip≥1.0)")

            # ── Pin-11 termination ──
            if cube_goal_dist <= PUSH_SUCCESS_M:
                outcome = EpisodeOutcome.SUCCESS
                logger.info(f"  ep{ep_idx} SUCCESS round{round_idx+1} cube_goal={cube_goal_dist*100:.1f}cm")
                break
            if plateau_armed_round is None:
                pass   # Pin-12: no contact yet → only PUSH_ROUND_CAP applies
            elif cube_disp < PUSH_PLATEAU_MIN_DISP_M:
                plateau_count += 1
                if plateau_count >= PUSH_PLATEAU_ROUNDS:
                    outcome = EpisodeOutcome.PUSH_PLATEAU
                    flags.append("push_plateau")
                    logger.info(f"  ep{ep_idx} PLATEAU at round{round_idx+1}")
                    break
            else:
                plateau_count = 0
            if parsed.stop:
                outcome = EpisodeOutcome.VLM_STOP_PREMATURE
                flags.append("vlm_stop_premature")
                break

        if scripted_targets is not None and outcome == EpisodeOutcome.TIMEOUT:
            outcome = EpisodeOutcome.SCRIPTED_END

        rgb_end = env.get_rgb()
        final_snap = pm.snapshot_push_state(env, level_config)
        pm.dump_png(ep_dump_dir, "episode_end.png", rgb_end)
        if top_view:
            pm.dump_png(ep_dump_dir, "episode_end_top.png", env.get_rgb_top())
        total_latency = sum(vi.latency_ms for vi in vlm_interactions)
        goal_sample = env.get_goal_sample() if hasattr(env, "get_goal_sample") else None
        ep_meta = {
            "label": episode_label,
            "task": pm.PUSH_TASK_TAG,
            "obs_rung": obs_rung,
            "top_view": top_view,
            "round_feedback": round_feedback,
            "round_history": round_history,
            "frame_convention": frame_convention,
            "verdict_contact_switch": verdict_contact_switch,
            "frame_line": frame_line,
            "plateau_armed_round": plateau_armed_round,
            "ee_reference": "tcp",                      # init_left_ee_pose = init TCP
            "init_left_tcp_int": list(init_snap.tcp_int),
            "rest_hand_quat_b": [round(float(v), 5) for v in q_rest],
            # GT — offline analysis only (never a model input)
            "init_cube_pose_b": list(init_snap.cube_b),
            "goal_pose_b": list(init_snap.goal_b),
            "offline_gt_situation": init_snap.offline_situation(),
            "workspace_bounds": {"x": list(bounds.x_bounds), "y": list(bounds.y_bounds),
                                 "z": list(bounds.z_bounds)},
            # after an auto-reset the end state is a fresh reset → not recorded
            "final_cube_pose_b": None if auto_reset else list(final_snap.cube_b),
            "rounds_state": pm.replay_rounds_state(round_meta),
            "memory_on": memory_retriever is not None and scripted_targets is None,
            "memory_hits": memory_hits,
            "geometry": geometry,
            "goal_sample": goal_sample,
            "preamble_coords": preamble_coords,
            "preamble_coord_redactions": preamble_coord_redactions,
            "scripted_policy": bool(scripted_targets is not None),
            "dump_dir": str(ep_dump_dir) if ep_dump_dir is not None else None,
        }
        pm.write_push_episode(
            replay,
            (ep_id, run_id, level_config, state, outcome, flags, trajectory,
             vlm_interactions, total_latency, rgb_start, rgb_end, ep_start),
            init=init_snap, env_seed=ep_seed, metadata=ep_meta,
        )
        summary["episodes"].append({"ep_id": ep_id, "outcome": outcome.value, "rounds": len(round_meta),
                                    "label": episode_label, "obs_rung": obs_rung, "env_seed": ep_seed,
                                    "plateau_armed_round": plateau_armed_round,
                                    "init_cube_b": list(init_snap.cube_b), "goal_b": list(init_snap.goal_b),
                                    "init_tcp_b": list(init_snap.tcp_b), "memory_hits": memory_hits,
                                    "geometry": geometry, "goal_sample": goal_sample,
                                    "preamble_coords": preamble_coords,
                                    "preamble_coord_redactions": preamble_coord_redactions,
                                    "scripted_policy": bool(scripted_targets is not None),
                                    "round_meta": round_meta})
        if outcome == EpisodeOutcome.SUCCESS:
            summary["n_success"] += 1
        pm.write_dump_meta(ep_dump_dir, {
            "episode_id": ep_id, "run_id": run_id, "level": level_config.level,
            "level_name": level_config.name, "outcome": outcome.value, "flags": list(flags),
            "label": episode_label, "obs_rung": obs_rung, "env_seed": ep_seed, "rounds": round_meta,
            "frame_convention": frame_convention, "verdict_contact_switch": verdict_contact_switch,
            "frame_line": frame_line,
            "workspace_bounds": {"x": list(bounds.x_bounds), "y": list(bounds.y_bounds),
                                 "z": list(bounds.z_bounds)},
            "geometry": geometry,
            "goal_sample": goal_sample,
            "preamble_coords": preamble_coords,
            "preamble_coord_redactions": preamble_coord_redactions,
            "scripted_policy": bool(scripted_targets is not None),
        })

        # recap — always (any outcome) if a buffer is given and not readonly
        # (collect.py's Amendment 8 §8.5 gate)
        # An auto-reset episode's end scene/state is a fresh reset → no recap
        # (it would teach memory a false outcome; ledger 15).
        if auto_reset and recap_buffer is not None:
            logger.warning(f"  ep{ep_idx} recap skipped (env_auto_reset)")
        if (recap_buffer is not None and not recap_buffer_readonly and not auto_reset
                and scripted_targets is None):
            try:
                pm.emit_push_recap(
                    recap_buffer=recap_buffer, ep_id=ep_id, run_id=run_id,
                    outcome=outcome.value, obs_rung=obs_rung, label=episode_label,
                    instruction=level_config.task_instruction_template,
                    init=init_snap, final=final_snap, round_meta=round_meta, bounds=bounds,
                    ep_dump_dir=ep_dump_dir, rgb_start=rgb_start, rgb_end=rgb_end,
                    teacher_url=teacher_url, success_cm=PUSH_SUCCESS_M * 100,
                    min_disp_cm=PUSH_PLATEAU_MIN_DISP_M * 100,
                )
            except Exception as e:
                logger.warning(f"  ep{ep_idx} recap failed: {e}")

    logger.info(f"push_collect DONE: {summary['n_success']}/{num_episodes} success")
    if gif_frame_every and gif_frames:
        try:
            import imageio.v2 as _imageio
            from aiongenos.orchestrator.push_gif import compose_frame
            # PI convention (2026-10-15): front | top, each labelled FED / PI-only.
            # The front image is always fed; the top view is fed from rung-1b on.
            imgs = [compose_frame(png, top, tag, front_fed=True, top_fed=top_view)
                    for png, top, tag in gif_frames]
            gif_path = f"logs/push_gif_{run_id}.gif"
            _imageio.mimsave(gif_path, imgs, duration=0.08)
            summary["gif_path"] = gif_path
            logger.info(f"push_collect GIF: {gif_path} ({len(imgs)} frames, cube→goal overlay)")
        except Exception as e:
            logger.warning(f"GIF save failed: {e}")
    return summary

