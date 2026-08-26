"""push_collect.py — P2 first-class collect instrument for the WP1-③a push task.

Sibling of collect.py (P1 reach/L2), NEVER integrated back into it. Equivalence
with collect.py is audited in docs/p2_prereg/dual_collect_equivalence_ledger.md.

Loop per round:
  RGB + two-leg state → run_stage1_push (teacher emits PUSH_TO x,y)
  → convert_push_to_waypoint_metric (translate int→base-frame metric)
  → push_segment_from_waypoint (primitive: lead-clamp + behind-cube approach)
  → iface.execute_push_segment (OSC servo + inner-loop τ monitor)
  → record round (push 3 nums + τ) → Pin-11 termination → next round
End: shared _write_episode + recap.

Shared substrate imported (NOT copied): collect_common helpers, ReplayBuffer,
schema, generate_recap. Only the loop glue + push success predicate are
push-specific (the one intended divergence — cube displacement, not EE
distance).
"""

from __future__ import annotations

import logging
import time
from typing import Optional

import numpy as np

from aiongenos.config import LevelConfig, WorkspaceBounds
from aiongenos.pipeline.stage1_reasoning import run_stage1_push
from aiongenos.pipeline.stage2_attempt import convert_push_to_waypoint_metric
from aiongenos.replay.buffer import ReplayBuffer
from aiongenos.replay.schema import EpisodeOutcome
from aiongenos.orchestrator.collect_common import _make_vlm_interaction, _write_episode
from aiongenos.tasks.WP1_contact_testbed.wp1_target_gate import push_segment_from_waypoint

logger = logging.getLogger(__name__)

# Pin-11 (sealed): success = cube within this of goal; round cap; plateau rule.
PUSH_SUCCESS_M = 0.05
PUSH_ROUND_CAP = 12
PUSH_PLATEAU_ROUNDS = 3
PUSH_PLATEAU_MIN_DISP_M = 0.01


