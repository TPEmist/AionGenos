"""Replay episode schema — TypedDict + JSON schema, schema_version=1.

Defines the canonical replay episode format stored as JSON + optional NPZ.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


SCHEMA_VERSION = 1


class EpisodeOutcome(str, Enum):
    SUCCESS = "success"
    TIMEOUT = "timeout"
    COLLISION = "collision"
    OUT_OF_WORKSPACE = "out_of_workspace"
    OBJECT_LOST = "object_lost"
    VLM_PARSE_FAIL = "vlm_parse_fail"
    NEAR_SINGULARITY = "near_singularity"
    # F19: VLM emitted STOP=True before reaching the success threshold.
    # Treated as failure for replay purposes (does NOT enter Stage 4-A
    # training data) so the success_replay/ folder stays clean.
    VLM_STOP_PREMATURE = "vlm_stop_premature"


class TimeStep(BaseModel):
    """Single timestep observation in a trajectory."""
    t: float  # time in seconds
    left_ee_pos: tuple[int, int, int]  # integer grid
    right_ee_pos: tuple[int, int, int]
    left_ee_rpy: Optional[tuple[int, int, int]] = None  # L2+
    right_ee_rpy: Optional[tuple[int, int, int]] = None
    left_gripper: Optional[str] = None  # "open" / "closed", L3+
    right_gripper: Optional[str] = None
    # Derived observables (from RGB, not hidden sensors)
    distances: Optional[dict[str, float]] = None  # e.g. {"dist_red": 12, "dist_green": 45}


class VLMInteraction(BaseModel):
    """Record of a single VLM call (Stage 1 or Stage 3)."""
    stage: str  # "stage1" or "stage3"
    prompt_hash: Optional[str] = None  # for dedup
    full_response: str  # raw VLM text (with THOUGHT for CoT preservation)
    parsed_left_pos: tuple[int, int, int]
    parsed_right_pos: tuple[int, int, int]
    parsed_left_rpy: Optional[tuple[int, int, int]] = None
    parsed_right_rpy: Optional[tuple[int, int, int]] = None
    parsed_left_gripper: Optional[str] = None
    parsed_right_gripper: Optional[str] = None
    parsed_stop: bool = False
    latency_ms: float = 0.0


class ReplayEpisode(BaseModel):
    """Full replay episode record."""
    schema_version: int = SCHEMA_VERSION
    episode_id: str
    run_id: str
    level: int
    task_name: str
    instruction: str
    outcome: EpisodeOutcome
    flags: list[str] = Field(default_factory=list)  # ["near_singularity", "clamped", etc.]

    # Trajectory
    trajectory: list[TimeStep] = Field(default_factory=list)

    # VLM interactions (Stage 1 + optional Stage 3 retries)
    vlm_interactions: list[VLMInteraction] = Field(default_factory=list)

    # Timing
    episode_duration_s: float = 0.0
    total_vlm_latency_ms: float = 0.0

    # RGB paths (relative to replay dir)
    rgb_start_path: Optional[str] = None
    rgb_end_path: Optional[str] = None

    # Metadata
    metadata: dict[str, Any] = Field(default_factory=dict)


# ──────────── Observable-only whitelist (Stage 3 input validation) ──────────

# Keys that are ALLOWED in Stage 3 critic input
OBSERVABLE_WHITELIST = frozenset({
    "t",
    "left_ee_pos",
    "right_ee_pos",
    "left_ee_rpy",
    "right_ee_rpy",
    "left_gripper",
    "right_gripper",
    "distances",
    # Derived from RGB
    "rgb_start",
    "rgb_end",
    # Task info
    "instruction",
    "failure_label",
    "trajectory_text",
})

# Keys that are FORBIDDEN in Stage 3 critic input (hidden sensors)
HIDDEN_SENSOR_BLACKLIST = frozenset({
    "contact_force",
    "joint_torque",
    "motor_current",
    "applied_wrench",
    "friction_coefficient",
    "object_mass",
    "object_inertia",
    "object_material",
    "depth_image",
    "semantic_mask",
    "point_cloud",
})


def validate_critic_input(input_dict: dict[str, Any]) -> bool:
    """Validate that critic input contains ONLY observable data.

    Raises:
        ValueError: If any hidden sensor key is found.

    Returns:
        True if valid.
    """
    for key in input_dict:
        if key in HIDDEN_SENSOR_BLACKLIST:
            raise ValueError(
                f"Hidden sensor '{key}' found in critic input! "
                f"Stage 3 must use ONLY observable data."
            )
    return True
