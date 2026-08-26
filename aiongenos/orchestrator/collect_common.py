"""Shared collect helpers — ONE copy used by BOTH collect instruments
(collect.py for P1 reach/L2, push_collect.py for P2 push).

Extracted 2026-08-25 by PURE RELOCATION from collect.py: the three functions
below are byte-for-byte identical to their originals (verified by per-function
SHA). This module exists so the two instruments share a single implementation
of these guarantees rather than drifting (see docs/p2_prereg/
dual_collect_equivalence_ledger.md). No behaviour change; collect.py now
imports these instead of defining them.

If push needs different behaviour, ADD a new function or a defaulted parameter
here — never edit an existing signature/body (that would break the P1
instrument, frozen with the submission)."""

from __future__ import annotations

import time
from typing import Optional

from aiongenos.config import LevelConfig
from aiongenos.replay.schema import (
    EpisodeOutcome,
    ReplayEpisode,
    VLMInteraction,
)


def _active_arm_for_level(level_config: LevelConfig) -> Optional[str]:
    """V4: identify which single arm is active for L0a sub-stages."""
    name = level_config.name
    if name.endswith("_left"):
        return "left"
    if name.endswith("_right"):
        return "right"
    return None


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