def _make_push_vlm_interaction(response, latency_ms: float):
    """VLMInteraction for a push response. _make_vlm_interaction (shared)
    assumes a two-arm Stage1Response; the push response has a single PUSH_TO.
    We adapt to the SAME VLMInteraction schema, storing the waypoint in the
    left-pos slot (z=0) and thought in full_response, so replay/recap consume
    it identically. A push-shaped shim, not a schema change."""
    from aiongenos.replay.schema import VLMInteraction
    return VLMInteraction(
        stage="stage1_push",
        full_response=getattr(response, "thought", ""),
        parsed_left_pos=(response.push_to.x, response.push_to.y, 0),
        parsed_right_pos=(0, 0, 0),
        parsed_left_rpy=None,
        parsed_right_rpy=None,
        parsed_left_gripper=None,
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
) -> dict:
    """Drive `num_episodes` push episodes. Returns a summary dict.

    Seed convention IDENTICAL to collect.py: env_seed_base + ep_idx (None →
    nondeterministic). Per-round records carry the push primitive's 3 numbers
    (requested/clamped disp, was_clamped) + the τ monitor summary."""
    bounds = level_config.workspace_bounds
    run_id = ReplayBuffer.new_run_id()
    logger.info(f"push_collect run_id={run_id} episodes={num_episodes} label={episode_label}")
    summary = {"run_id": run_id, "episodes": [], "n_success": 0}

    for ep_idx in range(num_episodes):
        ep_seed = None if env_seed_base is None else env_seed_base + ep_idx
        ep_id = ReplayBuffer.new_episode_id()
        ep_start = time.time()
        env.reset(seed=ep_seed)
        rgb_start = env.get_rgb()

        trajectory = []
        vlm_interactions = []
        flags = [f"label:{episode_label}"]
        round_meta = []
        outcome = EpisodeOutcome.TIMEOUT
        plateau_count = 0
        cube0_b = env.get_cube_pose_b()

        for round_idx in range(PUSH_ROUND_CAP):
            rgb = env.get_rgb()
            state = env.get_state(level_config)
            # inject instruction (get_state doesn't; collect.py does the same
            # from task_instruction_template) — the PUSH prompt has {instruction}
            state["instruction"] = level_config.task_instruction_template

            parsed, latency_ms, err = run_stage1_push(
                level_config, teacher_url, rgb, state,
            )
            if parsed is None:
                flags.append("vlm_parse_fail")
                outcome = EpisodeOutcome.VLM_PARSE_FAIL
                logger.warning(f"  ep{ep_idx} round{round_idx+1} parse fail → bail ({err})")
                break
            vlm_interactions.append(_make_push_vlm_interaction(parsed, latency_ms))

            # translate PUSH_TO → base-frame waypoint metric (x,y); z from cube
            wx, wy = convert_push_to_waypoint_metric(parsed, bounds)
            cube_b = env.get_cube_pose_b()
            import torch as _torch
            cube_t = _torch.tensor(cube_b, dtype=_torch.float32)
            waypoint_t = _torch.tensor([wx, wy, cube_b[2]], dtype=_torch.float32)
            approach_b, target_b, pinfo = push_segment_from_waypoint(cube_t, waypoint_t)

            cube_before = env.get_cube_pose_b()
            seg = env.execute_push_segment(approach_b, steps_per_segment)
            cube_after = env.get_cube_pose_b()
            cube_disp = float(np.linalg.norm(np.array(cube_after) - np.array(cube_before)))

            goal_b = env.get_goal_pose_b()
            cube_goal_dist = float(np.linalg.norm(np.array(cube_after[:2]) - np.array(goal_b[:2])))

            round_meta.append({
                "round": round_idx + 1,
                "push_to_int": [parsed.push_to.x, parsed.push_to.y],
                "waypoint_m": [round(wx, 4), round(wy, 4)],
                # push primitive 3 numbers (r-tracking raw material)
                "requested_disp_m": round(pinfo["requested_disp_m"], 4),
                "clamped_disp_m": round(pinfo["clamped_disp_m"], 4),
                "was_clamped": pinfo["was_clamped"],
                "cube_disp_m": round(cube_disp, 4),
                "cube_goal_dist_m": round(cube_goal_dist, 4),
                # τ monitor summary (Rule 9)
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
        total_latency = sum(vi.latency_ms for vi in vlm_interactions)
        _write_episode(
            replay, ep_id, run_id, level_config, state,
            outcome, flags, trajectory, vlm_interactions,
            total_latency, rgb_start, rgb_end, ep_start,
        )
        summary["episodes"].append({"ep_id": ep_id, "outcome": outcome.value, "rounds": len(round_meta),
                                    "round_meta": round_meta})
        if outcome == EpisodeOutcome.SUCCESS:
            summary["n_success"] += 1

        # recap (shared) — always, if buffer given
        if recap_buffer is not None:
            try:
                _emit_push_recap(recap_buffer, ep_id, level_config, round_meta, outcome, rgb_start)
            except Exception as e:
                logger.warning(f"  ep{ep_idx} recap failed: {e}")

    logger.info(f"push_collect DONE: {summary['n_success']}/{num_episodes} success")
    return summary


def _emit_push_recap(recap_buffer, ep_id, level_config, round_meta, outcome, rgb_start):
    """Emit a post-episode recap for a push episode via the SHARED recap
    pipeline. Deferred-heavy import (torchvision) done locally, mirroring
    collect.py's pattern."""
    from aiongenos.pipeline.stage4_recap import generate_recap
    # minimal round adaptation — push rounds carry vlm_thought + outcome signal
    text_rounds = [
        f"round {rm['round']}: PUSH_TO {rm['push_to_int']} → cube moved {rm['cube_disp_m']*100:.1f}cm, "
        f"cube-goal {rm['cube_goal_dist_m']*100:.1f}cm, τ_peak {rm['tau_peak_preclip']}"
        for rm in round_meta
    ]
    logger.info(f"  recap ep {ep_id[:8]}: {len(round_meta)} rounds, outcome={outcome.value}")
    # NOTE: full generate_recap wiring (RGB + structured rounds) is finalized
    # when the smoke's recap-content check runs (Q7); this records the trigger
    # fires and the round summary is available.
    return text_rounds
