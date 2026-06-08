"""Collector orchestrator — 4-stage cognitive evolution loop.

Drives the full collect pipeline:
1. Stage 1: VLM Reasoning → sub-goal
2. Stage 2: Attempt → execute in sim
3. Stage 3: Critic (on failure) → revised sub-goal → retry
4. Write replay episode

Curriculum manager checks for level advancement after each batch.

NOTE: This module defines the loop logic. IsaacLab env interaction requires
Isaac Sim runtime and is provided via the EnvInterface protocol.
"""

from __future__ import annotations

import logging
import time
import uuid
import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Protocol

from aiongenos.config import AionGenosConfig, LevelConfig
from aiongenos.curriculum.manager import AionGenosCurriculumManager
from aiongenos.pipeline.stage1_reasoning import run_stage1
from aiongenos.pipeline.stage2_attempt import (
    AttemptResult,
    convert_stage1_to_commands,
    BimanualCommand,
)
from aiongenos.pipeline.stage3_critic import generate_critic_feedback
from aiongenos.vlm.client import EpisodeConversation
from aiongenos.vlm.prompts import get_stage1_system_prompt
from aiongenos.replay.buffer import ReplayBuffer
from aiongenos.replay.schema import (
    EpisodeOutcome,
    ReplayEpisode,
    TimeStep,
    VLMInteraction,
)

logger = logging.getLogger(__name__)


class EnvInterface(Protocol):
    """Protocol for environment interaction.

    Implementations provide the sim-specific logic for:
    - Rendering RGB images
    - Getting EE state
    - Executing commands
    - Checking outcomes
    """

    def reset(self) -> dict:
        """Reset environment, return initial state dict."""
        ...

    def get_rgb(self) -> bytes:
        """Capture current scene as PNG bytes."""
        ...

    def get_state(self, level_config: LevelConfig) -> dict[str, str | int]:
        """Get current state dict for prompt template."""
        ...

    def execute_command(
        self,
        command: BimanualCommand,
        steps: int,
        active_arm: Optional[str] = None,
    ) -> AttemptResult:
        """Execute a bimanual command for N sim steps.

        ``active_arm`` (V4): when ``"left"`` / ``"right"``, the inactive arm
        is held in place regardless of the VLM's emitted target.
        """
        ...

    def get_current_distances(self) -> dict[str, float]:
        """Get current distances from left and right end effectors to targets."""
        ...


@dataclass
class CollectStats:
    """Aggregate stats for a collect run."""
    total_episodes: int = 0
    success_episodes: int = 0
    vlm_parse_fails: int = 0
    critic_retries: int = 0
    total_vlm_latency_ms: float = 0.0
    run_id: str = ""


def _active_arm_for_level(level_config: LevelConfig) -> Optional[str]:
    """V4: identify which single arm is active for L0a sub-stages."""
    name = level_config.name
    if name.endswith("_left"):
        return "left"
    if name.endswith("_right"):
        return "right"
    return None


