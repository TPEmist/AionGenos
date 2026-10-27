"""Unit tests for Pin-4c scan derivation (Spec §1, AC2, REVISION 1 R5, R6).
Pure CPU tests on synthetic scan JSONs — no Isaac/GPU.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from scripts.analysis.wp3a_p4c_derive import (
    compute_asymmetric_reach,
    compute_telemetry,
    derive_p4c_geometry,
    find_largest_box_for_range,
    format_candidate_table,
    is_point_solvable,
    is_record_solvable,
    merge_scan_inputs,
)


def make_synthetic_scan(
    solvable_fn,
    x_grid=None,
    y_grid=None,
    theta_grid=None,
    dist_grid=None,
):
    if x_grid is None:
        x_grid = [round(0.34 + i * 0.03, 3) for i in range(7)]   # 0.34 to 0.52
    if y_grid is None:
        y_grid = [round(-0.02 + i * 0.03, 3) for i in range(9)]  # -0.02 to 0.22
    if theta_grid is None:
        theta_grid = list(range(-90, 91, 15))
    if dist_grid is None:
        dist_grid = [0.07, 0.10]

    results = []
    for cx in x_grid:
        for cy in y_grid:
            for th in theta_grid:
                for d in dist_grid:
                    succ, dist_appr, final_dist = solvable_fn(cx, cy, th, d)
                    results.append({
                        "cube_x": cx,
                        "cube_y": cy,
                        "theta_deg": th,
                        "dist": d,
                        "success": succ,
                        "disturbed_approach": dist_appr,
                        "final_cube_goal_m": final_dist,
                    })

    return {
        "x_grid": x_grid,
        "y_grid": y_grid,
        "theta_deg_grid": theta_grid,
        "dist_grid": dist_grid,
        "results": results,
    }


def test_derive_disturbed_approach_counted_as_solvable():
    """R6: Solvability is outcome-only (final_cube_goal_m <= 0.05m).
    Disturbed approach is counted as telemetry but does NOT fail the configuration."""
    def solvable(cx, cy, th, d):
        # All points with x >= 0.38 and abs(th) <= 60 have final_m <= 0.05,
        # but at th == -60 approach was disturbed.
        if cx < 0.38 or abs(th) > 60:
            return False, False, 0.12
        if th == -60:
            return True, True, 0.03  # Disturbed approach, but final 3cm <= 5cm!
        return True, False, 0.02

    scan = make_synthetic_scan(solvable)
    res = derive_p4c_geometry(scan, candidate_thetas=[60, 75, 90])

    tel = res["telemetry"]
    assert tel["disturbed_approach_count"] > 0, "Telemetry must count disturbed approaches"
    assert tel["solvable_configs"] > 0

    # Under R6, candidate 60° must PASS because final distance <= 0.05m
    row_60 = next(r for r in res["candidate_table"] if r["theta_max_deg"] == 60)
    assert row_60["status"] == "PASS"
    assert row_60["box_x"][0] >= 0.38
    assert row_60["n_points"] > 0

    # Verify that a config with final > 0.05m is NOT solvable even if disturbed=False
    rec_fail = {"final_cube_goal_m": 0.08, "disturbed_approach": False}
    assert not is_record_solvable(rec_fail)

    # Verify that a config with final <= 0.05m is solvable even if disturbed=True
    rec_pass_disturbed = {"final_cube_goal_m": 0.045, "disturbed_approach": True}
    assert is_record_solvable(rec_pass_disturbed)


def test_derive_multi_input_merge_and_overwrite(tmp_path: Path):
    """Rework 6: Support multiple --input files. Later files override earlier files for matching configs."""
    cfg = (0.40, 0.01, 60, 0.07)

    # Run 1: config failed (final distance 0.12m)
    run1_data = {
        "x_grid": [0.40],
        "y_grid": [0.01],
        "theta_deg_grid": [60],
        "dist_grid": [0.07],
        "results": [
            {
                "cube_x": cfg[0],
                "cube_y": cfg[1],
                "theta_deg": cfg[2],
                "dist": cfg[3],
                "final_cube_goal_m": 0.12,
                "disturbed_approach": False,
                "success": False,
            }
        ],
    }
    file1 = tmp_path / "scan_part1.json"
    file1.write_text(json.dumps(run1_data), encoding="utf-8")

    # Run 2: config retested and succeeded (final distance 0.02m) + new config
    run2_data = {
        "x_grid": [0.40],
        "y_grid": [0.01, 0.04],
        "theta_deg_grid": [60],
        "dist_grid": [0.07],
        "results": [
            {
                "cube_x": cfg[0],
                "cube_y": cfg[1],
                "theta_deg": cfg[2],
                "dist": cfg[3],
                "final_cube_goal_m": 0.02,
                "disturbed_approach": True,
                "success": True,
            },
            {
                "cube_x": 0.40,
                "cube_y": 0.04,
                "theta_deg": 60,
                "dist": 0.07,
                "final_cube_goal_m": 0.03,
                "disturbed_approach": False,
                "success": True,
            },
        ],
    }
    file2 = tmp_path / "scan_part2.json"
    file2.write_text(json.dumps(run2_data), encoding="utf-8")

    merged, overwritten = merge_scan_inputs([file1, file2])

    assert len(overwritten) == 1
    ov = overwritten[0]
    assert ov["cube_x"] == 0.40
    assert ov["theta_deg"] == 60
    assert ov["previous_final_m"] == 0.12
    assert ov["new_final_m"] == 0.02
    assert ov["previous_solvable"] is False
    assert ov["new_solvable"] is True
    assert str(file1) in ov["previous_source"]
    assert str(file2) in ov["new_source"]

    # In merged data, the overwritten config should reflect run 2
    merged_cfg = next(r for r in merged["results"] if r["cube_y"] == 0.01)
    assert merged_cfg["final_cube_goal_m"] == 0.02
    assert is_record_solvable(merged_cfg) is True
    assert len(merged["results"]) == 2


def test_derive_candidate_thetas_table_and_tie_breaker():
    """Objective: evaluate candidate theta_max in {60, 75, 90}, find maximal box (points max, tie-break by area)."""
    # Create synthetic grid where:
    # At 60°: box spans 6 points (2x3) with area 0.03 * 0.06 = 0.0018
    # At 75°: box spans 4 points (2x2) with area 0.03 * 0.03 = 0.0009
    # At 90°: no points solvable -> FAIL
    def solvable(cx, cy, th, d):
        if abs(th) <= 60 and 0.40 <= cx <= 0.43 and 0.01 <= cy <= 0.07:
            return True, False, 0.02
        if abs(th) <= 75 and 0.40 <= cx <= 0.43 and 0.01 <= cy <= 0.04:
            return True, False, 0.02
        return False, False, 0.15

    scan = make_synthetic_scan(solvable)
    res = derive_p4c_geometry(scan, candidate_thetas=[60, 75, 90])

    table = res["candidate_table"]
    assert len(table) == 3

    t60 = table[0]
    assert t60["theta_max_deg"] == 60
    assert t60["status"] == "PASS"
    assert t60["n_points"] == 6
    assert math.isclose(t60["area"], 0.03 * 0.06, abs_tol=1e-5)

    t75 = table[1]
    assert t75["theta_max_deg"] == 75
    assert t75["status"] == "PASS"
    assert t75["n_points"] == 4
    assert math.isclose(t75["area"], 0.03 * 0.03, abs_tol=1e-5)

    t90 = table[2]
    assert t90["theta_max_deg"] == 90
    assert t90["status"] == "FAIL"
    assert t90["n_points"] == 0
    assert t90["box_x"] is None

    # Test tie-breaking logic directly:
    # 4 points in a 2x2 grid (area 0.0009) vs 4 points on a 1x4 line (area 0.0)
    x_grid = [0.40, 0.43]
    y_grid = [0.01, 0.04]
    # All 4 points solvable:
    res_map = {
        (0.40, 0.01, 0, 0.07): True,
        (0.40, 0.04, 0, 0.07): True,
        (0.43, 0.01, 0, 0.07): True,
        (0.43, 0.04, 0, 0.07): True,
    }
    box = find_largest_box_for_range(
        x_grid=x_grid,
        y_grid=y_grid,
        theta_min_deg=0,
        theta_max_deg=0,
        theta_step=15,
        dist_grid=[0.07],
        results_map=res_map,
        min_x=0.38,
    )
    assert box is not None
    assert box["n_points"] == 4
    assert box["area"] > 0.0  # 2D area selected over line


def test_format_candidate_table_markdown():
    """Verify markdown table formatting."""
    candidate_table = [
        {
            "theta_max_deg": 60,
            "box_x": (0.40, 0.46),
            "box_y": (0.01, 0.10),
            "n_points": 12,
            "area": 0.0054,
            "theta_plus_max_deg": 75,
            "theta_minus_max_deg": 60,
            "status": "PASS",
        },
        {
            "theta_max_deg": 90,
            "box_x": None,
            "box_y": None,
            "n_points": 0,
            "area": 0.0,
            "theta_plus_max_deg": 0,
            "theta_minus_max_deg": 0,
            "status": "FAIL",
        },
    ]
    md = format_candidate_table(candidate_table)
    assert "| Candidate θ_max |" in md
    assert "±60°" in md
    assert "[0.40, 0.46]" in md
    assert "PASS" in md
    assert "±90°" in md
    assert "FAIL" in md


def test_derive_variants_tried_outcome_solvability():
    """R6: If any variant has final <= 0.05m, it is solvable; telemetry counts timeouts & disturbed."""
    rec = {
        "cube_x": 0.40,
        "cube_y": 0.01,
        "theta_deg": 60,
        "dist": 0.07,
        "variants_tried": [
            {"variant": "V1", "failure_reason": "timeout", "final_cube_goal_m": 0.20, "disturbed_approach": False},
            {"variant": "V2", "failure_reason": None, "final_cube_goal_m": 0.04, "disturbed_approach": True},
        ],
    }
    assert is_record_solvable(rec) is True

    tel = compute_telemetry([rec])
    assert tel["solvable_configs"] == 1
    assert tel["timeout_count"] == 1
    assert tel["disturbed_approach_count"] == 1


def test_derive_asymmetric_reach():
    """R5: Asymmetric reach calculation per candidate box."""
    def solvable(cx, cy, th, d):
        if cx < 0.38:
            return False, False, 0.15
        # Positive reach extends to +75, negative only to -60
        if -60 <= th <= 75:
            return True, False, 0.02
        return False, False, 0.15

    scan = make_synthetic_scan(solvable)
    res = derive_p4c_geometry(scan, candidate_thetas=[60, 75, 90])

    row_60 = next(r for r in res["candidate_table"] if r["theta_max_deg"] == 60)
    assert row_60["status"] == "PASS"
    assert row_60["theta_plus_max_deg"] == 75
    assert row_60["theta_minus_max_deg"] == 60
