"""Stage 2 — Attempt (Heuristic Exploration).

Converts VLM integer sub-goals to metric commands, executes via IK servo
in simulation, and records trajectory + outcome.

NOTE: This module defines the interface and logic flow. The actual IsaacLab
env interaction requires Isaac Sim runtime and will be wired in the
orchestrator's collect loop.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from aiongenos.config import LevelConfig, WorkspaceBounds
from aiongenos.vlm.parser import Stage1Response, Stage3Response, VLMAction
from aiongenos.vlm.scalar_guard import int_to_metric, int_to_rpy_rad
from aiongenos.control.rotation import rpy_rad_to_quat
from aiongenos.replay.schema import TimeStep

logger = logging.getLogger(__name__)


@dataclass
class MetricCommand:
    """Metric-space command for one arm."""
    position: tuple[float, float, float]  # (x, y, z) in meters
    quaternion: Optional[tuple[float, float, float, float]] = None  # (w, x, y, z), L2+
    gripper_close: Optional[bool] = None  # L3+


@dataclass
class BimanualCommand:
    """Commands for both arms."""
    left: MetricCommand
    right: MetricCommand


@dataclass
class AttemptResult:
    """Result of a Stage 2 attempt."""
    trajectory: list[TimeStep] = field(default_factory=list)
    outcome: str = "timeout"  # success/timeout/collision/out_of_workspace/object_lost
    flags: list[str] = field(default_factory=list)
    rgb_start_bytes: Optional[bytes] = None
    rgb_end_bytes: Optional[bytes] = None


def vlm_action_to_metric(
    action: VLMAction,
    bounds: WorkspaceBounds,
) -> MetricCommand:
    """Convert a VLM integer action to metric-space command.

    Args:
        action: Parsed VLM action (integer coordinates).
        bounds: Workspace bounds for de-normalization.

    Returns:
        MetricCommand with metric position and optional rotation/gripper.
    """
    # Position: int → metric
    x = int_to_metric(action.position.x, bounds.x_bounds)
    y = int_to_metric(action.position.y, bounds.y_bounds)
    z = int_to_metric(action.position.z, bounds.z_bounds)

    # Rotation: if RPY is present
    quat = None
    if action.rpy is not None:
        r_int = action.rpy.r if action.rpy.r is not None else 0
        p_int = action.rpy.p
        y_int = action.rpy.y
        roll, pitch, yaw = int_to_rpy_rad(r_int, p_int, y_int)
        quat = rpy_rad_to_quat(roll, pitch, yaw)

    # Gripper
    gripper_close = None
    if action.gripper is not None:
        gripper_close = action.gripper == "closed"

    return MetricCommand(
        position=(x, y, z),
        quaternion=quat,
        gripper_close=gripper_close,
    )


def convert_stage1_to_commands(
    response: Stage1Response,
    bounds: WorkspaceBounds,
) -> BimanualCommand:
    """Convert a full Stage 1 response to bimanual metric commands."""
    return BimanualCommand(
        left=vlm_action_to_metric(response.left, bounds),
        right=vlm_action_to_metric(response.right, bounds),
    )


def convert_stage3_to_commands(
    response: Stage3Response,
    bounds: WorkspaceBounds,
) -> BimanualCommand:
    """Convert a Stage 3 critic response to bimanual metric commands."""
    return BimanualCommand(
        left=vlm_action_to_metric(response.left, bounds),
        right=vlm_action_to_metric(response.right, bounds),
    )