def run_collect_loop(
    config: AionGenosConfig,
    env: EnvInterface,
    curriculum: AionGenosCurriculumManager,
    replay: ReplayBuffer,
    max_episodes: int = 1000,
    check_advance_every: int = 10,
) -> CollectStats:
    """Run the 4-stage cognitive evolution collect loop.

    Args:
        config: Global config.
        env: Environment interface.
        curriculum: Curriculum manager.
        replay: Replay buffer for storage.
        max_episodes: Max episodes to collect.
        check_advance_every: Check curriculum advance every N episodes.

    Returns:
        CollectStats with aggregated metrics.
    """
    run_id = ReplayBuffer.new_run_id()
    stats = CollectStats(run_id=run_id)

    logger.info(f"Starting collect loop: run_id={run_id}, max_episodes={max_episodes}")

    for ep_idx in range(max_episodes):
        # Check if blocked
        if curriculum.is_blocked():
            logger.error("Curriculum is BLOCKED. Stopping collect loop.")
            break

        level_config = curriculum.get_current_level_config()
        episode_id = ReplayBuffer.new_episode_id()
        ep_start = time.time()

        logger.info(f"Episode {ep_idx + 1}/{max_episodes} | L{level_config.level} | {episode_id}")

        # Reset environment
        env.reset()
        vlm_interactions: list[VLMInteraction] = []
        trajectory: list[TimeStep] = []
        flags: list[str] = []

        max_rounds = level_config.max_subgoals_per_episode
        success_thresh = level_config.subgoal_success_threshold_m
        plateau_eps = level_config.plateau_min_progress_m
        plateau_patience = level_config.plateau_patience
        plateau_window = level_config.plateau_window

        conversation = EpisodeConversation(get_stage1_system_prompt())

        # Variables to track for round-based critic feedback
        prev_predicted_left = None
        prev_predicted_right = None
        prev_actual_left = None
        prev_actual_right = None
        prev_dist_l = None
        prev_dist_r = None

        rgb_start = env.get_rgb()
        rgb_end_final = rgb_start
        outcome = EpisodeOutcome.TIMEOUT
        no_progress_rounds = 0
        combined_history: list[float] = []  # T-8b rolling-mean plateau

        for round_idx in range(max_rounds):
            rgb = env.get_rgb()
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
                    dist_l_end_cm=final_dist_l * 100 if not math.isnan(final_dist_l) else 0.0,
                    dist_r_end_cm=final_dist_r * 100 if not math.isnan(final_dist_r) else 0.0,
                )
                logger.info(f"Round {round_idx + 1} Critic Feedback:\n{critic_feedback}")

            stage1_result, stage1_latency, stage1_error = run_stage1(
                level_config=level_config,
                teacher_url=config.teacher_url,
                rgb_bytes=rgb,
                state=state,
                conversation=conversation,
                critic_feedback=critic_feedback,
                max_retries=level_config.max_retry_on_parse_fail,
            )
            stats.total_vlm_latency_ms += stage1_latency

            if stage1_result is None:
                stats.vlm_parse_fails += 1
                flags.append("vlm_parse_fail")
                outcome = EpisodeOutcome.VLM_PARSE_FAIL
                logger.warning(f"  Round {round_idx + 1}/{max_rounds} parse fail → bail")
                break

            vlm_interactions.append(_make_vlm_interaction("stage1", stage1_result, stage1_latency))

            command = convert_stage1_to_commands(stage1_result, level_config.workspace_bounds)

            # Get initial state and distance before execution for the next round's feedback
            curr_dists = env.get_current_distances()
            prev_dist_l = curr_dists.get("dist_red", 0.0)
            prev_dist_r = curr_dists.get("dist_blue", 0.0)
            prev_actual_left = (state["left_x"], state["left_y"], state["left_z"])
            prev_actual_right = (state["right_x"], state["right_y"], state["right_z"])
            prev_predicted_left = (stage1_result.left.position.x, stage1_result.left.position.y, stage1_result.left.position.z)
            prev_predicted_right = (stage1_result.right.position.x, stage1_result.right.position.y, stage1_result.right.position.z)

            active_arm = _active_arm_for_level(level_config)
            attempt = env.execute_command(
                command,
                level_config.sim_steps_per_subgoal,
                active_arm=active_arm,
            )
            trajectory.extend(attempt.trajectory)
            flags.extend(attempt.flags)
            rgb_end_final = attempt.rgb_end_bytes or env.get_rgb()

            final_dist_l = float("nan")
            final_dist_r = float("nan")
            if attempt.trajectory:
                last = attempt.trajectory[-1].distances
                final_dist_l = last.get("dist_red", float("nan"))
                final_dist_r = last.get("dist_blue", float("nan"))

            combined = (final_dist_l + final_dist_r) if not (
                math.isnan(final_dist_l) or math.isnan(final_dist_r)
            ) else float("inf")

            logger.info(
                f"  Round {round_idx + 1}/{max_rounds} outcome={attempt.outcome} "
                f"final_dist L/R cm={final_dist_l*100:.1f}/{final_dist_r*100:.1f} "
                f"stop={getattr(stage1_result, 'stop', False)}"
            )

            # ── Termination checks ──
            if (
                not math.isnan(final_dist_l) and not math.isnan(final_dist_r)
                and final_dist_l < success_thresh and final_dist_r < success_thresh
            ):
                outcome = EpisodeOutcome.SUCCESS
                stats.success_episodes += 1
                break

            if attempt.outcome == "collision":
                outcome = EpisodeOutcome.COLLISION
                break

            if getattr(stage1_result, "stop", False):
                outcome = EpisodeOutcome.SUCCESS
                stats.success_episodes += 1
                break

            # T-8b Plateau detection: rolling-mean over `plateau_window` rounds
            # vs the previous window — robust to single-round oscillation that
            # the old best-combined-monotone rule mis-identified as plateau.
            if not math.isinf(combined):
                combined_history.append(combined)
            recent_mean = (
                sum(combined_history[-plateau_window:]) / plateau_window
                if len(combined_history) >= plateau_window
                else float("inf")
            )
            prior_window = combined_history[-2 * plateau_window : -plateau_window]
            prior_mean = (
                sum(prior_window) / plateau_window
                if len(prior_window) == plateau_window
                else float("inf")
            )
            if math.isinf(prior_mean):
                no_progress_rounds = 0
            elif prior_mean - recent_mean > plateau_eps:
                no_progress_rounds = 0
            else:
                no_progress_rounds += 1
                if no_progress_rounds >= plateau_patience:
                    outcome = EpisodeOutcome.TIMEOUT
                    flags.append("plateau")
                    logger.info(
                        f"  Plateau triggered: recent_mean={recent_mean*100:.1f}cm, "
                        f"prior_mean={prior_mean*100:.1f}cm, "
                        f"window={plateau_window}, patience={plateau_patience}"
                    )
                    break

        # Write replay — per-episode latency, NOT process-cumulative.
        # ``stats.total_vlm_latency_ms`` accumulates across episodes; the replay
        # schema expects this episode's total only.
        episode_latency_ms = sum(i.latency_ms for i in vlm_interactions)
        _write_episode(
            replay, episode_id, run_id, level_config, state,
            outcome, flags, trajectory, vlm_interactions,
            episode_latency_ms, rgb_start, rgb_end_final, ep_start,
        )
        curriculum.record_episode(outcome)
        stats.total_episodes += 1

        # Check curriculum advance
        if (ep_idx + 1) % check_advance_every == 0:
            advanced, msg = curriculum.check_advance()
            logger.info(f"Curriculum check: {msg}")
            if advanced:
                logger.info(f"🎯 Level advanced! Now at L{curriculum.current_level}")


    logger.info(
        f"Collect loop done: {stats.total_episodes} episodes, "
        f"{stats.success_episodes} success ({stats.success_episodes / max(1, stats.total_episodes):.1%}), "
        f"{stats.vlm_parse_fails} parse fails, {stats.critic_retries} critic retries"
    )
    return stats


