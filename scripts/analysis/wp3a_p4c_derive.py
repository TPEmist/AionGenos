"""wp3a_p4c_derive.py — Derive Pin-4c geometry from reachability scan (Spec §1, REVISION 1 R5, R6).

Derives:
  - Solvability per config: outcome only (final_cube_goal_m <= 0.05, R6).
  - Telemetry: disturbed_approach, timeout, nan counts.
  - Candidate table: for each theta_max in {60, 75, 90} deg, finds the maximal
    axis-aligned cube box (points max, tie-break by area) solvable for all theta
    and both push distances.
  - Supports merging multiple input JSON files with later files overriding earlier ones
    and logging overwritten configs for audit.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple


def is_record_solvable(r: Dict[str, Any], goal_threshold_m: float = 0.05) -> bool:
    """Config is solvable iff ANY variant has final_cube_goal_m <= goal_threshold_m (R6 outcome only).
    disturbed_approach and timeout are telemetry only, not solvability disqualifiers."""
    # 1. Check variants_tried if present
    variants = r.get("variants_tried")
    if variants and isinstance(variants, list):
        for v in variants:
            dist = v.get("final_cube_goal_m")
            if dist is not None:
                if float(dist) <= goal_threshold_m + 1e-6:
                    return True
            elif bool(v.get("success", False)):
                return True
        return False

    # 2. Check top-level final_cube_goal_m
    final_dist = r.get("final_cube_goal_m")
    if final_dist is not None:
        return float(final_dist) <= goal_threshold_m + 1e-6

    # 3. Fallback to boolean success
    return bool(r.get("success", False))


def compute_telemetry(results: Sequence[Dict[str, Any]]) -> Dict[str, int]:
    """Compute audit telemetry counts across scan results."""
    disturbed_count = 0
    timeout_count = 0
    nan_count = 0
    solvable_count = 0

    for r in results:
        if is_record_solvable(r):
            solvable_count += 1

        disturbed = bool(r.get("disturbed_approach", False))
        if not disturbed and "variants_tried" in r and isinstance(r["variants_tried"], list):
            disturbed = any(bool(v.get("disturbed_approach", False)) for v in r["variants_tried"])
        if disturbed:
            disturbed_count += 1

        has_timeout = (r.get("failure_reason") == "timeout")
        if not has_timeout and "variants_tried" in r and isinstance(r["variants_tried"], list):
            has_timeout = any(v.get("failure_reason") == "timeout" for v in r["variants_tried"])
        if has_timeout:
            timeout_count += 1

        has_nan = (r.get("failure_reason") == "nan")
        if not has_nan and "variants_tried" in r and isinstance(r["variants_tried"], list):
            has_nan = any(v.get("failure_reason") == "nan" for v in r["variants_tried"])
        if has_nan:
            nan_count += 1

    return {
        "total_configs": len(results),
        "solvable_configs": solvable_count,
        "disturbed_approach_count": disturbed_count,
        "timeout_count": timeout_count,
        "nan_count": nan_count,
    }


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
            key = (round(cx, 3), round(cy, 3), int(th), round(d, 3))
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
    """Search all axis-aligned subgrids of x_grid x y_grid with x >= min_x.
    Objective: maximize n_points, tie-break by area."""
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

                    if all_ok and n_pts > 0:
                        area = round((x2 - x1) * (y2 - y1), 6)
                        # Lead: 點數最多，平手取面積大
                        if (n_pts > best_points) or (n_pts == best_points and area > best_area):
                            best_points = n_pts
                            best_area = area
                            best_box = {
                                "box_x": (round(x1, 3), round(x2, 3)),
                                "box_y": (round(y1, 3), round(y2, 3)),
                                "area": area,
                                "n_points": n_pts,
                            }

    return best_box


def compute_asymmetric_reach(
    box_xs: Sequence[float],
    box_ys: Sequence[float],
    theta_step: int,
    dist_grid: Sequence[float],
    results_map: Dict[Tuple[float, float, int, float], bool],
    max_theta: int = 90,
) -> Tuple[int, int]:
    """Compute max theta+ and theta- separately such that all points in box are solvable."""
    theta_plus = 0
    for th in range(0, max_theta + 1, theta_step):
        all_ok = all(
            is_point_solvable(results_map, x, y, th, th, theta_step, dist_grid)
            for x in box_xs for y in box_ys
        )
        if all_ok:
            theta_plus = th
        else:
            break

    theta_minus = 0
    for th in range(0, max_theta + 1, theta_step):
        neg_th = -th
        all_ok = all(
            is_point_solvable(results_map, x, y, neg_th, neg_th, theta_step, dist_grid)
            for x in box_xs for y in box_ys
        )
        if all_ok:
            theta_minus = th
        else:
            break

    return theta_plus, theta_minus


def derive_p4c_geometry(
    scan_data: Dict[str, Any],
    candidate_thetas: Sequence[int] = (60, 75, 90),
    min_cube_x: float = 0.38,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Derive Pin-4c geometry table across candidate theta_max values."""
    x_grid = scan_data.get("x_grid", [0.34, 0.37, 0.40, 0.43, 0.46, 0.49, 0.52])
    y_grid = scan_data.get("y_grid", [-0.02, 0.01, 0.04, 0.07, 0.10, 0.13, 0.16, 0.19, 0.22])
    theta_deg_grid = sorted(scan_data.get("theta_deg_grid", list(range(-90, 91, 15))))
    dist_grid = scan_data.get("dist_grid", [0.07, 0.10])
    results = scan_data.get("results", [])

    results_map: Dict[Tuple[float, float, int, float], bool] = {}
    for r in results:
        k = (round(float(r["cube_x"]), 3), round(float(r["cube_y"]), 3),
             int(round(float(r["theta_deg"]))), round(float(r["dist"]), 3))
        results_map[k] = is_record_solvable(r)

    telemetry = compute_telemetry(results)

    theta_step = 15
    for i in range(len(theta_deg_grid) - 1):
        step = theta_deg_grid[i + 1] - theta_deg_grid[i]
        if step > 0:
            theta_step = step
            break

    candidate_table: List[Dict[str, Any]] = []
    for th in candidate_thetas:
        box = find_largest_box_for_range(
            x_grid, y_grid, -th, th, theta_step, dist_grid, results_map, min_x=min_cube_x
        )
        if box is not None:
            bx1, bx2 = box["box_x"]
            by1, by2 = box["box_y"]
            box_xs = [x for x in x_grid if bx1 - 1e-4 <= x <= bx2 + 1e-4]
            box_ys = [y for y in y_grid if by1 - 1e-4 <= y <= by2 + 1e-4]
            th_plus, th_minus = compute_asymmetric_reach(box_xs, box_ys, theta_step, dist_grid, results_map)
            entry = {
                "theta_max_deg": th,
                "theta_max_rad": round(math.radians(th), 4),
                "box_x": box["box_x"],
                "box_y": box["box_y"],
                "area": box["area"],
                "n_points": box["n_points"],
                "theta_plus_max_deg": th_plus,
                "theta_minus_max_deg": th_minus,
                "status": "PASS",
            }
        else:
            entry = {
                "theta_max_deg": th,
                "theta_max_rad": round(math.radians(th), 4),
                "box_x": None,
                "box_y": None,
                "area": 0.0,
                "n_points": 0,
                "theta_plus_max_deg": 0,
                "theta_minus_max_deg": 0,
                "status": "FAIL",
            }
        candidate_table.append(entry)

    # For backward-compatible convenience aliases: pick 60° or the highest passing candidate
    pass_entries = [e for e in candidate_table if e["status"] == "PASS"]
    best_candidate = pass_entries[0] if pass_entries else candidate_table[0]

    return {
        "candidate_table": candidate_table,
        "telemetry": telemetry,
        "dist_range": dist_grid,
        "x_grid": x_grid,
        "y_grid": y_grid,
        "theta_deg_grid": theta_deg_grid,
        # Backward-compatible convenience aliases:
        "status": "PASS" if pass_entries else "STOP",
        "theta_plus_max_deg": best_candidate["theta_plus_max_deg"],
        "theta_minus_max_deg": best_candidate["theta_minus_max_deg"],
        "theta_max_symmetric_deg": best_candidate["theta_max_deg"] if best_candidate["status"] == "PASS" else 0,
        "theta_max_rad": best_candidate["theta_max_rad"] if best_candidate["status"] == "PASS" else 0.0,
        "cube_box_x": best_candidate["box_x"],
        "cube_box_y": best_candidate["box_y"],
        "cube_box_area": best_candidate["area"],
        "n_grid_points": best_candidate["n_points"],
        "tradeoff_report": (
            f"Evaluated {len(candidate_thetas)} candidate theta_max values. "
            f"Passing candidates: {[e['theta_max_deg'] for e in pass_entries]}. "
            f"Solvable configs: {telemetry['solvable_configs']}/{telemetry['total_configs']} "
            f"(disturbed: {telemetry['disturbed_approach_count']}, timeouts: {telemetry['timeout_count']})."
        ),
    }


