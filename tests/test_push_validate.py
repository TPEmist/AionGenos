"""Tests for scripts/analysis/wp3a_push_validate.py.

Spec §4 + REVISION 1 (R7, R9).
Negative tests for each HARD check: a mutated copy in tmp_path must be CAUGHT.
"""

from __future__ import annotations

import copy
import glob
import json
import pathlib
import re
import pytest

from scripts.analysis.wp3a_push_validate import validate_episodes, box_dist_quat, box_dist_axis_aligned


@pytest.fixture
def sample_episode() -> dict:
    files = sorted(glob.glob("/home/control/AionGenos/data/collect_dumps/71134939/*/meta.json"))
    assert files, "Sample run 71134939 not found"
    with open(files[0], "r", encoding="utf-8") as f:
        return json.load(f)


def test_validator_baseline_run_passes(sample_episode):
    """Old run 71134939 passes with zero hard failures."""
    success, stats = validate_episodes([sample_episode])
    assert success is True
    assert len(stats["hard_failures"]) == 0
    assert stats["box_fallback_count"] > 0  # old run reports fallback


def test_negative_invalid_flag_caught(sample_episode):
    """Flags outside whitelist must be CAUGHT as HARD failure."""
    mut = copy.deepcopy(sample_episode)
    mut["flags"].append("some_rogue_flag")
    success, stats = validate_episodes([mut])
    assert success is False
    assert any("some_rogue_flag" in f for f in stats["hard_failures"])


def test_negative_env_auto_reset_caught(sample_episode):
    """env_auto_reset in flags must be CAUGHT as HARD failure."""
    mut = copy.deepcopy(sample_episode)
    mut["flags"].append("env_auto_reset")
    success, stats = validate_episodes([mut])
    assert success is False
    assert any("env_auto_reset" in f for f in stats["hard_failures"])


def test_negative_premature_timeout_caught(sample_episode):
    """Timeout episode with fewer than PUSH_ROUND_CAP (12) rounds must be CAUGHT."""
    mut = copy.deepcopy(sample_episode)
    mut["outcome"] = "timeout"
    mut["rounds"] = mut["rounds"][:5]  # only 5 rounds
    success, stats = validate_episodes([mut])
    assert success is False
    assert any("premature_timeout" in f or "fewer than" in f or "5 rounds < 12" in f for f in stats["hard_failures"])


def test_negative_feedback_round1_has_fb_caught(sample_episode):
    """Round 1 must not carry feedback; if present, must be CAUGHT."""
    mut = copy.deepcopy(sample_episode)
    mut["rounds"][0]["round_feedback"] = "DIAGNOSTIC REPORT FOR PREVIOUS ROUND:\n  LEFT ARM:\n..."
    success, stats = validate_episodes([mut])
    assert success is False
    assert any("round 1" in f for f in stats["hard_failures"])


def test_negative_feedback_target_mismatch_caught(sample_episode):
    """Feedback target coordinate mismatch must be CAUGHT."""
    mut = copy.deepcopy(sample_episode)
    # Corrupt target in round 2's feedback
    fb = mut["rounds"][1]["round_feedback"]
    corrupted_fb = re.sub(r"X=(-?\d+)", "X=999", fb, count=1)
    assert corrupted_fb != fb
    mut["rounds"][1]["round_feedback"] = corrupted_fb
    success, stats = validate_episodes([mut])
    assert success is False
    assert any("target==prev_target" in f for f in stats["hard_failures"])


def test_negative_feedback_verdict_mismatch_caught(sample_episode):
    """Feedback verdict mismatching actual distance delta must be CAUGHT."""
    mut = copy.deepcopy(sample_episode)
    fb = mut["rounds"][1]["round_feedback"]
    # Change "No significant progress" to "Successful progress" without distance change
    corrupted_fb = fb.replace("Result: No significant progress", "Result: Successful progress. Left arm moved 3.0 cm closer to target.")
    mut["rounds"][1]["round_feedback"] = corrupted_fb
    success, stats = validate_episodes([mut])
    assert success is False
    assert any("verdict_matches_delta" in f for f in stats["hard_failures"])


def test_negative_d2_metric_mismatch_caught(sample_episode):
    """When verdict_contact_switch is on, wrong verdict_metric must be CAUGHT."""
    mut = copy.deepcopy(sample_episode)
    mut["verdict_contact_switch"] = True
    # In round 2 (before contact), expected metric is tip_cube, but set to cube_goal
    mut["rounds"][1]["verdict_metric"] = "cube_goal"
    success, stats = validate_episodes([mut])
    assert success is False
    assert any("verdict_metric_match" in f for f in stats["hard_failures"])


def test_negative_d1_missing_line_caught(sample_episode):
    """frame_convention=True but frame_line missing must be CAUGHT."""
    mut = copy.deepcopy(sample_episode)
    mut["frame_convention"] = True
    mut["frame_line"] = None
    success, stats = validate_episodes([mut])
    assert success is False
    assert any("frame_line is missing" in f for f in stats["hard_failures"])


def test_negative_d1_unit_mismatch_caught(sample_episode):
    """frame_convention=True with corrupted unit values must be CAUGHT."""
    mut = copy.deepcopy(sample_episode)
    mut["frame_convention"] = True
    mut["workspace_bounds"] = {"x": [-0.3, 0.6], "y": [-0.4, 0.4], "z": [0.0, 0.7]}
    # Corrupt unit values
    mut["frame_line"] = "FRAME (base frame, same grid as the numbers above): +X = forward, away from the robot base; +Y = the robot's left; +Z = up. One grid unit = 0.99 cm in X, 0.99 cm in Y, 0.99 cm in Z."
    success, stats = validate_episodes([mut])
    assert success is False
    assert any("unit_mismatch" in f or "mismatch" in f for f in stats["hard_failures"])


def test_d1_valid_line_passes(sample_episode):
    """frame_convention=True with correctly computed units passes."""
    mut = copy.deepcopy(sample_episode)
    mut["frame_convention"] = True
    mut["workspace_bounds"] = {"x": [-0.3, 0.6], "y": [-0.4, 0.4], "z": [0.0, 0.7]}
    mut["frame_line"] = "FRAME (base frame, same grid as the numbers above): +X = forward, away from the robot base; +Y = the robot's left; +Z = up. One grid unit = 0.45 cm in X, 0.40 cm in Y, 0.35 cm in Z."
    success, stats = validate_episodes([mut])
    assert success is True


def test_box_dist_quat_equivalence_on_identity():
    """Oriented box distance equals axis-aligned distance when quaternion is identity."""
    p = [0.35, 0.15, 0.50]
    c = [0.40, 0.10, 0.45]
    q_ident = [1.0, 0.0, 0.0, 0.0]
    d_quat = box_dist_quat(p, c, q_ident, half_h=0.024)
    d_aa = box_dist_axis_aligned(p, c, half_h=0.024)
    assert abs(d_quat - d_aa) < 1e-6
