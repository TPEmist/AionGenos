"""Evaluation orchestrator — multi-round closed-loop within each episode.

Each episode runs up to ``max_subgoals_per_episode`` rounds:
  Round k: VLM observes fresh RGB + EE state → outputs sub-goal → IK servo for
  ``sim_steps`` steps. Episode stops on:
    - success: both arms within ``subgoal_success_threshold_m`` of target
    - vlm_stop: VLM emits STOP=true
    - plateau: best distance fails to improve > ``plateau_min_progress_m``
               for ``plateau_patience`` consecutive rounds
    - max_rounds: round budget exhausted
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from pathlib import Path
from typing import Optional

import numpy as np

from aiongenos.config import AionGenosConfig, LevelConfig
from aiongenos.pipeline.stage1_reasoning import run_stage1
from aiongenos.control.command_converter import convert_stage1_to_commands
from aiongenos.vlm.client import EpisodeConversation
from aiongenos.vlm.prompts import get_stage1_system_prompt
from aiongenos.pipeline.stage3_critic import generate_critic_feedback

logger = logging.getLogger(__name__)


def _grounding_targets_base_frame(env) -> Optional[tuple[np.ndarray, np.ndarray]]:
    """Resolve current GT targets in the robot's base frame, or None on failure."""
    try:
        left_target_w, right_target_w = env._get_target_poses()
        root_w = env.robot.data.root_pos_w[0].cpu().numpy() if env.robot is not None else np.zeros(3)
        return left_target_w - root_w, right_target_w - root_w
    except Exception as e:
        logger.debug(f"target-resolution failed: {e}")
        return None