def merge_scan_inputs(
    input_paths: Sequence[str | Path] | str | Path,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Merge multiple scan JSON files. Later files override earlier files for matching configs.

    Returns (merged_scan_data, overwritten_configs).
    """
    if isinstance(input_paths, (str, Path)):
        input_paths = [input_paths]

    merged_results: Dict[Tuple[float, float, int, float], Dict[str, Any]] = {}
    config_sources: Dict[Tuple[float, float, int, float], str] = {}
    overwritten_configs: List[Dict[str, Any]] = []

    all_x = set()
    all_y = set()
    all_th = set()
    all_d = set()
    merged_skipped = []

    for path_in in input_paths:
        p = Path(path_in)
        if not p.exists():
            raise FileNotFoundError(f"Input file not found: {p}")
        with open(p, "r", encoding="utf-8") as fp:
            data = json.load(fp)

        src_str = str(p)
        for x in data.get("x_grid", []):
            all_x.add(round(float(x), 3))
        for y in data.get("y_grid", []):
            all_y.add(round(float(y), 3))
        for th in data.get("theta_deg_grid", []):
            all_th.add(int(round(float(th))))
        for d in data.get("dist_grid", []):
            all_d.add(round(float(d), 3))

        for s in data.get("skipped", []):
            merged_skipped.append(s)

        for r in data.get("results", []):
            cx = round(float(r["cube_x"]), 3)
            cy = round(float(r["cube_y"]), 3)
            th = int(round(float(r["theta_deg"])))
            d = round(float(r["dist"]), 3)
            k = (cx, cy, th, d)

            if k in merged_results:
                old_rec = merged_results[k]
                overwritten_configs.append({
                    "cube_x": cx,
                    "cube_y": cy,
                    "theta_deg": th,
                    "dist": d,
                    "previous_source": config_sources[k],
                    "new_source": src_str,
                    "previous_final_m": old_rec.get("final_cube_goal_m"),
                    "new_final_m": r.get("final_cube_goal_m"),
                    "previous_solvable": is_record_solvable(old_rec),
                    "new_solvable": is_record_solvable(r),
                })

            merged_results[k] = r
            config_sources[k] = src_str
            all_x.add(cx)
            all_y.add(cy)
            all_th.add(th)
            all_d.add(d)

    merged_data = {
        "x_grid": sorted(all_x),
        "y_grid": sorted(all_y),
        "theta_deg_grid": sorted(all_th),
        "dist_grid": sorted(all_d),
        "results": list(merged_results.values()),
        "skipped": merged_skipped,
    }
    return merged_data, overwritten_configs


def format_candidate_table(table: Sequence[Dict[str, Any]]) -> str:
    """Format candidate geometry table into markdown."""
    lines = [
        "| Candidate θ_max | Cube Box X   | Cube Box Y   | Points | Area (m²) | θ+ max | θ- max | Status |",
        "|-----------------|--------------|--------------|--------|-----------|--------|--------|--------|",
    ]
    for row in table:
        th = f"±{row['theta_max_deg']}°"
        bx = f"[{row['box_x'][0]:.2f}, {row['box_x'][1]:.2f}]" if row.get("box_x") else "None"
        by = f"[{row['box_y'][0]:.2f}, {row['box_y'][1]:.2f}]" if row.get("box_y") else "None"
        pts = str(row.get("n_points", 0))
        area = f"{row.get('area', 0.0):.6f}"
        th_p = f"+{row.get('theta_plus_max_deg', 0)}°"
        th_m = f"-{row.get('theta_minus_max_deg', 0)}°"
        st = row.get("status", "FAIL")
        lines.append(f"| {th:<15} | {bx:<12} | {by:<12} | {pts:<6} | {area:<9} | {th_p:<6} | {th_m:<6} | {st:<6} |")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="Derive Pin-4c geometry table from scan JSON(s).")
    ap.add_argument("--input", "-i", nargs="+", default=["logs/wp3a_reach_scan_p4c.json"],
                    help="One or more scan JSON input files. Later files override earlier files.")
    ap.add_argument("--output", "-o", type=str, default="logs/wp3a_p4c_derived.json")
    ap.add_argument("--candidates", type=int, nargs="+", default=[60, 75, 90],
                    help="Candidate theta_max values in degrees (default: 60 75 90)")
    args = ap.parse_args()

    input_paths = [Path(p) for p in args.input]
    for p in input_paths:
        if not p.exists():
            print(f"Error: input file {p} does not exist.", flush=True)
            sys.exit(1)

    merged_data, overwritten = merge_scan_inputs(input_paths)
    print(f"[P4C DERIVE] Loaded {len(input_paths)} input file(s):", flush=True)
    for p in input_paths:
        print(f"  - {p}", flush=True)
    print(f"[P4C DERIVE] Total unique configs: {len(merged_data['results'])}", flush=True)
    if overwritten:
        print(f"[P4C DERIVE] Overwritten configs ({len(overwritten)}):", flush=True)
        for ov in overwritten:
            print(f"  * ({ov['cube_x']}, {ov['cube_y']}, th={ov['theta_deg']}°, d={ov['dist']}): "
                  f"{ov['previous_source']} -> {ov['new_source']} (final_m: {ov['previous_final_m']} -> {ov['new_final_m']})",
                  flush=True)

    res = derive_p4c_geometry(merged_data, candidate_thetas=args.candidates)
    res["inputs"] = [str(p) for p in input_paths]
    res["overwritten_configs"] = overwritten

    # Print candidate table
    print("\n[P4C DERIVE] Candidate Geometry Table:", flush=True)
    print(format_candidate_table(res["candidate_table"]), flush=True)

    # Print telemetry
    tel = res["telemetry"]
    print(f"\n[P4C DERIVE TELEMETRY] Total configs: {tel['total_configs']}, "
          f"Solvable (dist<=0.05m): {tel['solvable_configs']}, "
          f"Disturbed approach: {tel['disturbed_approach_count']}, "
          f"Timeouts: {tel['timeout_count']}, NaNs: {tel['nan_count']}", flush=True)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fp:
        json.dump(res, fp, indent=2)
    print(f"\n[P4C DERIVE] Output written to {args.output}", flush=True)

    sys.exit(0)


if __name__ == "__main__":
    main()
