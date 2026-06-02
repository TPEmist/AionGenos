"""Tests for VLM parser — all control mode variants for Stage 1 and Stage 3."""

import pytest

from aiongenos.vlm.parser import (
    parse_stage1,
    parse_stage3,
)


class TestStage1PositionOnly:
    """Stage 1 parser for L0/L1 (position-only)."""

    SAMPLE = (
        "THOUGHT: The red cube is at the left side. I need to move left arm towards it "
        "and right arm towards the green target.\n"
        "LEFT_TARGET_POS:  X=30 Y=-20 Z=50\n"
        "RIGHT_TARGET_POS: X=-10 Y=40 Z=60\n"
        "STOP: false"
    )

    def test_parse_basic(self):
        result = parse_stage1(self.SAMPLE)
        assert result.left.position.x == 30
        assert result.left.position.y == -20
        assert result.left.position.z == 50
        assert result.right.position.x == -10
        assert result.right.position.y == 40
        assert result.right.position.z == 60
        assert result.stop is False
        assert "red cube" in result.thought

    def test_stop_true(self):
        text = (
            "THOUGHT: Done.\n"
            "LEFT_TARGET_POS:  X=0 Y=0 Z=0\n"
            "RIGHT_TARGET_POS: X=0 Y=0 Z=0\n"
            "STOP: true"
        )
        result = parse_stage1(text)
        assert result.stop is True

    def test_negative_coords(self):
        text = (
            "THOUGHT: Moving.\n"
            "LEFT_TARGET_POS:  X=-100 Y=-50 Z=-30\n"
            "RIGHT_TARGET_POS: X=100 Y=50 Z=30\n"
            "STOP: false"
        )
        result = parse_stage1(text)
        assert result.left.position.x == -100
        assert result.right.position.x == 100


class TestStage1RPY2DoF:
    """Stage 1 parser for L2 (position + 2-DoF RPY)."""

    SAMPLE = (
        "THOUGHT: Need to approach from top.\n"
        "LEFT_TARGET_POS:  X=20 Y=10 Z=40\n"
        "LEFT_TARGET_RPY:  P=-30 Y=15\n"
        "RIGHT_TARGET_POS: X=-20 Y=-10 Z=50\n"
        "RIGHT_TARGET_RPY: P=20 Y=-45\n"
        "STOP: false"
    )

    def test_parse_rpy_2dof(self):
        result = parse_stage1(self.SAMPLE, has_rpy=True, rpy_2dof=True)
        assert result.left.rpy.p == -30
        assert result.left.rpy.y == 15
        assert result.right.rpy.p == 20
        assert result.right.rpy.y == -45


class TestStage1Full:
    """Stage 1 parser for L3/L4 (position + RPY + gripper)."""

    SAMPLE = (
        "THOUGHT: Need to grasp.\n"
        "LEFT_TARGET_POS:  X=10 Y=20 Z=30\n"
        "LEFT_TARGET_RPY:  R=5 P=-10 Y=15\n"
        "LEFT_GRIPPER_NEXT: closed\n"
        "RIGHT_TARGET_POS: X=-10 Y=-20 Z=40\n"
        "RIGHT_TARGET_RPY: R=-5 P=10 Y=-15\n"
        "RIGHT_GRIPPER_NEXT: open\n"
        "STOP: false"
    )

    def test_parse_full(self):
        result = parse_stage1(self.SAMPLE, has_rpy=True, has_gripper=True)
        assert result.left.rpy.r == 5
        assert result.left.gripper == "closed"
        assert result.right.gripper == "open"


class TestStage1ParseFailures:
    """Parser should raise on invalid input."""

    def test_missing_position(self):
        text = "THOUGHT: ...\nSTOP: false"
        with pytest.raises(ValueError, match="LEFT_TARGET_POS"):
            parse_stage1(text)

    def test_out_of_range_coordinate(self):
        text = (
            "THOUGHT: ...\n"
            "LEFT_TARGET_POS:  X=200 Y=0 Z=0\n"
            "RIGHT_TARGET_POS: X=0 Y=0 Z=0\n"
            "STOP: false"
        )
        with pytest.raises(ValueError):
            parse_stage1(text)


class TestStage3:
    """Stage 3 (critic) parser tests."""

    SAMPLE = (
        "DIAGNOSIS: The left arm moved too far right, missing the target.\n"
        "REVISED_LEFT_TARGET_POS:  X=25 Y=-15 Z=45\n"
        "REVISED_RIGHT_TARGET_POS: X=-5 Y=35 Z=55\n"
        "STOP: false"
    )

    def test_parse_basic(self):
        result = parse_stage3(self.SAMPLE)
        assert result.left.position.x == 25
        assert result.right.position.y == 35
        assert "too far right" in result.diagnosis

    def test_parse_with_gripper(self):
        text = (
            "DIAGNOSIS: Grip too early.\n"
            "REVISED_LEFT_TARGET_POS:  X=10 Y=20 Z=30\n"
            "REVISED_LEFT_TARGET_RPY:  R=0 P=-5 Y=10\n"
            "REVISED_LEFT_GRIPPER_NEXT: open\n"
            "REVISED_RIGHT_TARGET_POS: X=-10 Y=-20 Z=40\n"
            "REVISED_RIGHT_TARGET_RPY: R=0 P=5 Y=-10\n"
            "REVISED_RIGHT_GRIPPER_NEXT: closed\n"
            "STOP: false"
        )
        result = parse_stage3(text, has_rpy=True, has_gripper=True)
        assert result.left.gripper == "open"
        assert result.right.gripper == "closed"
