"""Unit tests for Pin-4c scan derivation (Spec §1, AC2, REVISION 1 R5).
Pure CPU tests on synthetic scan JSONs — no Isaac/GPU.
"""
from __future__ import annotations

import math
from scripts.analysis.wp3a_p4c_derive import (
    derive_p4c_geometry,
    find_largest_box_for_range,
    is_point_solvable,
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
                    succ, dist_appr = solvable_fn(cx, cy, th, d)
                    results.append({
                        "cube_x": cx,
                        "cube_y": cy,
                        "theta_deg": th,
                        "dist": d,
                        "success": succ,
                        "disturbed_approach": dist_appr,
                        "final_cube_goal_m": 0.02 if succ else 0.12,
                    })

    return {
        "x_grid": x_grid,
        "y_grid": y_grid,
        "theta_deg_grid": theta_grid,
        "dist_grid": dist_grid,
        "results": results,
    }


def test_derive_all_succeed_gives_90deg_and_full_box():
    """When all configurations succeed, theta_max reaches 90° and box spans all valid x>=0.38."""
    scan = make_synthetic_scan(lambda cx, cy, th, d: (True, False))
    res = derive_p4c_geometry(scan, min_required_theta_deg=60.0)

    assert res["status"] == "PASS"
    assert res["theta_plus_max_deg"] == 90
    assert res["theta_minus_max_deg"] == 90
    assert res["theta_max_symmetric_deg"] == 90
    assert res["cube_box_x"][0] >= 0.38
    assert res["n_grid_points"] > 10


def test_derive_asymmetric_reach():
    """R5: Derive theta+ and theta- separately; symmetric range is +-min(theta+, theta-)."""
    # Suppose positive angles up to +75° succeed, but negative angles only up to -60° succeed
    def solvable(cx, cy, th, d):
        if th > 75:
            return False, False
        if th < -60:
            return False, False
        return True, False

    scan = make_synthetic_scan(solvable)
    res = derive_p4c_geometry(scan, min_required_theta_deg=60.0)

    assert res["status"] == "PASS"
    assert res["theta_plus_max_deg"] == 75
    assert res["theta_minus_max_deg"] == 60
    assert res["theta_max_symmetric_deg"] == 60
    assert res["theta_max_rad"] == round(math.radians(60.0), 4)


def test_derive_disturbed_approach_counted_as_failure():
    """R4/R6: Disturbed approach is a configuration failure."""
    # Suppose at theta=-60°, approach was disturbed
    def solvable(cx, cy, th, d):
        if th == -60:
            return True, True  # success=True but disturbed_approach=True -> failure
        if th > 60 or th < -45:
            return False, False
        return True, False

    scan = make_synthetic_scan(solvable)
    res = derive_p4c_geometry(scan, min_required_theta_deg=60.0)

    # -60° failed due to disturbed approach, so theta^- only reaches 45°
    assert res["theta_minus_max_deg"] <= 45
    assert res["theta_max_symmetric_deg"] <= 45
    assert res["status"] == "STOP"  # below 60°


def test_derive_below_60deg_reports_stop_and_tradeoff():
    """When symmetric reach is below 60°, status must be STOP and report trade-off."""
    def solvable(cx, cy, th, d):
        if abs(th) > 45:
            return False, False
        return True, False

    scan = make_synthetic_scan(solvable)
    res = derive_p4c_geometry(scan, min_required_theta_deg=60.0)

    assert res["status"] == "STOP"
    assert res["theta_max_symmetric_deg"] == 45
    assert "STOP" in res["tradeoff_report"]


def test_derive_any_variant_success_counted():
    """Rework 4: derive treats any successful variant as success."""
    scan = make_synthetic_scan(lambda cx, cy, th, d: (False, True))
    # Give all records a successful variant V3
    for r in scan["results"]:
        r["variants_tried"] = [
            {"variant": "V1", "success": False, "disturbed_approach": True},
            {"variant": "V2", "success": False, "disturbed_approach": True},
            {"variant": "V3", "success": True, "disturbed_approach": False},
        ]
    res = derive_p4c_geometry(scan, min_required_theta_deg=60.0)
    assert res["status"] == "PASS"
    assert res["theta_max_symmetric_deg"] == 90
    assert res["theta_plus_max_deg"] == 90
    assert res["theta_minus_max_deg"] == 90

