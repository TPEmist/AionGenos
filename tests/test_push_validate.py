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
    assert stats["d1_units_OK"] == 1


def test_d1_missing_workspace_bounds_reports_na(sample_episode):
    """When workspace_bounds is missing from meta, d1 reports N/A instead of falling back to default."""
    mut = copy.deepcopy(sample_episode)
    mut["frame_convention"] = True
    mut.pop("workspace_bounds", None)
    mut["frame_line"] = "FRAME (base frame, same grid as the numbers above): +X = forward, away from the robot base; +Y = the robot's left; +Z = up. One grid unit = 0.45 cm in X, 0.40 cm in Y, 0.35 cm in Z."
    success, stats = validate_episodes([mut])
    assert success is True
    assert stats["d1_bounds_missing"] == 1


def test_standby_z_count_equals_509_on_71134939():
    """Verify that standby_z definition yields exactly 509 rounds on run 71134939."""
    files = sorted(glob.glob("/home/control/AionGenos/data/collect_dumps/71134939/*/meta.json"))
    assert len(files) == 50
    eps = [json.load(open(f, "r", encoding="utf-8")) for f in files]
    success, stats = validate_episodes(eps)
    assert success is True
    assert stats["z_standby_count"] == 509
    assert stats["z_contact_band_count"] == 13
    assert stats["z_other_count"] == 75
    assert stats["rounds"] == 597


def test_box_dist_quat_equivalence_on_identity():
    """Oriented box distance equals axis-aligned distance when quaternion is identity."""
    p = [0.35, 0.15, 0.50]
    c = [0.40, 0.10, 0.45]
    q_ident = [1.0, 0.0, 0.0, 0.0]
    d_quat = box_dist_quat(p, c, q_ident, half_h=0.024)
    d_aa = box_dist_axis_aligned(p, c, half_h=0.024)
    assert abs(d_quat - d_aa) < 1e-6


def test_pin4c_valid_sample_passes(sample_episode):
    """Pin-4c episode with valid commanded goal_sample passes HARD checks."""
    mut = copy.deepcopy(sample_episode)
    mut["geometry"] = "pin4c"
    mut["goal_sample"] = {"theta": 0.5, "dist": 0.085, "cube_xy": [0.40, 0.10]}
    success, stats = validate_episodes([mut])
    assert success is True
    assert stats["R"].get("pin4c_sample_OK") == 1


def test_negative_pin4c_missing_sample_caught(sample_episode):
    """Episode with geometry=pin4c but missing goal_sample must be CAUGHT as HARD failure."""
    mut = copy.deepcopy(sample_episode)
    mut["geometry"] = "pin4c"
    mut.pop("goal_sample", None)
    success, stats = validate_episodes([mut])
    assert success is False
    assert any("goal_sample is missing" in f for f in stats["hard_failures"])


def test_negative_pin4c_dist_out_of_bounds_caught(sample_episode):
    """Pin-4c commanded dist outside [0.07, 0.10] must be CAUGHT as HARD failure."""
    mut = copy.deepcopy(sample_episode)
    mut["geometry"] = "pin4c"
    mut["goal_sample"] = {"theta": 0.0, "dist": 0.060, "cube_xy": [0.40, 0.10]}
    success, stats = validate_episodes([mut])
    assert success is False
    assert any("dist 0.06" in f or "outside [0.07, 0.10]" in f for f in stats["hard_failures"])


def test_negative_pin4c_theta_out_of_bounds_caught(sample_episode):
    """Pin-4c commanded |theta| > theta_max must be CAUGHT as HARD failure."""
    mut = copy.deepcopy(sample_episode)
    mut["geometry"] = "pin4c"
    mut["goal_sample"] = {"theta": 1.50, "dist": 0.085, "cube_xy": [0.40, 0.10]}
    success, stats = validate_episodes([mut])
    assert success is False
    assert any("theta_max" in f for f in stats["hard_failures"])


def test_pin4b_ignores_pin4c_sample_checks(sample_episode):
    """R11: Pin-4b runs keep old checks and are not subject to pin4c sample checks."""
    mut = copy.deepcopy(sample_episode)
    mut["geometry"] = "pin4b"
    # Even with goal_sample missing or out of bounds, pin4b does not trigger pin4c HARD failures
    mut.pop("goal_sample", None)
    success, stats = validate_episodes([mut])
    assert success is True


def test_scripted_policy_flag_and_outcome_accepted(sample_episode):
    """scripted_policy flag and scripted_end outcome must be accepted."""
    mut = copy.deepcopy(sample_episode)
    mut["flags"] = ["scripted_policy"]
    mut["outcome"] = "scripted_end"
    mut["rounds"] = mut["rounds"][:3]  # e.g. 3 scripted rounds
    success, stats = validate_episodes([mut])
    assert success is True
    assert len(stats["hard_failures"]) == 0


