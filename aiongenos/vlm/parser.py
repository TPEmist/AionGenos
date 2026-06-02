"""VLM response parser — regex extraction + Pydantic validation.

Parses structured VLM output from Stage 1 and Stage 3 into validated dataclasses.
Supports all control mode variants (position-only, RPY 2-DoF, RPY + gripper).
"""

from __future__ import annotations

import re
from typing import Optional

from pydantic import BaseModel, field_validator


class PositionTarget(BaseModel):
    """3D integer position target."""
    x: int
    y: int
    z: int

    @field_validator("x", "y", "z")
    @classmethod
    def in_range(cls, v: int) -> int:
        if not -100 <= v <= 100:
            raise ValueError(f"Coordinate {v} out of [-100, 100]")
        return v


class RPYTarget(BaseModel):
    """RPY integer target (2-DoF or 3-DoF)."""
    r: Optional[int] = None  # Roll (L3+ only)
    p: int = 0
    y: int = 0

    @field_validator("r", "p", "y")
    @classmethod
    def in_range(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and not -100 <= v <= 100:
            raise ValueError(f"Angle {v} out of [-100, 100]")
        return v


class VLMAction(BaseModel):
    """Parsed VLM action output for one arm."""
    position: PositionTarget
    rpy: Optional[RPYTarget] = None
    gripper: Optional[str] = None  # "open" or "closed"

    @field_validator("gripper")
    @classmethod
    def valid_gripper(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("open", "closed"):
            raise ValueError(f"Gripper must be 'open' or 'closed', got '{v}'")
        return v


class Stage1Response(BaseModel):
    """Full parsed Stage 1 response."""
    thought: str
    left: VLMAction
    right: VLMAction
    stop: bool


class Stage3Response(BaseModel):
    """Full parsed Stage 3 (critic) response."""
    diagnosis: str
    left: VLMAction
    right: VLMAction
    stop: bool


# ──────────────────── Regex patterns ──────────────────────────────

_INT = r"(-?\d+)"
_POS = rf"X={_INT}\s+Y={_INT}\s+Z={_INT}"
_RPY3 = rf"R={_INT}\s+P={_INT}\s+Y={_INT}"
_RPY2 = rf"P={_INT}\s+Y={_INT}"
_GRIP = r"(open|closed)"
_BOOL = r"(true|false)"


def _extract(pattern: str, text: str, label: str) -> re.Match:
    m = re.search(pattern, text, re.IGNORECASE)
    if m is None:
        raise ValueError(f"Failed to parse {label} from VLM output")
    return m


def parse_stage1(text: str, has_rpy: bool = False, has_gripper: bool = False, rpy_2dof: bool = False) -> Stage1Response:
    """Parse a Stage 1 VLM response.

    Args:
        text: Raw VLM output string.
        has_rpy: Whether RPY fields are expected.
        has_gripper: Whether gripper fields are expected.
        rpy_2dof: If True, RPY is 2-DoF (pitch, yaw only).

    Returns:
        Validated Stage1Response.
    """
    # Thought
    thought_m = re.search(r"THOUGHT:\s*(.+?)(?=\n(?:LEFT_TARGET|$))", text, re.DOTALL | re.IGNORECASE)
    thought = thought_m.group(1).strip() if thought_m else ""

    # Left position
    left_pos_m = _extract(rf"LEFT_TARGET_POS:\s*{_POS}", text, "LEFT_TARGET_POS")
    left_pos = PositionTarget(x=int(left_pos_m.group(1)), y=int(left_pos_m.group(2)), z=int(left_pos_m.group(3)))

    # Right position
    right_pos_m = _extract(rf"RIGHT_TARGET_POS:\s*{_POS}", text, "RIGHT_TARGET_POS")
    right_pos = PositionTarget(x=int(right_pos_m.group(1)), y=int(right_pos_m.group(2)), z=int(right_pos_m.group(3)))

    # RPY
    left_rpy = right_rpy = None
    if has_rpy:
        if rpy_2dof:
            lr = _extract(rf"LEFT_TARGET_RPY:\s*{_RPY2}", text, "LEFT_TARGET_RPY")
            left_rpy = RPYTarget(p=int(lr.group(1)), y=int(lr.group(2)))
            rr = _extract(rf"RIGHT_TARGET_RPY:\s*{_RPY2}", text, "RIGHT_TARGET_RPY")
            right_rpy = RPYTarget(p=int(rr.group(1)), y=int(rr.group(2)))
        else:
            lr = _extract(rf"LEFT_TARGET_RPY:\s*{_RPY3}", text, "LEFT_TARGET_RPY")
            left_rpy = RPYTarget(r=int(lr.group(1)), p=int(lr.group(2)), y=int(lr.group(3)))
            rr = _extract(rf"RIGHT_TARGET_RPY:\s*{_RPY3}", text, "RIGHT_TARGET_RPY")
            right_rpy = RPYTarget(r=int(rr.group(1)), p=int(rr.group(2)), y=int(rr.group(3)))

    # Gripper
    left_grip = right_grip = None
    if has_gripper:
        lg = _extract(rf"LEFT_GRIPPER_NEXT:\s*{_GRIP}", text, "LEFT_GRIPPER_NEXT")
        left_grip = lg.group(1).lower()
        rg = _extract(rf"RIGHT_GRIPPER_NEXT:\s*{_GRIP}", text, "RIGHT_GRIPPER_NEXT")
        right_grip = rg.group(1).lower()

    # Stop
    stop_m = _extract(rf"STOP:\s*{_BOOL}", text, "STOP")
    stop = stop_m.group(1).lower() == "true"

    return Stage1Response(
        thought=thought,
        left=VLMAction(position=left_pos, rpy=left_rpy, gripper=left_grip),
        right=VLMAction(position=right_pos, rpy=right_rpy, gripper=right_grip),
        stop=stop,
    )


def parse_stage3(text: str, has_rpy: bool = False, has_gripper: bool = False, rpy_2dof: bool = False) -> Stage3Response:
    """Parse a Stage 3 (critic) VLM response.

    Similar to parse_stage1 but with REVISED_ prefix and DIAGNOSIS field.
    """
    # Diagnosis
    diag_m = re.search(r"DIAGNOSIS:\s*(.+?)(?=\n(?:REVISED_|$))", text, re.DOTALL | re.IGNORECASE)
    diagnosis = diag_m.group(1).strip() if diag_m else ""

    # Left position
    lp = _extract(rf"REVISED_LEFT_TARGET_POS:\s*{_POS}", text, "REVISED_LEFT_TARGET_POS")
    left_pos = PositionTarget(x=int(lp.group(1)), y=int(lp.group(2)), z=int(lp.group(3)))

    # Right position
    rp = _extract(rf"REVISED_RIGHT_TARGET_POS:\s*{_POS}", text, "REVISED_RIGHT_TARGET_POS")
    right_pos = PositionTarget(x=int(rp.group(1)), y=int(rp.group(2)), z=int(rp.group(3)))

    # RPY
    left_rpy = right_rpy = None
    if has_rpy:
        if rpy_2dof:
            lr = _extract(rf"REVISED_LEFT_TARGET_RPY:\s*{_RPY2}", text, "REVISED_LEFT_TARGET_RPY")
            left_rpy = RPYTarget(p=int(lr.group(1)), y=int(lr.group(2)))
            rr = _extract(rf"REVISED_RIGHT_TARGET_RPY:\s*{_RPY2}", text, "REVISED_RIGHT_TARGET_RPY")
            right_rpy = RPYTarget(p=int(rr.group(1)), y=int(rr.group(2)))
        else:
            lr = _extract(rf"REVISED_LEFT_TARGET_RPY:\s*{_RPY3}", text, "REVISED_LEFT_TARGET_RPY")
            left_rpy = RPYTarget(r=int(lr.group(1)), p=int(lr.group(2)), y=int(lr.group(3)))
            rr = _extract(rf"REVISED_RIGHT_TARGET_RPY:\s*{_RPY3}", text, "REVISED_RIGHT_TARGET_RPY")
            right_rpy = RPYTarget(r=int(rr.group(1)), p=int(rr.group(2)), y=int(rr.group(3)))

    # Gripper
    left_grip = right_grip = None
    if has_gripper:
        lg = _extract(rf"REVISED_LEFT_GRIPPER_NEXT:\s*{_GRIP}", text, "REVISED_LEFT_GRIPPER_NEXT")
        left_grip = lg.group(1).lower()
        rg = _extract(rf"REVISED_RIGHT_GRIPPER_NEXT:\s*{_GRIP}", text, "REVISED_RIGHT_GRIPPER_NEXT")
        right_grip = rg.group(1).lower()

    # Stop
    stop_m = _extract(rf"STOP:\s*{_BOOL}", text, "STOP")
    stop = stop_m.group(1).lower() == "true"

    return Stage3Response(
        diagnosis=diagnosis,
        left=VLMAction(position=left_pos, rpy=left_rpy, gripper=left_grip),
        right=VLMAction(position=right_pos, rpy=right_rpy, gripper=right_grip),
        stop=stop,
    )
