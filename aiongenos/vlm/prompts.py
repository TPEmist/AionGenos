"""All VLM-facing prompt artifacts in one place.

Inventory of every string this codebase sends to a VLM (or constructs locally
for inclusion in a VLM call). Anything outside this file that goes to a VLM
should be considered an architectural mistake and migrated here.

| ID  | Symbol                       | Audience      | Per-level? | Purpose                             |
|-----|------------------------------|---------------|------------|-------------------------------------|
| P1  | ``STAGE1_SYSTEM``            | Stage 1 VLM   | No         | Role + output rules                 |
| P2  | ``_S1_POS``                  | Stage 1 VLM   | No (mode)  | User template for L0/L1             |
| P3  | ``_S1_RPY2``                 | Stage 1 VLM   | No (mode)  | User template for L2                |
| P4  | ``_S1_FULL``                 | Stage 1 VLM   | No (mode)  | User template for L3/L4             |
| P5  | ``STAGE3_SYSTEM``            | Stage 3 VLM   | No         | Critic role + observable-only rule  |
| P6  | ``_S3_POS/_S3_RPY2/_S3_FULL``| Stage 3 VLM   | No (mode)  | Critic user template                |
| P7  | ``LEVEL_TASK_INSTRUCTIONS``  | Stage 1 VLM   | YES        | Per-level task description (in      |
|     |   (``vlm/task_instructions``)|               |            | a separate module so this file      |
|     |                              |               |            | stays task-agnostic)                |
| P8  | ``CRITIC_FEEDBACK_*``        | Stage 1 VLM   | No         | Programmatic per-round critic text  |
|     |                              |               |            | injected via ``run_stage1``         |
| P9  | ``format_trajectory_text``   | Stage 3 VLM   | No         | Observable-only trajectory dump     |
|     |   (``pipeline/stage3_critic``|               |            |                                     |

**Task-agnostic invariant:** Everything in this file must work for any of the
five curriculum levels without modification — adding a new level should never
require editing this file. Per-level wording lives in ``task_instructions.py``
exclusively.

**Observable-only invariant (Stage 3, plan §10):** Stage 3 prompts/feedback
must not reference contact force, joint torque, mass, friction, etc. Adding
new fields requires updating ``replay.schema.OBSERVABLE_WHITELIST``.
"""

from __future__ import annotations

from typing import Final

from aiongenos.config import ControlMode, LevelConfig

# ─────────────────────────────────────────────────────────────────────────
# P1: Stage 1 system prompt
# ─────────────────────────────────────────────────────────────────────────
STAGE1_SYSTEM: Final[str] = (
    "You are a bimanual robot controller. You receive a camera image of the scene "
    "and must plan the next sub-goal for both arms.\n"
    "Rules:\n- All coordinates are integers in [-100, 100].\n"
    "- Never output floating point numbers for coordinates.\n"
    "- Reason step-by-step about the physics before giving targets.\n"
    "- Output your response in the EXACT format specified below."
)

# ─────────────────────────────────────────────────────────────────────────
# P2-P4: Stage 1 user templates per ControlMode
# ─────────────────────────────────────────────────────────────────────────
_S1_POS: Final[str] = (
    "TASK: {instruction}\nCONTROL_MODE: end_effector_position_only\n\n"
    "CURRENT STATE:\n"
    "  LEFT_EE_POS  = (X={left_x}, Y={left_y}, Z={left_z})\n"
    "  RIGHT_EE_POS = (X={right_x}, Y={right_y}, Z={right_z})\n"
    "  LEFT_EE_TO_RED_CUBE  = {dist_red_cm} cm\n"
    "  RIGHT_EE_TO_BLUE_CUBE = {dist_blue_cm} cm\n\n"
    "THOUGHT: <one paragraph physics reasoning>\n"
    "LEFT_TARGET_POS:  X=<int> Y=<int> Z=<int>\n"
    "RIGHT_TARGET_POS: X=<int> Y=<int> Z=<int>\n"
    "STOP: <true|false>"
)

_S1_RPY2: Final[str] = (
    "TASK: {instruction}\nCONTROL_MODE: end_effector_pose_with_2dof_rpy\n\n"
    "CURRENT STATE:\n"
    "  LEFT_EE_POS  = (X={left_x}, Y={left_y}, Z={left_z})\n"
    "  LEFT_EE_RPY  = (P={left_p}, Y={left_yaw})\n"
    "  RIGHT_EE_POS = (X={right_x}, Y={right_y}, Z={right_z})\n"
    "  RIGHT_EE_RPY = (P={right_p}, Y={right_yaw})\n"
    "  LEFT_EE_TO_RED_CUBE  = {dist_red_cm} cm\n"
    "  RIGHT_EE_TO_BLUE_CUBE = {dist_blue_cm} cm\n\n"
    "THOUGHT: <one paragraph physics reasoning>\n"
    "LEFT_TARGET_POS:  X=<int> Y=<int> Z=<int>\n"
    "LEFT_TARGET_RPY:  P=<int> Y=<int>\n"
    "RIGHT_TARGET_POS: X=<int> Y=<int> Z=<int>\n"
    "RIGHT_TARGET_RPY: P=<int> Y=<int>\n"
    "STOP: <true|false>"
)

