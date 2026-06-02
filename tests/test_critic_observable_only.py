"""Tests for critic observable-only enforcement.

This is a MANDATORY test from the plan (§3, Stage 3):
Stage 3 input dict must pass schema whitelist assertion.
Any hidden sensor key → test MUST fail.
"""

import pytest

from aiongenos.replay.schema import (
    HIDDEN_SENSOR_BLACKLIST,
    OBSERVABLE_WHITELIST,
    validate_critic_input,
)


class TestCriticObservableOnly:
    """Enforce that Stage 3 critic ONLY receives observable data."""

    def test_valid_input(self):
        """Observable-only input should pass."""
        valid = {
            "instruction": "Push the red cube",
            "failure_label": "timeout",
            "trajectory_text": "t=0.0: LEFT_EE=(0,0,50)...",
            "rgb_start": "base64...",
            "rgb_end": "base64...",
        }
        assert validate_critic_input(valid) is True

    def test_contact_force_rejected(self):
        with pytest.raises(ValueError, match="Hidden sensor.*contact_force"):
            validate_critic_input({"contact_force": [1.0, 2.0, 3.0]})

    def test_joint_torque_rejected(self):
        with pytest.raises(ValueError, match="Hidden sensor.*joint_torque"):
            validate_critic_input({"joint_torque": [0.5]})

    def test_motor_current_rejected(self):
        with pytest.raises(ValueError, match="Hidden sensor.*motor_current"):
            validate_critic_input({"motor_current": 1.2})

    def test_applied_wrench_rejected(self):
        with pytest.raises(ValueError, match="Hidden sensor.*applied_wrench"):
            validate_critic_input({"applied_wrench": [0, 0, 0, 0, 0, 0]})

    def test_friction_rejected(self):
        with pytest.raises(ValueError, match="Hidden sensor.*friction_coefficient"):
            validate_critic_input({"friction_coefficient": 0.5})

    def test_object_mass_rejected(self):
        with pytest.raises(ValueError, match="Hidden sensor.*object_mass"):
            validate_critic_input({"object_mass": 0.1})

    def test_object_inertia_rejected(self):
        with pytest.raises(ValueError, match="Hidden sensor.*object_inertia"):
            validate_critic_input({"object_inertia": [1, 1, 1]})

    def test_object_material_rejected(self):
        with pytest.raises(ValueError, match="Hidden sensor.*object_material"):
            validate_critic_input({"object_material": "rubber"})

    def test_depth_image_rejected(self):
        with pytest.raises(ValueError, match="Hidden sensor.*depth_image"):
            validate_critic_input({"depth_image": "..."})

    def test_semantic_mask_rejected(self):
        with pytest.raises(ValueError, match="Hidden sensor.*semantic_mask"):
            validate_critic_input({"semantic_mask": "..."})

    def test_point_cloud_rejected(self):
        with pytest.raises(ValueError, match="Hidden sensor.*point_cloud"):
            validate_critic_input({"point_cloud": "..."})

    def test_mixed_valid_and_hidden(self):
        """Even one hidden sensor key in an otherwise valid dict should fail."""
        mixed = {
            "instruction": "Push cube",
            "trajectory_text": "...",
            "contact_force": [1.0],  # HIDDEN!
        }
        with pytest.raises(ValueError):
            validate_critic_input(mixed)

    def test_all_blacklisted_keys_covered(self):
        """Verify every blacklisted key triggers rejection."""
        for key in HIDDEN_SENSOR_BLACKLIST:
            with pytest.raises(ValueError, match=f"Hidden sensor.*{key}"):
                validate_critic_input({key: "dummy"})
