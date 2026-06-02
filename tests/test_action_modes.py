"""Tests for action_modes — per-level control mode switching."""

import pytest

from aiongenos.config import ControlMode, LEVEL_CONFIGS
from aiongenos.control.action_modes import (
    ACTION_MODE_MAP,
    build_ik_action_cfg_dict,
    get_action_mode,
)


class TestActionModes:
    def test_l0_position_only(self):
        cfg = LEVEL_CONFIGS[0]
        spec = get_action_mode(cfg)
        assert spec.command_type == "position"
        assert spec.dims_per_arm == 3
        assert spec.has_gripper is False

    def test_l1_position_only(self):
        cfg = LEVEL_CONFIGS[1]
        spec = get_action_mode(cfg)
        assert spec.command_type == "position"
        assert spec.dims_per_arm == 3
        assert spec.has_gripper is False

    def test_l2_rpy_2dof(self):
        cfg = LEVEL_CONFIGS[2]
        spec = get_action_mode(cfg)
        assert spec.command_type == "pose"
        assert spec.dims_per_arm == 5
        assert spec.has_gripper is False

    def test_l3_full(self):
        cfg = LEVEL_CONFIGS[3]
        spec = get_action_mode(cfg)
        assert spec.command_type == "pose"
        assert spec.dims_per_arm == 6
        assert spec.has_gripper is True

    def test_l4_full(self):
        cfg = LEVEL_CONFIGS[4]
        spec = get_action_mode(cfg)
        assert spec.command_type == "pose"
        assert spec.has_gripper is True

    def test_build_ik_cfg_dict(self):
        cfg = LEVEL_CONFIGS[0]
        d = build_ik_action_cfg_dict(cfg)
        assert d["command_type"] == "position"
        assert d["use_relative_mode"] is False
        assert d["has_gripper"] is False
        assert d["dims_per_arm"] == 3

    def test_all_levels_covered(self):
        """Every defined level should have a valid action mode."""
        for level, config in LEVEL_CONFIGS.items():
            spec = get_action_mode(config)
            assert spec is not None, f"Level {level} has no action mode"

    def test_all_control_modes_mapped(self):
        """Every ControlMode enum value should be in the map."""
        for mode in ControlMode:
            assert mode in ACTION_MODE_MAP, f"Missing mapping for {mode}"