def _make_vlm_interaction(stage: str, response, latency_ms: float) -> VLMInteraction:
    """Create a VLMInteraction record from a parsed response."""
    return VLMInteraction(
        stage=stage,
        full_response=getattr(response, 'thought', getattr(response, 'diagnosis', '')),
        parsed_left_pos=(response.left.position.x, response.left.position.y, response.left.position.z),
        parsed_right_pos=(response.right.position.x, response.right.position.y, response.right.position.z),
        parsed_left_rpy=(
            (response.left.rpy.r or 0, response.left.rpy.p, response.left.rpy.y)
            if response.left.rpy else None
        ),
        parsed_right_rpy=(
            (response.right.rpy.r or 0, response.right.rpy.p, response.right.rpy.y)
            if response.right.rpy else None
        ),
        parsed_left_gripper=response.left.gripper,
        parsed_right_gripper=response.right.gripper,
        parsed_stop=response.stop,
        latency_ms=latency_ms,
    )


def _write_episode(
    replay, episode_id, run_id, level_config, state,
    outcome, flags, trajectory, vlm_interactions,
    total_latency, rgb_start, rgb_end, ep_start,
):
    """Write a completed episode to the replay buffer."""
    subdir = "success" if outcome == EpisodeOutcome.SUCCESS else "failure"
    target_dir = replay.base_path / run_id / subdir
    target_dir.mkdir(parents=True, exist_ok=True)

    rgb_start_path = None
    rgb_end_path = None

    if rgb_start:
        start_filename = f"{episode_id}_start.png"
        with open(target_dir / start_filename, "wb") as f:
            f.write(rgb_start)
        rgb_start_path = f"{run_id}/{subdir}/{start_filename}"

    if rgb_end:
        end_filename = f"{episode_id}_end.png"
        with open(target_dir / end_filename, "wb") as f:
            f.write(rgb_end)
        rgb_end_path = f"{run_id}/{subdir}/{end_filename}"

    ep = ReplayEpisode(
        episode_id=episode_id,
        run_id=run_id,
        level=level_config.level,
        task_name=level_config.name,
        instruction=state.get("instruction", ""),
        outcome=outcome,
        flags=flags,
        trajectory=trajectory,
        vlm_interactions=vlm_interactions,
        episode_duration_s=time.time() - ep_start,
        total_vlm_latency_ms=total_latency,
        rgb_start_path=rgb_start_path,
        rgb_end_path=rgb_end_path,
    )
    replay.write(ep)
