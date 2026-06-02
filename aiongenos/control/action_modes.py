"""Per-level control mode switching and IK config builder.

Builds the appropriate IsaacLab DifferentialInverseKinematicsActionCfg
based on the current curriculum level's control_mode setting.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from aiongenos.config import ControlMode, LevelConfig


@dataclass
class ActionModeSpec:
    """Specifies the action dimensionality and IK command type for a level."""

    command_type: str  # "position" or "pose"
    use_relative_mode: bool
    dims_per_arm: int  # 3 (pos only), 5 (pos + 2DoF RPY), 6 (pos + RPY)
    has_gripper: bool
    description: str


# Mapping from ControlMode to ActionModeSpec
ACTION_MODE_MAP: dict[ControlMode, ActionModeSpec] = {
    ControlMode.POSITION_ONLY: ActionModeSpec(
        command_type="position",
        use_relative_mode=False,
        dims_per_arm=3,
        has_gripper=False,
        description="L0/L1: EE position-only (x, y, z), no wrist rotation",
    ),
    ControlMode.POSITION_RPY_2DOF: ActionModeSpec(
        command_type="pose",
        use_relative_mode=False,
        dims_per_arm=5,
        has_gripper=False,
        description="L2: EE position + 2-DoF approach angle (pitch, yaw)",
    ),
    ControlMode.POSITION_RPY_GRIPPER: ActionModeSpec(
        command_type="pose",
        use_relative_mode=False,
        dims_per_arm=6,
        has_gripper=True,
        description="L3/L4: EE position + 3-DoF Euler RPY + binary gripper",
    ),
}


def get_action_mode(level_config: LevelConfig) -> ActionModeSpec:
    """Get the action mode specification for a curriculum level.

    Args:
        level_config: The level configuration.

    Returns:
        ActionModeSpec for the level.

    Raises:
        KeyError: If control mode is unknown.
    """
    return ACTION_MODE_MAP[level_config.control_mode]


def build_ik_action_cfg_dict(level_config: LevelConfig) -> dict[str, Any]:
    """Build a dict of IK action config parameters for IsaacLab.

    This returns a serializable dict rather than an IsaacLab cfg object
    to avoid hard-coupling to isaaclab imports (which require Isaac Sim runtime).

    Args:
        level_config: The level configuration.

    Returns:
        Dict with keys: command_type, use_relative_mode, has_gripper.
    """
    spec = get_action_mode(level_config)
    return {
        "command_type": spec.command_type,
        "use_relative_mode": spec.use_relative_mode,
        "has_gripper": spec.has_gripper,
        "dims_per_arm": spec.dims_per_arm,
    }
