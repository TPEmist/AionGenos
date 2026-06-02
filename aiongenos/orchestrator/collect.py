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
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Protocol

from aiongenos.config import AionGenosConfig, LevelConfig
from aiongenos.curriculum.manager import AionGenosCurriculumManager
from aiongenos.pipeline.stage1_reasoning import run_stage1
from aiongenos.pipeline.stage2_attempt import (
    AttemptResult,
    convert_stage1_to_commands,
    convert_stage3_to_commands,
    BimanualCommand,
)
from aiongenos.pipeline.stage3_critic import run_stage3
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

    def execute_command(self, command: BimanualCommand, steps: int) -> AttemptResult:
        """Execute a bimanual command for N sim steps."""
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

        # ── Stage 1: Reasoning ──
        rgb_start = env.get_rgb()
        state = env.get_state(level_config)
        try:
            state["instruction"] = level_config.task_instruction_template.format(**state)
        except Exception:
            state["instruction"] = level_config.task_instruction_template

        stage1_result, stage1_latency, stage1_error = run_stage1(
            level_config=level_config,
            teacher_url=config.teacher_url,
            rgb_bytes=rgb_start,
            state=state,
            max_retries=level_config.max_retry_on_parse_fail,
        )

        stats.total_vlm_latency_ms += stage1_latency

        if stage1_result is None:
            # VLM parse failure → mark and continue
            stats.vlm_parse_fails += 1
            flags.append("vlm_parse_fail")
            outcome = EpisodeOutcome.VLM_PARSE_FAIL
            _write_episode(
                replay, episode_id, run_id, level_config, state,
                outcome, flags, trajectory, vlm_interactions,
                stage1_latency, rgb_start, rgb_start, ep_start,
            )
            curriculum.record_episode(outcome)
            stats.total_episodes += 1
            continue

        # Record Stage 1 interaction
        vlm_interactions.append(_make_vlm_interaction("stage1", stage1_result, stage1_latency))

        # ── Stage 2: Attempt ──
        command = convert_stage1_to_commands(stage1_result, level_config.workspace_bounds)
        attempt = env.execute_command(command, level_config.sim_steps_per_subgoal)
        trajectory.extend(attempt.trajectory)
        flags.extend(attempt.flags)

        if attempt.outcome == "success":
            outcome = EpisodeOutcome.SUCCESS
            stats.success_episodes += 1
        else:
            # ── Stage 3: Critic (on failure) ──
            failure_label = attempt.outcome
            rgb_end = attempt.rgb_end_bytes or env.get_rgb()

            stage3_result, stage3_latency, stage3_error = run_stage3(
                level_config=level_config,
                teacher_url=config.teacher_url,
                instruction=level_config.task_instruction_template,
                failure_label=failure_label,
                trajectory=trajectory,
                rgb_start_bytes=rgb_start,
                rgb_end_bytes=rgb_end,
            )

            stats.total_vlm_latency_ms += stage3_latency
            stats.critic_retries += 1

            if stage3_result is not None:
                vlm_interactions.append(_make_vlm_interaction("stage3", stage3_result, stage3_latency))

                # Retry with revised commands
                revised_command = convert_stage3_to_commands(stage3_result, level_config.workspace_bounds)
                retry_attempt = env.execute_command(revised_command, level_config.sim_steps_per_subgoal)
                trajectory.extend(retry_attempt.trajectory)
                flags.extend(retry_attempt.flags)
                flags.append("critic_retry")

                if retry_attempt.outcome == "success":
                    outcome = EpisodeOutcome.SUCCESS
                    stats.success_episodes += 1
                else:
                    outcome = EpisodeOutcome(retry_attempt.outcome) if retry_attempt.outcome in EpisodeOutcome.__members__.values() else EpisodeOutcome.TIMEOUT
            else:
                outcome = EpisodeOutcome(failure_label) if failure_label in [e.value for e in EpisodeOutcome] else EpisodeOutcome.TIMEOUT

        # Write replay
        rgb_end_final = attempt.rgb_end_bytes or env.get_rgb()
        _write_episode(
            replay, episode_id, run_id, level_config, state,
            outcome, flags, trajectory, vlm_interactions,
            stats.total_vlm_latency_ms, rgb_start, rgb_end_final, ep_start,
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