def _run_episode(
    env,
    level_config: LevelConfig,
    vlm_url: str,
    sim_steps: int,
    dump_dir: Optional[Path] = None,
) -> dict:
    """Drive a single multi-round episode, return per-episode metrics.

    Args:
        env: IsaacLab env interface.
        level_config: Curriculum level config.
        vlm_url: VLM endpoint URL.
        sim_steps: IK servo step count per round.
        dump_dir: If provided, save per-round RGB pairs and meta.json under it.
    """
    env.reset()
    round_meta: list[dict] = []
    if dump_dir is not None:
        dump_dir.mkdir(parents=True, exist_ok=True)

    max_rounds = level_config.max_subgoals_per_episode
    success_thresh = level_config.subgoal_success_threshold_m
    plateau_eps = level_config.plateau_min_progress_m
    plateau_patience = level_config.plateau_patience
    plateau_window = level_config.plateau_window

    total_latency_ms = 0.0
    vlm_calls = 0
    parse_fails = 0
    rounds_executed = 0
    outcome = "max_rounds"
    grounding_errs_l: list[float] = []
    grounding_errs_r: list[float] = []
    final_dist_l = float("nan")
    final_dist_r = float("nan")
    no_progress_rounds = 0
    combined_history: list[float] = []  # T-8b: track combined dist per round for rolling-mean plateau

    conversation = EpisodeConversation(get_stage1_system_prompt())

    # Variables to track for round-based critic feedback
    prev_predicted_left = None
    prev_predicted_right = None
    prev_actual_left = None
    prev_actual_right = None
    prev_dist_l = None
    prev_dist_r = None

    for round_idx in range(max_rounds):
        rounds_executed = round_idx + 1
        rgb = env.get_rgb()
        if dump_dir is not None and rgb:
            (dump_dir / f"round_{round_idx + 1:02d}_pre.png").write_bytes(rgb)
        state = env.get_state(level_config)
        try:
            state["instruction"] = level_config.task_instruction_template.format(**state)
        except Exception:
            state["instruction"] = level_config.task_instruction_template

        critic_feedback = None
        if round_idx > 0 and prev_predicted_left is not None:
            actual_left_end = (state["left_x"], state["left_y"], state["left_z"])
            actual_right_end = (state["right_x"], state["right_y"], state["right_z"])
            critic_feedback = generate_critic_feedback(
                prev_predicted_left=prev_predicted_left,
                prev_predicted_right=prev_predicted_right,
                actual_left_start=prev_actual_left,
                actual_right_start=prev_actual_right,
                actual_left_end=actual_left_end,
                actual_right_end=actual_right_end,
                dist_l_start_cm=prev_dist_l * 100 if prev_dist_l is not None else 0.0,
                dist_r_start_cm=prev_dist_r * 100 if prev_dist_r is not None else 0.0,
                dist_l_end_cm=final_dist_l * 100 if not np.isnan(final_dist_l) else 0.0,
                dist_r_end_cm=final_dist_r * 100 if not np.isnan(final_dist_r) else 0.0,
            )
            logger.info(f"Round {round_idx + 1} Critic Feedback:\n{critic_feedback}")

        stage1_result, stage1_latency, _ = run_stage1(
            level_config=level_config,
            teacher_url=vlm_url,
            rgb_bytes=rgb,
            state=state,
            conversation=conversation,
            critic_feedback=critic_feedback,
            max_retries=level_config.max_retry_on_parse_fail,
        )
        total_latency_ms += stage1_latency
        vlm_calls += 1

        if stage1_result is None:
            parse_fails += 1
            outcome = "vlm_parse_fail"
            logger.warning(f"  Round {round_idx + 1}/{max_rounds} parse fail → bail")
            break

        command = convert_stage1_to_commands(stage1_result, level_config.workspace_bounds)

        # Get initial state and distance before execution for the next round's feedback
        curr_dists = env.get_current_distances()
        prev_dist_l = curr_dists.get("dist_red", 0.0)
        prev_dist_r = curr_dists.get("dist_blue", 0.0)
        prev_actual_left = (state["left_x"], state["left_y"], state["left_z"])
        prev_actual_right = (state["right_x"], state["right_y"], state["right_z"])
        prev_predicted_left = (stage1_result.left.position.x, stage1_result.left.position.y, stage1_result.left.position.z)
        prev_predicted_right = (stage1_result.right.position.x, stage1_result.right.position.y, stage1_result.right.position.z)

        targets = _grounding_targets_base_frame(env)
        left_target_b = right_target_b = None  # type: ignore[assignment]
        ge_l = ge_r = float("nan")
        if targets is not None:
            left_target_b, right_target_b = targets
            ge_l = float(np.linalg.norm(np.array(command.left.position) - left_target_b))
            ge_r = float(np.linalg.norm(np.array(command.right.position) - right_target_b))
            grounding_errs_l.append(ge_l)
            grounding_errs_r.append(ge_r)
            logger.info(
                f"  Round {round_idx + 1}/{max_rounds} VLM=({command.left.position}, {command.right.position}) "
                f"GT=({tuple(round(v,3) for v in left_target_b)}, {tuple(round(v,3) for v in right_target_b)}) "
                f"grounding L/R cm={ge_l*100:.1f}/{ge_r*100:.1f}"
            )

        attempt = env.execute_command(command, sim_steps)

        if dump_dir is not None:
            post_rgb = env.get_rgb()
            if post_rgb:
                (dump_dir / f"round_{round_idx + 1:02d}_post.png").write_bytes(post_rgb)

        if attempt.trajectory:
            last = attempt.trajectory[-1].distances
            final_dist_l = last.get("dist_red", float("nan"))
            final_dist_r = last.get("dist_blue", float("nan"))

        combined = (final_dist_l + final_dist_r) if not (
            np.isnan(final_dist_l) or np.isnan(final_dist_r)
        ) else float("inf")

        logger.info(
            f"  Round {round_idx + 1}/{max_rounds} outcome={attempt.outcome} "
            f"final_dist L/R cm={final_dist_l*100:.1f}/{final_dist_r*100:.1f} "
            f"stop={getattr(stage1_result, 'stop', False)}"
        )

        if dump_dir is not None:
            round_meta.append({
                "round": round_idx + 1,
                "vlm_left_pos_m": [float(v) for v in command.left.position],
                "vlm_right_pos_m": [float(v) for v in command.right.position],
                "gt_left_pos_b_m": [float(v) for v in left_target_b] if left_target_b is not None else None,
                "gt_right_pos_b_m": [float(v) for v in right_target_b] if right_target_b is not None else None,
                "grounding_err_l_cm": float(ge_l * 100) if not np.isnan(ge_l) else None,
                "grounding_err_r_cm": float(ge_r * 100) if not np.isnan(ge_r) else None,
                "final_dist_l_cm": float(final_dist_l * 100) if not np.isnan(final_dist_l) else None,
                "final_dist_r_cm": float(final_dist_r * 100) if not np.isnan(final_dist_r) else None,
                "attempt_outcome": attempt.outcome,
                "vlm_stop": bool(getattr(stage1_result, "stop", False)),
                "vlm_thought": getattr(stage1_result, "thought", "")[:500],
                "stage1_latency_ms": float(stage1_latency),
            })

        # ── Termination checks ──
        if (
            not np.isnan(final_dist_l) and not np.isnan(final_dist_r)
            and final_dist_l < success_thresh and final_dist_r < success_thresh
        ):
            outcome = "success"
            break

        if attempt.outcome == "collision":
            outcome = "collision"
            break

        if getattr(stage1_result, "stop", False):
            outcome = "vlm_stop"
            break

        # T-8b Plateau detection: rolling-mean over the last `plateau_window`
        # rounds vs the previous window. We only start judging after we have
        # enough history (2 * window rounds), so VLM has room to explore early.
        if not np.isinf(combined):
            combined_history.append(combined)
        recent_mean = (
            float(np.mean(combined_history[-plateau_window:]))
            if len(combined_history) >= plateau_window
            else float("inf")
        )
        prior_mean = (
            float(np.mean(combined_history[-2 * plateau_window : -plateau_window]))
            if len(combined_history) >= 2 * plateau_window
            else float("inf")
        )
        if np.isinf(prior_mean):
            no_progress_rounds = 0
        elif prior_mean - recent_mean > plateau_eps:
            no_progress_rounds = 0
        else:
            no_progress_rounds += 1
            if no_progress_rounds >= plateau_patience:
                outcome = "plateau"
                logger.info(
                    f"  Plateau triggered: recent_mean={recent_mean*100:.1f}cm, "
                    f"prior_mean={prior_mean*100:.1f}cm, "
                    f"window={plateau_window}, patience={plateau_patience}"
                )
                break

    if dump_dir is not None:
        meta = {
            "level": level_config.level,
            "level_name": level_config.name,
            "outcome": outcome,
            "rounds_executed": rounds_executed,
            "max_rounds": max_rounds,
            "sim_steps_per_subgoal": sim_steps,
            "rounds": round_meta,
        }
        (dump_dir / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))

    return {
        "outcome": outcome,
        "rounds": rounds_executed,
        "vlm_calls": vlm_calls,
        "total_latency_ms": total_latency_ms,
        "parse_fails": parse_fails,
        "grounding_errs_l": grounding_errs_l,
        "grounding_errs_r": grounding_errs_r,
        "final_dist_l": final_dist_l,
        "final_dist_r": final_dist_r,
    }


