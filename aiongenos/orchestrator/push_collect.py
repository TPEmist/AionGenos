"""push_collect.py — P2 first-class collect instrument for the WP1-③a push task.

Sibling of collect.py (P1 reach/L2), NEVER integrated back into it. Equivalence
with collect.py is audited in docs/p2_prereg/dual_collect_equivalence_ledger.md.

Observation rule (PI ruling 2026-10-05): the model sees IMAGE +
PROPRIOCEPTION only (stage-1 state = TCP grid + disclosed scaffold block of
the env's push_obs_rung). GT cube/goal is read here ONLY for the success
predicate and offline records (round_meta, replay metadata).

Loop per round:
  RGB + proprio state → run_stage1_eef (teacher emits a left-TCP target:
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
GIF_STRIP_PX = 14         # bottom margin strip for the GIF text tag
ORI_ERR_TAIL_STEPS = 20   # ori_err max over the segment's last N steps (settled error)


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
) -> dict:
    """Drive `num_episodes` push episodes. Returns a summary dict.

    Seed convention IDENTICAL to collect.py: env_seed_base + ep_idx (None →
    nondeterministic). Per-round records carry the push primitive's 3 numbers
    (requested/clamped disp, was_clamped) + the τ monitor summary."""
    _check_episode_budget(env, steps_per_segment)
    # disclosed-scaffold rung lives on the env (it shapes get_state); read it
    # once here so every record states which rung its data came from
    obs_rung = int(env.push_obs_rung)
    if memory_retriever is not None and int(memory_retriever.obs_rung) != obs_rung:
        raise RuntimeError(f"push_collect: retriever obs_rung={memory_retriever.obs_rung} "
                           f"!= env push_obs_rung={obs_rung}")
    bounds = level_config.workspace_bounds
    run_id = ReplayBuffer.new_run_id()
    logger.info(f"push_collect run_id={run_id} episodes={num_episodes} label={episode_label} obs_rung={obs_rung}")
    summary = {"run_id": run_id, "label": episode_label, "obs_rung": obs_rung, "episodes": [],
               "n_success": 0, "memory_on": memory_retriever is not None}
    gif_frames = []   # PNG bytes across the run (if gif_frame_every>0)

    for ep_idx in range(num_episodes):
        ep_seed = None if env_seed_base is None else env_seed_base + ep_idx
        ep_id = ReplayBuffer.new_episode_id()
        ep_start = time.time()
        env.reset(seed=ep_seed)
        rgb_start = env.get_rgb()
        ep_dump_dir = pm.episode_dump_dir(dump_images_root, run_id, ep_id)
        pm.dump_png(ep_dump_dir, "episode_start.png", rgb_start)
        # Reset-time snapshot (after reset, before any servo): init TCP
        # (proprio: retrieval key, recap) + GT cube/goal (offline records).
        init_snap = pm.snapshot_push_state(env, level_config)
        # Rest orientation = the live Pin-7a standby hand orientation; the
        # ONLY orientation source besides the teacher's ORI offset.
        q_rest = env.get_left_hand_quat_b()

        trajectory = []
        vlm_interactions = []
        flags = [f"label:{episode_label}"]
        round_meta = []
        outcome = EpisodeOutcome.TIMEOUT
        plateau_count = 0
        cube0_b = env.get_cube_pose_b()
        last_step_count = _episode_step_count(env)   # auto-reset detector (ledger 15)
        auto_reset = False

        # Memory: retrieve once at ep start (query = start RGB + init TCP);
        # within-run retrieval allowed (this ep's recap does not exist yet).
        memory_text: Optional[str] = None
        memory_imgs: Optional[list[str]] = None
        memory_hits: list[dict] = []
        if memory_retriever is not None and rgb_start:
            try:
                pre = memory_retriever.retrieve_for_episode(rgb_start, init_snap.tcp_int)
                if not pre.is_empty:
                    memory_text, memory_imgs = pre.prelude_text, pre.past_image_base64_list
                    memory_hits = [{"ep_id": r.ep_id, "run_id": r.run_id, "score": round(s, 4),
                                    "outcome": r.outcome}
                                   for r, s in zip(pre.retrieved_records, pre.similarities)]
                    hit_ids = ",".join(h["ep_id"][:8] for h in memory_hits)
                    hit_scores = ",".join(f"{h['score']:.2f}" for h in memory_hits)
                    logger.info(f"  ep{ep_idx} memory: injected {len(memory_hits)} past eps "
                                f"[{hit_ids}] scores=[{hit_scores}]")
                else:
                    logger.info(f"  ep{ep_idx} memory: buffer empty or all filtered, no preamble")
            except Exception as e:
                logger.warning(f"  ep{ep_idx} memory retrieval failed (continuing without): {e}")

        for round_idx in range(PUSH_ROUND_CAP):
            rgb = env.get_rgb()
            pm.dump_png(ep_dump_dir, f"round_{round_idx + 1:02d}_pre.png", rgb)
            state = env.get_state(level_config)
            pre_snap = pm.snapshot_push_state(env, level_config, state)
            # inject instruction (get_state doesn't; collect.py does the same
            # from task_instruction_template) — the PUSH prompt has {instruction}
            state["instruction"] = level_config.task_instruction_template

            # Option A (ledger item 7): the memory preamble rides ROUND 1 only, in a
            # fresh single-turn EpisodeConversation (same payload layout as the
            # stateless call + preamble). Rounds 2+ — and every round when no
            # preamble — keep conversation=None (stateless, unchanged).
            r1_conv = (EpisodeConversation(get_stage1_system_prompt())
                       if round_idx == 0 and memory_text else None)
            parsed, latency_ms, err = run_stage1_eef(
                level_config, teacher_url, rgb, state,
                conversation=r1_conv,
                memory_preamble_text=memory_text if r1_conv is not None else None,
                memory_preamble_images_b64=memory_imgs if r1_conv is not None else None,
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
                for f in seg["frames"]:
                    gif_frames.append((f, tag))
            tcp_final = seg.get("tcp_final_b")
            tcp_reach_err_cm = (round(float(np.linalg.norm(np.array(tcp_final) - np.array([tx, ty, tz]))) * 100, 2)
                                if tcp_final is not None else None)
            ori_err = seg.get("ori_err_deg") or []

            round_meta.append({
                "round": round_idx + 1,
                # pre-action state: EE start = TCP (proprio) + GT cube/goal (offline)
                **pm.snapshot_to_round_fields(pre_snap),
                "memory_preamble": r1_conv is not None,
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
                "vlm_full_response": vlm_interactions[-1].full_response,
                "vlm_stop": parsed.stop,
            })
            if seg["tau_flag_steps"] > 0:
                logger.warning(f"  ep{ep_idx} round{round_idx+1} τ SATURATED {seg['tau_flag_steps']} steps (pre-clip≥1.0)")

            # ── Pin-11 termination ──
            if cube_goal_dist <= PUSH_SUCCESS_M:
                outcome = EpisodeOutcome.SUCCESS
                logger.info(f"  ep{ep_idx} SUCCESS round{round_idx+1} cube_goal={cube_goal_dist*100:.1f}cm")
                break
            if cube_disp < PUSH_PLATEAU_MIN_DISP_M:
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

        rgb_end = env.get_rgb()
        final_snap = pm.snapshot_push_state(env, level_config)
        pm.dump_png(ep_dump_dir, "episode_end.png", rgb_end)
        total_latency = sum(vi.latency_ms for vi in vlm_interactions)
        ep_meta = {
            "label": episode_label,
            "task": pm.PUSH_TASK_TAG,
            "obs_rung": obs_rung,
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
            "memory_on": memory_retriever is not None,
            "memory_hits": memory_hits,
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
                                    "init_cube_b": list(init_snap.cube_b), "goal_b": list(init_snap.goal_b),
                                    "init_tcp_b": list(init_snap.tcp_b), "memory_hits": memory_hits,
                                    "round_meta": round_meta})
        if outcome == EpisodeOutcome.SUCCESS:
            summary["n_success"] += 1
        pm.write_dump_meta(ep_dump_dir, {
            "episode_id": ep_id, "run_id": run_id, "level": level_config.level,
            "level_name": level_config.name, "outcome": outcome.value, "flags": list(flags),
            "label": episode_label, "obs_rung": obs_rung, "env_seed": ep_seed, "rounds": round_meta,
        })

        # recap — always (any outcome) if a buffer is given and not readonly
        # (collect.py's Amendment 8 §8.5 gate)
        # An auto-reset episode's end scene/state is a fresh reset → no recap
        # (it would teach memory a false outcome; ledger 15).
        if auto_reset and recap_buffer is not None:
            logger.warning(f"  ep{ep_idx} recap skipped (env_auto_reset)")
        if recap_buffer is not None and not recap_buffer_readonly and not auto_reset:
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
            import imageio.v2 as _imageio, io as _io, numpy as _np
            from PIL import Image as _Image, ImageDraw as _ImageDraw
            imgs = []
            for png, tag in gif_frames:
                scene = _Image.open(_io.BytesIO(png)).convert("RGB")
                # bottom margin strip BELOW the scene (canvas grows; no scene
                # pixel is covered); default PIL font, legible at 256px
                im = _Image.new("RGB", (scene.width, scene.height + GIF_STRIP_PX), (0, 0, 0))
                im.paste(scene, (0, 0))
                _ImageDraw.Draw(im).text((2, scene.height + 2), tag, fill=(255, 255, 0))
                imgs.append(_np.asarray(im))
            gif_path = f"logs/push_gif_{run_id}.gif"
            _imageio.mimsave(gif_path, imgs, duration=0.08)
            summary["gif_path"] = gif_path
            logger.info(f"push_collect GIF: {gif_path} ({len(imgs)} frames, cube→goal overlay)")
        except Exception as e:
            logger.warning(f"GIF save failed: {e}")
    return summary

