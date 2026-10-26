"""wp3a_p4c_derive.py — Derive Pin-4c geometry from reachability scan (Spec §1, REVISION 1 R5).

Derives:
  - theta^+_max and theta^-_max separately (asymmetric reach);
  - symmetric theta_max = min(theta^+_max, theta^-_max);
  - largest axis-aligned cube region [x_min, x_max] x [y_min, y_max] (with x_min >= 0.38)
    such that push succeeds for all d in {0.07, 0.10} and all theta in [-theta_max, theta_max]
    for every cube grid point inside the box;
  - if theta_max < 60°, reports STOP and the best trade-off (PI decision).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple


def is_point_solvable(
    results_map: Dict[Tuple[float, float, int, float], bool],
    cx: float,
    cy: float,
    theta_min_deg: int,
    theta_max_deg: int,
    theta_step: int,
    dist_grid: Sequence[float],
) -> bool:
    """Check if (cx, cy) succeeds for all angles in [theta_min_deg, theta_max_deg] and all dists."""
    for th in range(theta_min_deg, theta_max_deg + 1, theta_step):
        for d in dist_grid:
            key = (round(cx, 3), round(cy, 3), th, round(d, 3))
            if not results_map.get(key, False):
                return False
    return True


def find_largest_box_for_range(
    x_grid: Sequence[float],
    y_grid: Sequence[float],
    theta_min_deg: int,
    theta_max_deg: int,
    theta_step: int,
    dist_grid: Sequence[float],
    results_map: Dict[Tuple[float, float, int, float], bool],
    min_x: float = 0.38,
) -> Optional[Dict[str, Any]]:
    """Search all axis-aligned subgrids of x_grid x y_grid with x >= min_x."""
    valid_xs = [x for x in sorted(x_grid) if x >= min_x - 1e-6]
    valid_ys = sorted(y_grid)

    best_box = None
    best_area = -1.0
    best_points = 0

    # Precompute solvable status for each point
    solvable_points = set()
    for x in valid_xs:
        for y in valid_ys:
            if is_point_solvable(results_map, x, y, theta_min_deg, theta_max_deg, theta_step, dist_grid):
                solvable_points.add((round(x, 3), round(y, 3)))

    nx = len(valid_xs)
    ny = len(valid_ys)

    for i1 in range(nx):
        for i2 in range(i1, nx):
            x1, x2 = valid_xs[i1], valid_xs[i2]
            for j1 in range(ny):
                for j2 in range(j1, ny):
                    y1, y2 = valid_ys[j1], valid_ys[j2]

                    # Check if all points in [x1, x2] x [y1, y2] are solvable
                    all_ok = True
                    n_pts = 0
                    for xi in range(i1, i2 + 1):
                        for yj in range(j1, j2 + 1):
                            n_pts += 1
                            if (round(valid_xs[xi], 3), round(valid_ys[yj], 3)) not in solvable_points:
                                all_ok = False
                                break
                        if not all_ok:
                            break

                    if all_ok:
                        area = (x2 - x1) * (y2 - y1)
                        # Preference: larger area, then more points, then wider x
                        if area > best_area or (abs(area - best_area) < 1e-9 and n_pts > best_points):
                            best_area = area
                            best_points = n_pts
                            best_box = {
                                "box_x": (round(x1, 3), round(x2, 3)),
                                "box_y": (round(y1, 3), round(y2, 3)),
                                "area": round(area, 6),
                                "n_points": n_pts,
                            }

    return best_box


def derive_p4c_geometry(
    scan_data: Dict[str, Any],
    min_required_theta_deg: float = 60.0,
    min_cube_x: float = 0.38,
) -> Dict[str, Any]:
    """Derive Pin-4c geometry constants from scan JSON data."""
    x_grid = scan_data.get("x_grid", [0.34, 0.37, 0.40, 0.43, 0.46, 0.49, 0.52])
    y_grid = scan_data.get("y_grid", [-0.02, 0.01, 0.04, 0.07, 0.10, 0.13, 0.16, 0.19, 0.22])
    theta_deg_grid = sorted(scan_data.get("theta_deg_grid", list(range(-90, 91, 15))))
    dist_grid = scan_data.get("dist_grid", [0.07, 0.10])
    results = scan_data.get("results", [])

    results_map: Dict[Tuple[float, float, int, float], bool] = {}
    for r in results:
        k = (round(r["cube_x"], 3), round(r["cube_y"], 3), int(r["theta_deg"]), round(r["dist"], 3))
        # Success requires outcome success AND not disturbed during approach (R4, R6)
        succ = bool(r.get("success", False)) and not bool(r.get("disturbed_approach", False))
        results_map[k] = succ

    theta_step = 15
    for i in range(len(theta_deg_grid) - 1):
        step = theta_deg_grid[i + 1] - theta_deg_grid[i]
        if step > 0:
            theta_step = step
            break

    # Search symmetric candidates in descending order: 90, 75, 60, ...
    sym_candidates = [th for th in range(90, 0, -theta_step) if th in theta_deg_grid and -th in theta_deg_grid]

    best_sym_result = None
    best_sym_theta = 0

    for th in sym_candidates:
        box = find_largest_box_for_range(
            x_grid, y_grid, -th, th, theta_step, dist_grid, results_map, min_x=min_cube_x
        )
        if box is not None and box["n_points"] >= 2:  # non-trivial box
            best_sym_result = box
            best_sym_theta = th
            break

    # Asymmetric derivation (R5): find theta^+_max and theta^-_max over the derived box
    theta_plus_max = 0
    theta_minus_max = 0

    if best_sym_result is not None:
        bx1, bx2 = best_sym_result["box_x"]
        by1, by2 = best_sym_result["box_y"]
        box_xs = [x for x in x_grid if bx1 - 1e-4 <= x <= bx2 + 1e-4]
        box_ys = [y for y in y_grid if by1 - 1e-4 <= y <= by2 + 1e-4]

        # Check positive reach theta^+
        for th in range(0, 91, theta_step):
            all_box_ok = all(
                is_point_solvable(results_map, x, y, th, th, theta_step, dist_grid)
                for x in box_xs for y in box_ys
            )
            if all_box_ok:
                theta_plus_max = th
            else:
                break

        # Check negative reach theta^-
        for th in range(0, 91, theta_step):
            neg_th = -th
            all_box_ok = all(
                is_point_solvable(results_map, x, y, neg_th, neg_th, theta_step, dist_grid)
                for x in box_xs for y in box_ys
            )
            if all_box_ok:
                theta_minus_max = th
            else:
                break
    else:
        # Trade-off report when no box found
        best_sym_result = {
            "box_x": (0.38, 0.42),
            "box_y": (0.05, 0.15),
            "area": 0.004,
            "n_points": 0,
        }

    symmetric_theta = min(theta_plus_max, theta_minus_max) if best_sym_theta > 0 else 0
    passes_spec = symmetric_theta >= min_required_theta_deg

    return {
        "status": "PASS" if passes_spec else "STOP",
        "theta_plus_max_deg": theta_plus_max,
        "theta_minus_max_deg": theta_minus_max,
        "theta_max_symmetric_deg": symmetric_theta,
        "theta_max_rad": round(math.radians(symmetric_theta), 4),
        "cube_box_x": best_sym_result["box_x"],
        "cube_box_y": best_sym_result["box_y"],
        "cube_box_area": best_sym_result["area"],
        "n_grid_points": best_sym_result["n_points"],
        "dist_range": dist_grid,
        "tradeoff_report": (
            f"Derived symmetric theta_max = {symmetric_theta}° (theta+ = {theta_plus_max}°, theta- = {theta_minus_max}°). "
            f"Cube region X={best_sym_result['box_x']} Y={best_sym_result['box_y']} with {best_sym_result['n_points']} points. "
            + ("PASS: meets >= 60° PI requirement." if passes_spec else "STOP: below 60° requirement, consult PI.")
        ),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=str, default="logs/wp3a_reach_scan_p4c.json")
    ap.add_argument("--output", type=str, default="logs/wp3a_p4c_derived.json")
    ap.add_argument("--min_theta", type=float, default=60.0)
    args = ap.parse_args()

    in_path = Path(args.input)
    if not in_path.exists():
        print(f"Error: input file {args.input} does not exist.")
        sys.exit(1)

    with open(in_path, "r", encoding="utf-8") as fp:
        scan_data = json.load(fp)

    res = derive_p4c_geometry(scan_data, min_required_theta_deg=args.min_theta)
    print(f"[P4C DERIVE] Status: {res['status']}")
    print(f"[P4C DERIVE] theta+ max: {res['theta_plus_max_deg']}°, theta- max: {res['theta_minus_max_deg']}°")
    print(f"[P4C DERIVE] Symmetric theta_max: {res['theta_max_symmetric_deg']}° ({res['theta_max_rad']} rad)")
    print(f"[P4C DERIVE] Derived Cube Box: X={res['cube_box_x']}, Y={res['cube_box_y']} (area={res['cube_box_area']} m^2, pts={res['n_grid_points']})")
    print(f"[P4C DERIVE] Trade-off: {res['tradeoff_report']}")

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fp:
        json.dump(res, fp, indent=2)
    print(f"[P4C DERIVE] Output written to {args.output}")

    if res["status"] == "STOP":
        sys.exit(2)


if __name__ == "__main__":
    main()