def run_eval(
    config: AionGenosConfig,
    env,
    level_config: LevelConfig,
    vlm_url: str,
    num_episodes: int = 10,
    sim_steps_override: Optional[int] = None,
    dump_root: Optional[Path] = None,
    run_label: Optional[str] = None,
) -> dict[str, float]:
    """Evaluate a VLM endpoint on a level via multi-round closed-loop episodes.

    If ``dump_root`` is provided, every episode writes per-round RGB pairs and
    a meta.json under ``{dump_root}/{run_label}/{ep_id}/``.
    """
    logger.info(f"Starting evaluation: URL={vlm_url}, level={level_config.level}, episodes={num_episodes}")

    sim_steps = sim_steps_override if sim_steps_override is not None else level_config.sim_steps_per_subgoal
    logger.info(
        f"sim_steps_per_subgoal={sim_steps} (override={sim_steps_override is not None}), "
        f"max_rounds={level_config.max_subgoals_per_episode}"
    )

    eval_run_dir: Optional[Path] = None
    if dump_root is not None:
        label = run_label or "eval"
        eval_run_dir = dump_root / label
        eval_run_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Dumping per-round RGB + meta to: {eval_run_dir}")

    success_count = 0
    total_latency_ms = 0.0
    total_duration_s = 0.0
    total_vlm_calls = 0
    total_parse_fails = 0
    rounds_per_ep: list[int] = []
    grounding_errs_l_all: list[float] = []
    grounding_errs_r_all: list[float] = []
    final_dists_l: list[float] = []
    final_dists_r: list[float] = []
    outcome_counts: dict[str, int] = {}

    for ep_idx in range(num_episodes):
        ep_start = time.time()
        logger.info(f"Eval Episode {ep_idx + 1}/{num_episodes} | L{level_config.level}")

        ep_dump_dir: Optional[Path] = None
        if eval_run_dir is not None:
            ep_dump_dir = eval_run_dir / f"ep_{ep_idx + 1:03d}_{uuid.uuid4().hex[:6]}"

        result = _run_episode(env, level_config, vlm_url, sim_steps, dump_dir=ep_dump_dir)

        outcome_counts[result["outcome"]] = outcome_counts.get(result["outcome"], 0) + 1
        rounds_per_ep.append(result["rounds"])
        total_vlm_calls += result["vlm_calls"]
        total_latency_ms += result["total_latency_ms"]
        total_parse_fails += result["parse_fails"]
        grounding_errs_l_all.extend(result["grounding_errs_l"])
        grounding_errs_r_all.extend(result["grounding_errs_r"])
        if not np.isnan(result["final_dist_l"]):
            final_dists_l.append(result["final_dist_l"])
        if not np.isnan(result["final_dist_r"]):
            final_dists_r.append(result["final_dist_r"])

        if result["outcome"] == "success":
            success_count += 1
            logger.info(
                f"Episode {ep_idx + 1} SUCCESS in {result['rounds']} rounds "
                f"(final dist L/R cm: {result['final_dist_l']*100:.1f}/{result['final_dist_r']*100:.1f})"
            )
        else:
            logger.info(
                f"Episode {ep_idx + 1} {result['outcome'].upper()} after {result['rounds']} rounds "
                f"(final dist L/R cm: {result['final_dist_l']*100:.1f}/{result['final_dist_r']*100:.1f})"
            )

        total_duration_s += time.time() - ep_start

    sr = success_count / num_episodes if num_episodes > 0 else 0.0
    avg_latency = total_latency_ms / total_vlm_calls if total_vlm_calls > 0 else 0.0
    avg_duration = total_duration_s / num_episodes if num_episodes > 0 else 0.0
    avg_rounds = float(np.mean(rounds_per_ep)) if rounds_per_ep else 0.0

    avg_ge_l = float(np.mean(grounding_errs_l_all)) if grounding_errs_l_all else float("nan")
    avg_ge_r = float(np.mean(grounding_errs_r_all)) if grounding_errs_r_all else float("nan")
    avg_fd_l = float(np.mean(final_dists_l)) if final_dists_l else float("nan")
    avg_fd_r = float(np.mean(final_dists_r)) if final_dists_r else float("nan")

    metrics = {
        "success_rate": sr,
        "avg_latency_ms": avg_latency,
        "avg_duration_s": avg_duration,
        "total_episodes": float(num_episodes),
        "success_episodes": float(success_count),
        "parse_fail": float(total_parse_fails),
        "avg_rounds_per_episode": avg_rounds,
        "total_vlm_calls": float(total_vlm_calls),
        "avg_grounding_err_left_m": avg_ge_l,
        "avg_grounding_err_right_m": avg_ge_r,
        "avg_final_dist_left_m": avg_fd_l,
        "avg_final_dist_right_m": avg_fd_r,
        "outcome_counts": outcome_counts,
    }

    logger.info(
        f"Evaluation finished: SR={sr:.1%}, "
        f"avg_rounds={avg_rounds:.1f}, "
        f"avg_latency={avg_latency:.0f}ms/call, "
        f"avg_duration={avg_duration:.1f}s/ep, "
        f"parse_fail={total_parse_fails}, "
        f"grounding_err L/R cm={avg_ge_l*100:.1f}/{avg_ge_r*100:.1f}, "
        f"final_dist L/R cm={avg_fd_l*100:.1f}/{avg_fd_r*100:.1f}, "
        f"outcomes={outcome_counts}"
    )
    return metrics