_S1_FULL: Final[str] = (
    "TASK: {instruction}\nCONTROL_MODE: end_effector_pose_with_rpy\n\n"
    "CURRENT STATE:\n"
    "  LEFT_EE_POS  = (X={left_x}, Y={left_y}, Z={left_z})\n"
    "  LEFT_EE_RPY  = (R={left_r}, P={left_p}, Y={left_yaw})\n"
    "  LEFT_GRIPPER = {left_gripper}\n"
    "  RIGHT_EE_POS = (X={right_x}, Y={right_y}, Z={right_z})\n"
    "  RIGHT_EE_RPY = (R={right_r}, P={right_p}, Y={right_yaw})\n"
    "  RIGHT_GRIPPER = {right_gripper}\n"
    "  LEFT_EE_TO_RED_CUBE  = {dist_red_cm} cm\n"
    "  RIGHT_EE_TO_BLUE_CUBE = {dist_blue_cm} cm\n\n"
    "THOUGHT: <one paragraph physics reasoning>\n"
    "LEFT_TARGET_POS:  X=<int> Y=<int> Z=<int>\n"
    "LEFT_TARGET_RPY:  R=<int> P=<int> Y=<int>\n"
    "LEFT_GRIPPER_NEXT: <open|closed>\n"
    "RIGHT_TARGET_POS: X=<int> Y=<int> Z=<int>\n"
    "RIGHT_TARGET_RPY: R=<int> P=<int> Y=<int>\n"
    "RIGHT_GRIPPER_NEXT: <open|closed>\n"
    "STOP: <true|false>"
)

STAGE1_TEMPLATES: Final[dict[ControlMode, str]] = {
    ControlMode.POSITION_ONLY: _S1_POS,
    ControlMode.POSITION_RPY_2DOF: _S1_RPY2,
    ControlMode.POSITION_RPY_GRIPPER: _S1_FULL,
}

# ─────────────────────────────────────────────────────────────────────────
# P5: Stage 3 system prompt
# ─────────────────────────────────────────────────────────────────────────
STAGE3_SYSTEM: Final[str] = (
    "You are a physics-grounded critic. The robot just attempted a task and FAILED. "
    "Diagnose using ONLY externally observable info (camera, EE positions, gripper states). "
    "Do NOT reference hidden sensors (contact force, joint torque, friction, mass, inertia)."
)

# ─────────────────────────────────────────────────────────────────────────
# P6: Stage 3 user templates per ControlMode
# ─────────────────────────────────────────────────────────────────────────
_S3_POS: Final[str] = (
    'The robot attempted: "{instruction}" and FAILED: {failure_label}.\n\n'
    "TRAJECTORY:\n{trajectory_text}\n\n"
    "DIAGNOSIS: <visible evidence analysis>\n"
    "REVISED_LEFT_TARGET_POS:  X=<int> Y=<int> Z=<int>\n"
    "REVISED_RIGHT_TARGET_POS: X=<int> Y=<int> Z=<int>\n"
    "STOP: <true|false>"
)

_S3_RPY2: Final[str] = (
    'The robot attempted: "{instruction}" and FAILED: {failure_label}.\n\n'
    "TRAJECTORY:\n{trajectory_text}\n\n"
    "DIAGNOSIS: <visible evidence analysis>\n"
    "REVISED_LEFT_TARGET_POS:  X=<int> Y=<int> Z=<int>\n"
    "REVISED_LEFT_TARGET_RPY:  P=<int> Y=<int>\n"
    "REVISED_RIGHT_TARGET_POS: X=<int> Y=<int> Z=<int>\n"
    "REVISED_RIGHT_TARGET_RPY: P=<int> Y=<int>\n"
    "STOP: <true|false>"
)

_S3_FULL: Final[str] = (
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

STAGE3_TEMPLATES: Final[dict[ControlMode, str]] = {
    ControlMode.POSITION_ONLY: _S3_POS,
    ControlMode.POSITION_RPY_2DOF: _S3_RPY2,
    ControlMode.POSITION_RPY_GRIPPER: _S3_FULL,
}

# ─────────────────────────────────────────────────────────────────────────
# P8: Programmatic critic-feedback templates (injected into Stage 1 user)
# ─────────────────────────────────────────────────────────────────────────
CRITIC_FEEDBACK_HEADER: Final[str] = "DIAGNOSTIC REPORT FOR PREVIOUS ROUND:"

CRITIC_FEEDBACK_ARM_BLOCK: Final[str] = (
    "  {arm} ARM:\n"
    "    Target coordinate was predicted at: X={px} Y={py} Z={pz}\n"
    "    Actual movement: from X={sx} Y={sy} Z={sz} to X={ex} Y={ey} Z={ez}\n"
    "    Euclidean distance to target: started at {d_start:.1f} cm, ended at {d_end:.1f} cm"
)
CRITIC_FEEDBACK_PROGRESS: Final[str] = (
    "    Result: Successful progress. {Arm} arm moved {abs_delta:.1f} cm closer to target."
)
CRITIC_FEEDBACK_REGRESS: Final[str] = (
    "    Result: Regression. {Arm} arm moved {delta:.1f} cm further from target. "
    "Adjust prediction direction."
)
CRITIC_FEEDBACK_FLAT: Final[str] = (
    "    Result: No significant progress (still {d_end:.1f} cm from target). "
    "Try a different direction or larger step size. "
    "STOP only when the task's success criterion is met — do not stop because "
    "previous rounds showed no progress."
)

# Threshold (cm) below which we declare the round flat (no progress / no regress).
CRITIC_PROGRESS_DEAD_BAND_CM: Final[float] = 1.0

# Critic feedback header token (Stage 1 user prompt suffix when feedback exists).
CRITIC_FEEDBACK_INJECTION_HEADER: Final[str] = "### CRITIC FEEDBACK FROM PREVIOUS ROUND:"


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
