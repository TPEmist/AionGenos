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

import json
import logging
import math
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
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
    dump_images_root: Optional[Path] = None,
    memory_retriever: "Optional[object]" = None,
    recap_buffer: "Optional[object]" = None,
) -> CollectStats:
    """Run the 4-stage cognitive evolution collect loop.

    Args:
        config: Global config.
        env: Environment interface.
        curriculum: Curriculum manager.
        replay: Replay buffer for storage.
        max_episodes: Max episodes to collect.
        check_advance_every: Check curriculum advance every N episodes.
        dump_images_root: When set, write per-round RGB pairs (and a meta.json
            summarising VLM I/O per round) under
            ``{dump_images_root}/{run_id}/{episode_id}/round_NN_{pre,post}.png``
            for offline playback / debugging.
        memory_retriever: Optional Phase 4 ``MemoryRetriever``. When provided,
            at R1 of every episode the top-K visually similar past recaps are
            retrieved and their (text + init image) injected as the prompt
            preamble for the FIRST run_stage1 call only.
        recap_buffer: Optional Phase 4 ``RecapBuffer``. When provided, every
            episode emits a recap at the end (regardless of success/failure)
            and persists it into the buffer for future retrieval.

    Returns:
        CollectStats with aggregated metrics.
    """
    run_id = ReplayBuffer.new_run_id()
    stats = CollectStats(run_id=run_id)

    logger.info(f"Starting collect loop: run_id={run_id}, max_episodes={max_episodes}")
    if dump_images_root is not None:
        logger.info(f"  dump_images_root={dump_images_root / run_id}")

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

        # F19/V4 playback support: per-round RGB + meta dump.
        ep_dump_dir: Optional[Path] = None
        round_meta: list[dict] = []
        if dump_images_root is not None:
            ep_dump_dir = dump_images_root / run_id / episode_id
            ep_dump_dir.mkdir(parents=True, exist_ok=True)
            if rgb_start:
                (ep_dump_dir / "episode_start.png").write_bytes(rgb_start)

        # Phase 4: Retrieve top-K past similar episodes at ep start (Q13).
        # The retrieved (text + past images) is injected only into round 0's
        # run_stage1 call via the conversation's preamble slot.
        memory_preamble_text: Optional[str] = None
        memory_preamble_images_b64: Optional[list[str]] = None
        if memory_retriever is not None and rgb_start:
            try:
                init_state = env.get_state(level_config)
                init_L = (
                    int(init_state["left_x"]),
                    int(init_state["left_y"]),
                    int(init_state["left_z"]),
                )
                preamble = memory_retriever.retrieve_for_episode(
                    init_rgb_bytes=rgb_start,
                    init_L_EE=init_L,
                    exclude_run_ids={run_id},
                )
                if not preamble.is_empty:
                    memory_preamble_text = preamble.prelude_text
                    memory_preamble_images_b64 = preamble.past_image_base64_list
                    sims_str = ",".join(f"{s:.2f}" for s in preamble.similarities)
                    eps_str = ",".join(r.ep_id[:8] for r in preamble.retrieved_records)
                    logger.info(f"  memory: injected {len(preamble.retrieved_records)} past eps [{eps_str}] sims=[{sims_str}]")
                else:
                    logger.info("  memory: buffer empty or all candidates filtered, no preamble injected")
            except Exception as e:
                logger.warning(f"  memory retrieval failed (continuing without): {e}")

        for round_idx in range(max_rounds):
            rgb = env.get_rgb()
            if ep_dump_dir is not None and rgb:
                (ep_dump_dir / f"round_{round_idx + 1:02d}_pre.png").write_bytes(rgb)
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

            # Phase 4: only round 0 receives the retrieved-memory preamble.
            # Subsequent rounds use the existing conversation history; the
            # preamble is fused into the first user turn once and stays there
            # via the conversation pruning (which preserves messages[0]).
            r1_preamble_text = memory_preamble_text if round_idx == 0 else None
            r1_preamble_imgs = memory_preamble_images_b64 if round_idx == 0 else None

            stage1_result, stage1_latency, stage1_error = run_stage1(
                level_config=level_config,
                teacher_url=config.teacher_url,
                rgb_bytes=rgb,
                state=state,
                conversation=conversation,
                critic_feedback=critic_feedback,
                max_retries=level_config.max_retry_on_parse_fail,
                memory_preamble_text=r1_preamble_text,
                memory_preamble_images_b64=r1_preamble_imgs,
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

            if ep_dump_dir is not None and attempt.rgb_end_bytes:
                (ep_dump_dir / f"round_{round_idx + 1:02d}_post.png").write_bytes(
                    attempt.rgb_end_bytes
                )

            final_dist_l = float("nan")
            final_dist_r = float("nan")
            if attempt.trajectory:
                last = attempt.trajectory[-1].distances
                final_dist_l = last.get("dist_red", float("nan"))
                final_dist_r = last.get("dist_blue", float("nan"))

            if ep_dump_dir is not None:
                round_meta.append({
                    "round": round_idx + 1,
                    "active_arm": active_arm,
                    "vlm_left_pos_int": list(prev_predicted_left or ()),
                    "vlm_right_pos_int": list(prev_predicted_right or ()),
                    "command_left_pos_m": [float(v) for v in command.left.position],
                    "command_right_pos_m": [float(v) for v in command.right.position],
                    "actual_left_start": list(prev_actual_left or ()),
                    "actual_right_start": list(prev_actual_right or ()),
                    "final_dist_l_cm": float(final_dist_l * 100) if not math.isnan(final_dist_l) else None,
                    "final_dist_r_cm": float(final_dist_r * 100) if not math.isnan(final_dist_r) else None,
                    # Full thought (NOT truncated). The thought is the most
                    # information-rich signal we have for diagnosing whether
                    # the VLM is actually reasoning vs. running a fallback,
                    # so we keep it intact in meta.json.
                    "vlm_thought": getattr(stage1_result, "thought", "") or "",
                    # Full raw response (regex-parser source) — useful when
                    # debugging parse failures or comparing thought vs. emitted
                    # coordinates.
                    "vlm_full_response": (
                        vlm_interactions[-1].full_response
                        if vlm_interactions else ""
                    ),
                    # Programmatic critic feedback that was injected as the
                    # "### CRITIC FEEDBACK FROM PREVIOUS ROUND" suffix on the
                    # round's user prompt; None on round 1.
                    "critic_feedback": critic_feedback,
                    "vlm_stop": bool(getattr(stage1_result, "stop", False)),
                    "attempt_outcome": attempt.outcome,
                    "stage1_latency_ms": float(stage1_latency),
                })

            combined = (final_dist_l + final_dist_r) if not (
                math.isnan(final_dist_l) or math.isnan(final_dist_r)
            ) else float("inf")

            logger.info(
                f"  Round {round_idx + 1}/{max_rounds} outcome={attempt.outcome} "
                f"final_dist L/R cm={final_dist_l*100:.1f}/{final_dist_r*100:.1f} "
                f"stop={getattr(stage1_result, 'stop', False)}"
            )

            # ── Termination checks ──
            # F33: success criteria must respect active_arm. For L0a
            # sub-stages the inactive arm is held in place by the env
            # interface, so its dist is the random initial-spawn offset
            # to the (also random) target — typically 12-25cm and never
            # under threshold. Asking "both arms < threshold" therefore
            # makes L0a structurally 0% even when the active arm is
            # converged. Bimanual levels (L0..L4) keep the stricter
            # both-arms gate.
            if active_arm == "left":
                ok = (not math.isnan(final_dist_l)) and final_dist_l < success_thresh
            elif active_arm == "right":
                ok = (not math.isnan(final_dist_r)) and final_dist_r < success_thresh
            else:
                ok = (
                    not math.isnan(final_dist_l) and not math.isnan(final_dist_r)
                    and final_dist_l < success_thresh
                    and final_dist_r < success_thresh
                )
            if ok:
                outcome = EpisodeOutcome.SUCCESS
                stats.success_episodes += 1
                break

            if attempt.outcome == "collision":
                outcome = EpisodeOutcome.COLLISION
                break

            if getattr(stage1_result, "stop", False):
                # F19 fix: VLM saying STOP=True does NOT imply success — verify
                # against distance threshold. The earlier "real" success branch
                # above already covers genuine convergence; if we get here, the
                # VLM thinks it's done but the EE isn't on target.
                outcome = EpisodeOutcome.VLM_STOP_PREMATURE
                flags.append("vlm_stop_premature")
                logger.info(
                    f"  VLM emitted STOP=True at round {round_idx + 1} but "
                    f"final dist L/R cm={final_dist_l*100:.1f}/{final_dist_r*100:.1f} > threshold "
                    f"{success_thresh*100:.1f}cm → mark vlm_stop_premature"
                )
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

        # Persist per-round dump meta.json alongside the PNGs (V4 playback).
        if ep_dump_dir is not None:
            if rgb_end_final:
                (ep_dump_dir / "episode_end.png").write_bytes(rgb_end_final)
            (ep_dump_dir / "meta.json").write_text(
                json.dumps(
                    {
                        "episode_id": episode_id,
                        "run_id": run_id,
                        "level": level_config.level,
                        "level_name": level_config.name,
                        "outcome": outcome.value if hasattr(outcome, "value") else str(outcome),
                        "flags": list(flags),
                        "rounds": round_meta,
                    },
                    indent=2,
                )
            )

        # Phase 4: post-episode self-recap (Q1 — always written).
        if recap_buffer is not None:
            try:
                _emit_recap_for_episode(
                    recap_buffer=recap_buffer,
                    ep_id=episode_id,
                    run_id=run_id,
                    outcome=outcome,
                    level_config=level_config,
                    trajectory=trajectory,
                    vlm_interactions=vlm_interactions,
                    round_meta=round_meta,
                    ep_dump_dir=ep_dump_dir,
                    rgb_start_bytes=rgb_start,
                    rgb_end_bytes=rgb_end_final,
                    teacher_url=config.teacher_url,
                )
            except Exception as e:
                logger.warning(f"  recap generation failed (continuing): {e}")

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


# ─────────────────────── Phase 4: post-episode recap glue ───────────────────────

def _emit_recap_for_episode(
    *,
    recap_buffer,
    ep_id: str,
    run_id: str,
    outcome,
    level_config: LevelConfig,
    trajectory: list,
    vlm_interactions: list,
    round_meta: list,
    ep_dump_dir: Optional[Path],
    rgb_start_bytes: Optional[bytes],
    rgb_end_bytes: Optional[bytes],
    teacher_url: str,
) -> None:
    """Glue between the collect loop and ``stage4_recap.generate_recap``.

    Imports are local so that orchestrator stays importable in environments
    without torchvision (used for image embedding).
    """
    from aiongenos.pipeline.stage4_recap import generate_recap, _RoundInfo

    active_arm = _active_arm_for_level(level_config)

    init_L = (0, 0, 0)
    final_L = (0, 0, 0)
    init_R: Optional[tuple] = None
    final_R: Optional[tuple] = None
    if trajectory:
        first_ts = trajectory[0]
        last_ts = trajectory[-1]
        init_L = tuple(getattr(first_ts, "left_ee_pos", None) or (0, 0, 0))
        final_L = tuple(getattr(last_ts, "left_ee_pos", None) or (0, 0, 0))
        ir = getattr(first_ts, "right_ee_pos", None)
        fr = getattr(last_ts, "right_ee_pos", None)
        if ir:
            init_R = tuple(ir)
        if fr:
            final_R = tuple(fr)

    # Adapt round_meta + vlm_interactions into RoundInfo
    stage1s = [i for i in vlm_interactions if getattr(i, "stage", None) == "stage1"]
    n = min(len(stage1s), len(round_meta)) if round_meta else len(stage1s)
    rounds: list = []
    for i in range(n):
        s1 = stage1s[i]
        meta = round_meta[i] if i < len(round_meta) else {}
        if active_arm == "right":
            dist = meta.get("final_dist_r_cm")
        else:
            dist = meta.get("final_dist_l_cm")
        pre_png = None
        if ep_dump_dir is not None:
            cand = Path(ep_dump_dir) / f"round_{i + 1:02d}_pre.png"
            if cand.exists():
                pre_png = cand
        rounds.append(_RoundInfo(
            round_idx=i + 1,
            pre_png=pre_png,
            final_dist_cm=float(dist) if dist is not None else float("nan"),
            parsed_left_pos=list(getattr(s1, "parsed_left_pos", None) or []) or None,
        ))

    if not rounds:
        logger.info(f"  recap({ep_id}): no rounds (parse fail?), skip")
        return

    outcome_str = outcome.value if hasattr(outcome, "value") else str(outcome)
    rec = generate_recap(
        ep_id=ep_id,
        run_id=run_id,
        outcome=outcome_str,
        active_arm=active_arm,
        instruction=level_config.task_instruction_template,
        init_L_EE=init_L,
        final_L_EE=final_L,
        init_R_EE=init_R,
        final_R_EE=final_R,
        rounds=rounds,
        ep_dump_dir=ep_dump_dir,
        rgb_start_bytes=rgb_start_bytes,
        rgb_end_bytes=rgb_end_bytes,
        teacher_url=teacher_url,
        buffer=recap_buffer,
        embedder_device="cpu",
    )
    if rec is None:
        logger.warning(f"  recap({ep_id}): generation returned None")
