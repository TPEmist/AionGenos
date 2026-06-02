"""Central configuration for AionGenos.

All runtime-configurable parameters live here. Environment variables override defaults.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Tuple


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
    blocked_timeout_hours: float = 12.0
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
    sim_steps_per_subgoal: int = 60  # ≈ 1 s at 60 Hz sim
    max_retry_on_parse_fail: int = 2
    max_critic_retries: int = 1  # Stage 3 retry after critic


# Pre-defined level configs
LEVEL_CONFIGS: dict[int, LevelConfig] = {
    0: LevelConfig(
        level=0,
        name="L0_reach_two_cubes",
        control_mode=ControlMode.POSITION_ONLY,
        task_instruction_template=(
            "Move both end-effectors to the target positions. "
            "Left arm should reach the {left_target_color} target, "
            "right arm should reach the {right_target_color} target."
        ),
    ),
    1: LevelConfig(
        level=1,
        name="L1_dual_trace",
        control_mode=ControlMode.POSITION_ONLY,
        task_instruction_template=(
            "Follow the waypoint trajectory with both arms. "
            "Left arm traces {left_trace_shape}, right arm traces {right_trace_shape}."
        ),
    ),
    2: LevelConfig(
        level=2,
        name="L2_dual_push",
        control_mode=ControlMode.POSITION_RPY_2DOF,
        task_instruction_template=(
            "Push the {object_color} block to the {target_color} zone using both arms cooperatively."
        ),
    ),
    3: LevelConfig(
        level=3,
        name="L3_pick_place_close",
        control_mode=ControlMode.POSITION_RPY_GRIPPER,
        task_instruction_template=(
            "Pick up the {object_color} object with one arm and place it at the {target_color} zone."
        ),
    ),
    4: LevelConfig(
        level=4,
        name="L4_block_handover",
        control_mode=ControlMode.POSITION_RPY_GRIPPER,
        task_instruction_template=(
            "Pick up the {object_color} block with the left arm, "
            "hand it over to the right arm, and place it at the {target_color} zone."
        ),
    ),
}


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
        default_factory=lambda: os.environ.get("REMOTE_USER", "user")
    )
    remote_replay_path: str = field(
        default_factory=lambda: os.environ.get("REMOTE_REPLAY_PATH", "/data/replays")
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
