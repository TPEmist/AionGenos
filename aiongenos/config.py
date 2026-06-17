"""Central configuration for AionGenos.

All runtime-configurable parameters live here. Environment variables override defaults.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Tuple

from aiongenos.vlm.task_instructions import (
    L0A_SINGLE_REACH_LEFT,
    L0A_SINGLE_REACH_RIGHT,
    L0_REACH_TWO_CUBES,
    L1_DUAL_TRACE,
    L2_DUAL_PUSH,
    L3_PICK_PLACE_CLOSE,
    L4_BLOCK_HANDOVER,
)


class ControlMode(str, Enum):
    """Control mode for each curriculum level."""

    POSITION_ONLY = "end_effector_position_only"  # L0/L1: 3-DoF (x, y, z)
    POSITION_RPY_2DOF = "end_effector_pose_with_2dof_rpy"  # L2: 5-DoF (x, y, z, pitch, yaw)
    POSITION_RPY_GRIPPER = "end_effector_pose_with_rpy"  # L3/L4: 6-DoF + 1-bit gripper


@dataclass(frozen=True)
class WorkspaceBounds:
    """Axis-aligned workspace bounds in metric (meters)."""

    x_bounds: Tuple[float, float] = (-0.3, 0.6)
    y_bounds: Tuple[float, float] = (-0.4, 0.4)
    z_bounds: Tuple[float, float] = (0.0, 0.7)


@dataclass(frozen=True)
class ScalarGuardConfig:
    """Scalar guard integer grid configuration."""

    int_range: Tuple[int, int] = (-100, 100)
    rpy_metric_range_roll: Tuple[float, float] = (-3.14159265, 3.14159265)
    rpy_metric_range_pitch: Tuple[float, float] = (-1.57079633, 1.57079633)
    rpy_metric_range_yaw: Tuple[float, float] = (-3.14159265, 3.14159265)
    near_singularity_pitch_threshold: int = 80  # |P| > 80 → near_singularity


@dataclass(frozen=True)
class CurriculumConfig:
    """Curriculum advancement parameters."""

    advance_threshold: float = 0.6  # success rate ≥ 60% to unlock next level
    # Plan §M5 set this to 12 h / 100 successes as a production "stuck-on-this-level"
    # guard. During R&D we frequently want to run a single level long enough to
    # measure the SR distribution even when SR is low (D5 hit BLOCKED at 13 h /
    # 3 successes, which was the sentinel doing its job). Bumped to 48 h while
    # we're tuning the loop; tighten back to 12 h once teacher SR clears 30%.
    blocked_timeout_hours: float = 48.0
    min_success_episodes: int = 100


@dataclass
class LevelConfig:
    """Per-level configuration."""

    level: int
    name: str
    control_mode: ControlMode
    task_instruction_template: str
    workspace_bounds: WorkspaceBounds = field(default_factory=WorkspaceBounds)
    episode_length_s: float = 24.0
    # T-8c: 60→30 (1Hz→2Hz VLM frequency, plan §3.5.5 path).
    sim_steps_per_subgoal: int = 30  # ≈ 0.5 s at 60 Hz sim
    max_retry_on_parse_fail: int = 2
    max_critic_retries: int = 1  # Stage 3 retry after critic

    # Multi-round closed-loop within an episode (Option A, 2026-06-03).
    # VLM is re-queried with fresh RGB + EE state each round until success / plateau / cap.
    # T-8(a) → V1: 15 → 25 → 40 (longer rounds; offsets the 0.5s/round shrink).
    max_subgoals_per_episode: int = 40
    # D1 (2026-06-11) loosened the gate 5→6cm to capture run 0602e905
    # ep 0eda8269's R10/R12 (5.4-5.9cm) as success. Run b6783e98 (D3)
    # then showed an ugly side effect: 3/10 ep emitted vlm_stop_premature
    # mid-episode (F34) — VLM saw dist drop into the looser band and
    # decided "good enough", short-circuiting further refinement. Combined
    # with F33 (active-arm criteria not respected) the experiment was
    # confounded. Reverting to 0.05 m here so F33+F35 can be evaluated
    # cleanly; revisit threshold loosening *after* a successful baseline.
    subgoal_success_threshold_m: float = 0.05  # both arms < threshold → success
    plateau_min_progress_m: float = 0.01  # < 1 cm improvement counted as no progress
    # T-8b: plateau patience now denotes consecutive rounds where the rolling
    # mean (over `plateau_window`) failed to improve by `plateau_min_progress_m`.
    plateau_patience: int = 5
    plateau_window: int = 3  # rolling-window size for mean-progress evaluation


# Pre-defined level configs.
#
# Negative-numbered levels are pre-L0 sub-stages added by V4 (sensory-
# integration ordering: master single-channel before dual-channel). The
# advancement order is encoded in ``LEVEL_ORDER`` below — the curriculum
# manager treats that list as the source of truth, not the integer values.
LEVEL_CONFIGS: dict[int, LevelConfig] = {
    -2: LevelConfig(
        level=-2,
        name="L0a_single_reach_left",
        control_mode=ControlMode.POSITION_ONLY,
        task_instruction_template=L0A_SINGLE_REACH_LEFT,
        max_subgoals_per_episode=40,
        plateau_patience=5,
    ),
    -1: LevelConfig(
        level=-1,
        name="L0a_single_reach_right",
        control_mode=ControlMode.POSITION_ONLY,
        task_instruction_template=L0A_SINGLE_REACH_RIGHT,
        max_subgoals_per_episode=40,
        plateau_patience=5,
    ),
    0: LevelConfig(
        level=0,
        name="L0_reach_two_cubes",
        control_mode=ControlMode.POSITION_ONLY,
        task_instruction_template=L0_REACH_TWO_CUBES,
        max_subgoals_per_episode=40,  # V1: 25→40
        plateau_patience=5,
    ),
    1: LevelConfig(
        level=1,
        name="L1_dual_trace",
        control_mode=ControlMode.POSITION_ONLY,
        task_instruction_template=L1_DUAL_TRACE,
        max_subgoals_per_episode=40,
        plateau_patience=5,
    ),
    2: LevelConfig(
        level=2,
        name="L2_dual_push",
        control_mode=ControlMode.POSITION_RPY_2DOF,
        task_instruction_template=L2_DUAL_PUSH,
        max_subgoals_per_episode=40,
        plateau_patience=5,
    ),
    3: LevelConfig(
        level=3,
        name="L3_pick_place_close",
        control_mode=ControlMode.POSITION_RPY_GRIPPER,
        task_instruction_template=L3_PICK_PLACE_CLOSE,
        max_subgoals_per_episode=40,
        plateau_patience=5,
    ),
    4: LevelConfig(
        level=4,
        name="L4_block_handover",
        control_mode=ControlMode.POSITION_RPY_GRIPPER,
        task_instruction_template=L4_BLOCK_HANDOVER,
        max_subgoals_per_episode=40,
        plateau_patience=5,
    ),
}


# Curriculum advancement order. Negative ids are V4 sub-stages, traversed
# before L0 (sensory-integration: single-channel → dual-channel).
LEVEL_ORDER: tuple[int, ...] = (-2, -1, 0, 1, 2, 3, 4)


@dataclass
class AionGenosConfig:
    """Top-level AionGenos runtime configuration."""

    # Server endpoints
    teacher_url: str = field(
        default_factory=lambda: os.environ.get("TEACHER_URL", "http://10.80.9.148:18888")
    )
    student_url: str = field(
        default_factory=lambda: os.environ.get("STUDENT_URL", "http://10.80.9.148:18889")
    )

    # Replay paths
    local_replay_path: Path = field(
        default_factory=lambda: Path(os.environ.get("LOCAL_REPLAY_PATH", "./data/replays"))
    )
    remote_host: str = field(
        default_factory=lambda: os.environ.get("REMOTE_HOST", "10.80.9.148")
    )
    remote_user: str = field(
        default_factory=lambda: os.environ.get("REMOTE_USER", "exx")
    )
    remote_replay_path: str = field(
        default_factory=lambda: os.environ.get("REMOTE_REPLAY_PATH", "~/CYTu/AionGenos_server/data/replays")
    )
    remote_python: str = field(
        default_factory=lambda: os.environ.get("REMOTE_PYTHON", "python3")
    )


    # Workspace & scalar guard
    workspace_bounds: WorkspaceBounds = field(default_factory=WorkspaceBounds)
    scalar_guard: ScalarGuardConfig = field(default_factory=ScalarGuardConfig)

    # Curriculum
    curriculum: CurriculumConfig = field(default_factory=CurriculumConfig)

    # Simulation
    num_envs: int = 16  # POC scale
    sim_dt: float = 1.0 / 120.0  # 120 Hz sim
    decimation: int = 2  # → 60 Hz control
    render_width: int = 128
    render_height: int = 128

    def get_level_config(self, level: int) -> LevelConfig:
        """Get configuration for a curriculum level."""
        if level not in LEVEL_CONFIGS:
            raise ValueError(f"Unknown curriculum level: {level}. Valid: {list(LEVEL_CONFIGS.keys())}")
        return LEVEL_CONFIGS[level]
