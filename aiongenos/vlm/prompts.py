"""Task-agnostic prompt templates for Stage 1 (Reasoning) and Stage 3 (Critic).

All prompts are parameterized via format_map with task config fields.
The same template works across all 5 curriculum levels.
"""

from __future__ import annotations

from aiongenos.config import ControlMode, LevelConfig

STAGE1_SYSTEM = (
    "You are a bimanual robot controller. You receive a camera image of the scene "
    "and must plan the next sub-goal for both arms.\n"
    "Rules:\n- All coordinates are integers in [-100, 100].\n"
    "- Never output floating point numbers for coordinates.\n"
    "- Reason step-by-step about the physics before giving targets.\n"
    "- Output your response in the EXACT format specified below."
)

_S1_POS = (
    "TASK: {instruction}\nCONTROL_MODE: end_effector_position_only\n\n"
    "CURRENT STATE:\n"
    "  LEFT_EE_POS  = (X={left_x}, Y={left_y}, Z={left_z})\n"
    "  RIGHT_EE_POS = (X={right_x}, Y={right_y}, Z={right_z})\n\n"
    "THOUGHT: <one paragraph physics reasoning>\n"
    "LEFT_TARGET_POS:  X=<int> Y=<int> Z=<int>\n"
    "RIGHT_TARGET_POS: X=<int> Y=<int> Z=<int>\n"
    "STOP: <true|false>"
)

_S1_RPY2 = (
    "TASK: {instruction}\nCONTROL_MODE: end_effector_pose_with_2dof_rpy\n\n"
    "CURRENT STATE:\n"
    "  LEFT_EE_POS  = (X={left_x}, Y={left_y}, Z={left_z})\n"
    "  LEFT_EE_RPY  = (P={left_p}, Y={left_yaw})\n"
    "  RIGHT_EE_POS = (X={right_x}, Y={right_y}, Z={right_z})\n"
    "  RIGHT_EE_RPY = (P={right_p}, Y={right_yaw})\n\n"
    "THOUGHT: <one paragraph physics reasoning>\n"
    "LEFT_TARGET_POS:  X=<int> Y=<int> Z=<int>\n"
    "LEFT_TARGET_RPY:  P=<int> Y=<int>\n"
    "RIGHT_TARGET_POS: X=<int> Y=<int> Z=<int>\n"
    "RIGHT_TARGET_RPY: P=<int> Y=<int>\n"
    "STOP: <true|false>"
)

_S1_FULL = (
    "TASK: {instruction}\nCONTROL_MODE: end_effector_pose_with_rpy\n\n"
    "CURRENT STATE:\n"
    "  LEFT_EE_POS  = (X={left_x}, Y={left_y}, Z={left_z})\n"
    "  LEFT_EE_RPY  = (R={left_r}, P={left_p}, Y={left_yaw})\n"
    "  LEFT_GRIPPER = {left_gripper}\n"
    "  RIGHT_EE_POS = (X={right_x}, Y={right_y}, Z={right_z})\n"
    "  RIGHT_EE_RPY = (R={right_r}, P={right_p}, Y={right_yaw})\n"
    "  RIGHT_GRIPPER = {right_gripper}\n\n"
    "THOUGHT: <one paragraph physics reasoning>\n"
    "LEFT_TARGET_POS:  X=<int> Y=<int> Z=<int>\n"
    "LEFT_TARGET_RPY:  R=<int> P=<int> Y=<int>\n"
    "LEFT_GRIPPER_NEXT: <open|closed>\n"
    "RIGHT_TARGET_POS: X=<int> Y=<int> Z=<int>\n"
    "RIGHT_TARGET_RPY: R=<int> P=<int> Y=<int>\n"
    "RIGHT_GRIPPER_NEXT: <open|closed>\n"
    "STOP: <true|false>"
)

STAGE1_TEMPLATES = {
    ControlMode.POSITION_ONLY: _S1_POS,
    ControlMode.POSITION_RPY_2DOF: _S1_RPY2,
    ControlMode.POSITION_RPY_GRIPPER: _S1_FULL,
}

# ── Stage 3: Critic ──

STAGE3_SYSTEM = (
    "You are a physics-grounded critic. The robot just attempted a task and FAILED. "
    "Diagnose using ONLY externally observable info (camera, EE positions, gripper states). "
    "Do NOT reference hidden sensors (contact force, joint torque, friction, mass, inertia)."
)

_S3_POS = (
    'The robot attempted: "{instruction}" and FAILED: {failure_label}.\n\n'
    "TRAJECTORY:\n{trajectory_text}\n\n"
    "DIAGNOSIS: <visible evidence analysis>\n"
    "REVISED_LEFT_TARGET_POS:  X=<int> Y=<int> Z=<int>\n"
    "REVISED_RIGHT_TARGET_POS: X=<int> Y=<int> Z=<int>\n"
    "STOP: <true|false>"
)

_S3_RPY2 = (
    'The robot attempted: "{instruction}" and FAILED: {failure_label}.\n\n'
    "TRAJECTORY:\n{trajectory_text}\n\n"
    "DIAGNOSIS: <visible evidence analysis>\n"
    "REVISED_LEFT_TARGET_POS:  X=<int> Y=<int> Z=<int>\n"
    "REVISED_LEFT_TARGET_RPY:  P=<int> Y=<int>\n"
    "REVISED_RIGHT_TARGET_POS: X=<int> Y=<int> Z=<int>\n"
    "REVISED_RIGHT_TARGET_RPY: P=<int> Y=<int>\n"
    "STOP: <true|false>"
)

_S3_FULL = (
    'The robot attempted: "{instruction}" and FAILED: {failure_label}.\n\n'
    "TRAJECTORY:\n{trajectory_text}\n\n"
    "DIAGNOSIS: <visible evidence analysis>\n"
    "REVISED_LEFT_TARGET_POS:  X=<int> Y=<int> Z=<int>\n"
    "REVISED_LEFT_TARGET_RPY:  R=<int> P=<int> Y=<int>\n"
    "REVISED_LEFT_GRIPPER_NEXT: <open|closed>\n"
    "REVISED_RIGHT_TARGET_POS: X=<int> Y=<int> Z=<int>\n"
    "REVISED_RIGHT_TARGET_RPY: R=<int> P=<int> Y=<int>\n"
    "REVISED_RIGHT_GRIPPER_NEXT: <open|closed>\n"
    "STOP: <true|false>"
)

STAGE3_TEMPLATES = {
    ControlMode.POSITION_ONLY: _S3_POS,
    ControlMode.POSITION_RPY_2DOF: _S3_RPY2,
    ControlMode.POSITION_RPY_GRIPPER: _S3_FULL,
}


def get_stage1_prompt(level_config: LevelConfig, state: dict) -> str:
    """Build Stage 1 user prompt."""
    return STAGE1_TEMPLATES[level_config.control_mode].format_map(state)


def get_stage3_prompt(level_config: LevelConfig, state: dict) -> str:
    """Build Stage 3 critic prompt."""
    return STAGE3_TEMPLATES[level_config.control_mode].format_map(state)


def get_stage1_system_prompt() -> str:
    return STAGE1_SYSTEM


def get_stage3_system_prompt() -> str:
    return STAGE3_SYSTEM