def test_lesson_leak_rate_and_redactions_counted(sample_episode):
    """Lesson coordinate leak rate and redactions are tracked in stats."""
    mut = copy.deepcopy(sample_episode)
    mut["preamble_coords"] = "off"
    mut["preamble_coord_redactions"] = 4
    mut["memory_hits"] = [
        {"ep_id": "ep1", "lesson": "Push with X=50"},
        {"ep_id": "ep2", "lesson": "Good push to green zone"},
    ]
    success, stats = validate_episodes([mut])
    assert success is True
    assert stats["total_injected_lessons"] == 2
    assert stats["leaked_lesson_count"] == 1
    assert stats["preamble_coord_redactions_total"] == 4
    assert stats["preamble_coords_mode"] == "off"


def test_vlm_parse_fail_flag_and_outcome_accepted(sample_episode):
    """vlm_parse_fail outcome and flag with early exit (rounds < 12) must be accepted."""
    mut = copy.deepcopy(sample_episode)
    mut["outcome"] = "vlm_parse_fail"
    mut["flags"] = ["label:pilot", "vlm_parse_fail"]
    mut["rounds"] = mut["rounds"][:3]
    success, stats = validate_episodes([mut])
    assert success is True
    assert len(stats["hard_failures"]) == 0
    assert stats["outcomes"]["vlm_parse_fail"] == 1


def test_vlm_parse_fail_with_timeout_outcome_exempt_from_cap_check(sample_episode):
    """If outcome is timeout but vlm_parse_fail is present, premature timeout cap check is exempt."""
    mut = copy.deepcopy(sample_episode)
    mut["outcome"] = "timeout"
    mut["flags"] = ["label:pilot", "vlm_parse_fail"]
    mut["rounds"] = mut["rounds"][:4]
    success, stats = validate_episodes([mut])
    assert success is True
    assert len(stats["hard_failures"]) == 0
    assert not any("premature_timeout" in f or "fewer than" in f for f in stats["hard_failures"])


def test_real_run_3786f4e5_parse_fail_episode_passes():
    """Verify the real parse-fail episode 5d22865f-13b from run 3786f4e5 passes validation."""
    meta_path = pathlib.Path("/home/control/AionGenos/data/collect_dumps/3786f4e5/5d22865f-13b/meta.json")
    if not meta_path.exists():
        pytest.skip("Run 3786f4e5 not found on disk")
    with open(meta_path, "r", encoding="utf-8") as f:
        ep = json.load(f)
    assert ep["outcome"] == "vlm_parse_fail"
    assert "vlm_parse_fail" in ep["flags"]
    assert len(ep["rounds"]) < 12
    success, stats = validate_episodes([ep])
    assert success is True
    assert len(stats["hard_failures"]) == 0


def test_negative_vlm_parse_fail_with_unwhitelisted_flag_caught(sample_episode):
    """vlm_parse_fail episode that also contains a rogue flag must still be CAUGHT."""
    mut = copy.deepcopy(sample_episode)
    mut["outcome"] = "vlm_parse_fail"
    mut["flags"] = ["vlm_parse_fail", "unwhitelisted_custom_flag"]
    mut["rounds"] = mut["rounds"][:3]
    success, stats = validate_episodes([mut])
    assert success is False
    assert any("unwhitelisted_custom_flag" in f for f in stats["hard_failures"])


def test_negative_vlm_parse_fail_with_env_auto_reset_caught(sample_episode):
    """vlm_parse_fail episode that also contains env_auto_reset must still be CAUGHT as HARD."""
    mut = copy.deepcopy(sample_episode)
    mut["outcome"] = "vlm_parse_fail"
    mut["flags"] = ["vlm_parse_fail", "env_auto_reset"]
    mut["rounds"] = mut["rounds"][:3]
    success, stats = validate_episodes([mut])
    assert success is False
    assert any("env_auto_reset" in f for f in stats["hard_failures"])


def test_negative_timeout_without_parse_fail_flag_still_caught(sample_episode):
    """Premature timeout without vlm_parse_fail flag must still be CAUGHT."""
    mut = copy.deepcopy(sample_episode)
    mut["outcome"] = "timeout"
    mut["flags"] = ["label:pilot", "scripted_policy"]
    mut["rounds"] = mut["rounds"][:3]
    success, stats = validate_episodes([mut])
    assert success is False
    assert any("premature_timeout" in f or "fewer than" in f or "3 rounds < 12" in f for f in stats["hard_failures"])


def test_whitelisted_push_collect_and_guard_flags_accepted(sample_episode):
    """All legitimate flags from push_collect and scalar guard pass whitelist check."""
    from scripts.analysis.wp3a_push_validate import FLAG_WHITELIST
    safe_flags = FLAG_WHITELIST - {"env_auto_reset"}  # env_auto_reset is deliberately caught as HARD
    for flag in safe_flags:
        mut = copy.deepcopy(sample_episode)
        mut["flags"] = ["label:pilot", flag]
        success, stats = validate_episodes([mut])
        assert not any(f"has invalid flag {flag!r}" in f for f in stats["hard_failures"]), f"Flag {flag} failed whitelist"

