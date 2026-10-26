"""Instrument validation for WP1-3a push runs (generalised for all rungs).

Spec §4 + REVISION 1 (R7).
Authority: PI ruling 2026-10-22.
"""

from __future__ import annotations

import argparse
import collections
import glob
import hashlib
import json
import math
import os
import pathlib
import re
import statistics as st
import sys
from typing import Any, Dict, List, Optional, Sequence, Tuple

# Ensure workspace root is in sys.path
_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

H = 0.0240  # cube half-height (m)
SUCC_M = 0.05  # push success distance (m)
PUSH_ROUND_CAP = 12

FLAG_WHITELIST = frozenset({"push_plateau", "vlm_stop_premature", "env_auto_reset", "scripted_policy"})

COORD_PATTERN = re.compile(
    r"[XYZxyz]\s*=\s*-?\d+|\(\s*-?\d+\s*,\s*-?\d+\s*(?:,\s*-?\d+\s*)?\)"
)


def _is_flag_whitelisted(flag: str) -> bool:
    if flag.startswith("label:"):
        return True
    return flag in FLAG_WHITELIST


def _round_touched(contact: dict, cube_disp_m: float) -> bool:
    return contact.get("first_cube_move") is not None or cube_disp_m >= 0.01


def box_dist_quat(p: Sequence[float], c: Sequence[float], q: Sequence[float], half_h: float = H) -> float:
    """True oriented box distance using cube quaternion (w, x, y, z)."""
    # Transform point into box local frame
    qw, qx, qy, qz = q[0], q[1], q[2], q[3]
    # conjugate
    cqw, cqx, cqy, cqz = qw, -qx, -qy, -qz
    dx, dy, dz = p[0] - c[0], p[1] - c[1], p[2] - c[2]
    # Quat rotate (dx, dy, dz) by (cqw, cqx, cqy, cqz)
    tx = 2.0 * (cqy * dz - cqz * dy)
    ty = 2.0 * (cqz * dx - cqx * dz)
    tz = 2.0 * (cqx * dy - cqy * dx)
    lx = dx + cqw * tx + (cqy * tz - cqz * ty)
    ly = dy + cqw * ty + (cqz * tx - cqx * tz)
    lz = dz + cqw * tz + (cqx * ty - cqy * tx)

    ex = max(abs(lx) - half_h, 0.0)
    ey = max(abs(ly) - half_h, 0.0)
    ez = max(abs(lz) - half_h, 0.0)
    return math.sqrt(ex * ex + ey * ey + ez * ez)


def box_dist_axis_aligned(p: Sequence[float], c: Sequence[float], half_h: float = H) -> float:
    """Fallback axis-aligned box distance approximation."""
    return math.sqrt(sum(max(abs(a - b) - half_h, 0.0) ** 2 for a, b in zip(p, c)))


def validate_episodes(eps: List[Dict[str, Any]], ep_dirs: Optional[List[str]] = None) -> Tuple[bool, Dict[str, Any]]:
    """Validate a list of episode dicts. Returns (success: bool, stats: dict).
    
    HARD checks (any failure -> success=False):
      - feedback/runtime consistency (including PROGRESS/REGRESS/FLAT and d2 metric rule)
      - d1 units
      - env_auto_reset present
      - episode with outcome=timeout but fewer than PUSH_ROUND_CAP rounds (unless auto-reset)
      - flags outside whitelist
    """
    hard_failures: List[str] = []
    R = collections.Counter()
    reach_raw: List[float] = []
    reach_guarded: List[float] = []
    lowz: List[Tuple[float, float]] = []
    fb_bad: List[Tuple[Any, ...]] = []
    img_same = 0
    img_pairs = 0
    init_cg: List[float] = []
    min_cg: List[float] = []
    closest_tcp_cube: List[float] = []
    nrounds = 0
    zt = collections.Counter()
    outcomes = collections.Counter()
    contact_episodes = 0

    # Critic's 5 checks & Telemetry
    setpoint_clamps_total = 0
    rounds_with_setpoint_clamps = 0
    setpoint_clamp_steps_list: List[int] = []
    target_clamps_count = 0

    ori_err_final_list: List[float] = []
    ori_err_max_last20_list: List[float] = []
    ori_err_above_5deg = 0

    tau_flag_rounds = 0
    tau_flag_steps_max = 0
    tau_warn_rounds = 0
    tau_warn_steps_max = 0

    target_rel_x: List[float] = []
    target_rel_y: List[float] = []
    z_standby_count = 0
    z_contact_band_count = 0
    z_other_count = 0

    box_fallback_count = 0
    box_quat_count = 0

    total_injected_lessons = 0
    leaked_lesson_count = 0
    preamble_coord_redactions_total = 0
    settled_dists: List[float] = []
    settled_angles: List[float] = []
    settled_cubes_x: List[float] = []
    settled_cubes_y: List[float] = []

    for ep_idx, e in enumerate(eps):
        ep_id = e.get("episode_id", f"ep_{ep_idx}")
        flags = e.get("flags", [])
        outcome = e.get("outcome")
        outcomes[outcome] += 1
        rs = e.get("rounds", [])

        # HARD check: flag whitelist
        for f in flags:
            if not _is_flag_whitelisted(f):
                msg = f"HARD: Episode {ep_id} has invalid flag {f!r} not in whitelist"
                hard_failures.append(msg)
                R["hard_invalid_flag"] += 1

        # HARD check: env_auto_reset present
        if "env_auto_reset" in flags:
            msg = f"HARD: Episode {ep_id} has env_auto_reset in flags"
            hard_failures.append(msg)
            R["hard_env_auto_reset"] += 1

        # HARD check: timeout episode with fewer than PUSH_ROUND_CAP rounds
        if outcome == "timeout" and len(rs) < PUSH_ROUND_CAP and "env_auto_reset" not in flags:
            msg = f"HARD: Episode {ep_id} timeout with {len(rs)} rounds < {PUSH_ROUND_CAP} (no auto_reset flag)"
            hard_failures.append(msg)
            R["hard_premature_timeout"] += 1

        # HARD check: d1 frame-convention check
        if e.get("frame_convention"):
            f_line = e.get("frame_line")
            if not f_line:
                hard_failures.append(f"HARD: Episode {ep_id} frame_convention is True but frame_line is missing")
                R["hard_d1_missing_line"] += 1
            else:
                bounds_dict = e.get("workspace_bounds")
                if not bounds_dict or "x" not in bounds_dict or "y" not in bounds_dict or "z" not in bounds_dict:
                    R["d1_bounds_missing"] += 1
                else:
                    xb = bounds_dict["x"]
                    yb = bounds_dict["y"]
                    zb = bounds_dict["z"]
                    from aiongenos.vlm.scalar_guard import INT_MAX, INT_MIN
                    grid_span = float(INT_MAX - INT_MIN)
                    ux = (xb[1] - xb[0]) / grid_span * 100.0
                    uy = (yb[1] - yb[0]) / grid_span * 100.0
                    uz = (zb[1] - zb[0]) / grid_span * 100.0
                    expected_line = (
                        f"FRAME (base frame, same grid as the numbers above): "
                        f"+X = forward, away from the robot base; +Y = the robot's left; +Z = up. "
                        f"One grid unit = {ux:.2f} cm in X, {uy:.2f} cm in Y, {uz:.2f} cm in Z."
                    )
                    if f_line.strip() != expected_line.strip():
                        hard_failures.append(
                            f"HARD: Episode {ep_id} frame_line mismatch: {f_line!r} != {expected_line!r}"
                        )
                        R["hard_d1_unit_mismatch"] += 1
                    else:
                        R["d1_units_OK"] += 1

        # HARD check: pin4c geometry check (R3, R11)
        if e.get("geometry") == "pin4c":
            gs = e.get("goal_sample")
            if not gs:
                hard_failures.append(f"HARD: Episode {ep_id} geometry is pin4c but goal_sample is missing")
                R["hard_pin4c_missing_sample"] += 1
            else:
                dist = gs.get("dist")
                theta = gs.get("theta")
                from aiongenos.tasks.WP1_contact_testbed.pin4c_constants import PIN4C_THETA_MAX
                if dist is None or not (0.07 - 1e-6 <= dist <= 0.10 + 1e-6):
                    hard_failures.append(f"HARD: Episode {ep_id} pin4c commanded dist {dist} outside [0.07, 0.10]")
                    R["hard_pin4c_dist_out_of_bounds"] += 1
                elif theta is None or abs(theta) > PIN4C_THETA_MAX + 1e-6:
                    hard_failures.append(f"HARD: Episode {ep_id} pin4c commanded |theta| {abs(theta) if theta is not None else None} > theta_max {PIN4C_THETA_MAX}")
                    R["hard_pin4c_theta_out_of_bounds"] += 1
                else:
                    R["pin4c_sample_OK"] += 1

        # Injected lesson leak check
        for h in e.get("memory_hits", []):
            lesson = h.get("lesson")
            if not lesson and "ep_id" in h:
                hit_ep = h["ep_id"]
                cand_recaps = glob.glob(f"workspace/recaps*/{hit_ep}/recap.json") + \
                              glob.glob(f"workspace/recaps*/recap_{hit_ep}.json") + \
                              glob.glob(f"/home/control/AionGenos/workspace/recaps*/{hit_ep}/recap.json") + \
                              glob.glob(f"/home/control/AionGenos/workspace/recaps*/*/{hit_ep}/recap.json")
                if cand_recaps:
                    try:
                        with open(cand_recaps[0]) as rf:
                            lesson = json.load(rf).get("text_lesson")
                    except Exception:
                        pass
            if lesson:
                total_injected_lessons += 1
                if COORD_PATTERN.search(lesson):
                    leaked_lesson_count += 1

        preamble_coord_redactions_total += e.get("preamble_coord_redactions", 0)

        # Settled goal-cube telemetry
        c_init = e.get("init_cube_pose_b") or (rs[0].get("cube_b_pre") if rs else None)
        g_init = e.get("goal_pose_b") or (rs[0].get("goal_b_pre") if rs else None)
        if c_init is not None and g_init is not None:
            dx = g_init[0] - c_init[0]
            dy = g_init[1] - c_init[1]
            settled_dists.append(math.hypot(dx, dy))
            settled_angles.append(math.degrees(math.atan2(dy, dx)))
            settled_cubes_x.append(c_init[0])
            settled_cubes_y.append(c_init[1])

        if not rs:
            continue

        if rs[0].get("cube_goal_dist_m_pre") is not None:
            init_cg.append(rs[0]["cube_goal_dist_m_pre"])
        min_cg.append(min((r["cube_goal_dist_m"] for r in rs if r.get("cube_goal_dist_m") is not None), default=999.0))

        ep_had_contact = False
        prev_md5 = None
        d = ep_dirs[ep_idx] if ep_dirs and ep_idx < len(ep_dirs) else None

        for i, r in enumerate(rs):
            nrounds += 1
            target_int = r.get("eef_target_int")
            if target_int is not None and len(target_int) >= 3:
                zt[target_int[2]] += 1

            target_m = r.get("eef_target_m")
            cube_pre = r.get("cube_b_pre")
            if target_int is not None and len(target_int) >= 3 and cube_pre is not None and len(cube_pre) >= 3:
                if target_m is not None and len(target_m) >= 3:
                    target_rel_x.append(target_m[0] - cube_pre[0])
                    target_rel_y.append(target_m[1] - cube_pre[1])

                zt_val = target_int[2]
                cz = cube_pre[2]
                # init_tcp_z_int: standby height from initial TCP proprioception (round 1 start)
                init_tcp_z_int = rs[0].get("ee_start_int", [0, 0, 53])[2]
                # contact band = cube centre ± half-height mapped to z_int range
                from aiongenos.vlm.scalar_guard import metric_to_int
                zb = e.get("workspace_bounds", {}).get("z", (0.0, 0.7))
                z_lo, _ = metric_to_int(cz - H, zb)
                z_hi, _ = metric_to_int(cz + H, zb)

                if zt_val == init_tcp_z_int:
                    z_standby_count += 1
                elif z_lo <= zt_val <= z_hi:
                    z_contact_band_count += 1
                else:
                    z_other_count += 1

            # Reach errors (raw vs guarded)
            reach_err = r.get("tcp_reach_err_cm")
            if reach_err is not None:
                reach_raw.append(reach_err)

            tg = r.get("table_guard") or {}
            if tg.get("target_clamp"):
                target_clamps_count += 1
                R["target_clamp"] += 1
                # Guarded reach error
                guarded_b = tg["target_clamp"].get("guarded_tcp_target_b")
                tcp_final = r.get("tcp_final_b")
                if guarded_b is not None and tcp_final is not None:
                    g_err = math.sqrt(sum((a - b) ** 2 for a, b in zip(tcp_final, guarded_b))) * 100.0
                    reach_guarded.append(round(g_err, 2))
                elif reach_err is not None:
                    reach_guarded.append(reach_err)
            elif reach_err is not None:
                reach_guarded.append(reach_err)

            # Table guard setpoint clamp steps
            sp_clamps = tg.get("setpoint_clamp_steps", 0)
            setpoint_clamps_total += sp_clamps
            setpoint_clamp_steps_list.append(sp_clamps)
            if sp_clamps > 0:
                rounds_with_setpoint_clamps += 1

            # ORI telemetry
            ori_final = r.get("ori_err_deg_final")
            if ori_final is not None:
                ori_err_final_list.append(ori_final)
                if ori_final > 5.0:
                    ori_err_above_5deg += 1
            ori_last20 = r.get("ori_err_deg_max_last20")
            if ori_last20 is not None:
                ori_err_max_last20_list.append(ori_last20)

            # Tau telemetry
            tau_flags = r.get("tau_flag_steps", 0)
            if tau_flags > 0:
                tau_flag_rounds += 1
                tau_flag_steps_max = max(tau_flag_steps_max, tau_flags)
            tau_warns = r.get("tau_warn_steps", 0)
            if tau_warns > 0:
                tau_warn_rounds += 1
                tau_warn_steps_max = max(tau_warn_steps_max, tau_warns)

            # Contact tracking
            contact_info = r.get("contact") or {}
            cube_disp = r.get("cube_disp_m", 0.0)
            touched = _round_touched(contact_info, cube_disp)
            if touched:
                ep_had_contact = True

            # Closest TCP to cube
            if r.get("ee_start_b") and cube_pre:
                q_cube = r.get("cube_quat_b_pre")
                if q_cube is not None and len(q_cube) == 4:
                    box_quat_count += 1
                    cd = box_dist_quat(r["ee_start_b"], cube_pre, q_cube)
                else:
                    box_fallback_count += 1
                    cd = box_dist_axis_aligned(r["ee_start_b"], cube_pre)
                closest_tcp_cube.append(cd)

            if target_m is not None and len(target_m) >= 3 and target_m[2] < 0.52:
                tcp_final = r.get("tcp_final_b")
                if tcp_final and len(tcp_final) >= 3:
                    lowz.append((target_m[2], tcp_final[2]))

            # PNG verification (if dir given and pngs exist)
            if d:
                png_path = os.path.join(d, f"round_{i+1:02d}_pre.png")
                if os.path.exists(png_path):
                    try:
                        m = hashlib.md5(open(png_path, "rb").read()).hexdigest()
                        if prev_md5 is not None:
                            img_pairs += 1
                            img_same += (m == prev_md5)
                        prev_md5 = m
                    except Exception:
                        R["png_missing"] += 1
                else:
                    R["png_missing"] += 1

            # Round 1 feedback check
            if i == 0:
                if r.get("round_feedback"):
                    R["fb_on_round1"] += 1
                    hard_failures.append(f"HARD: Episode {ep_id} round 1 has feedback when it should be None")
                continue

            fb = r.get("round_feedback") or ""
            if not fb:
                R["fb_missing"] += 1
                continue

            # Validate round feedback against previous round
            p = rs[i - 1]
            try:
                nums = lambda pat: [int(x) for x in re.search(pat, fb).groups()]
                tgt = nums(r"predicted at: X=(-?\d+) Y=(-?\d+) Z=(-?\d+)")
                mv = nums(r"from X=(-?\d+) Y=(-?\d+) Z=(-?\d+) to X=(-?\d+) Y=(-?\d+) Z=(-?\d+)")

                # Box distances
                q_p = p.get("cube_quat_b_pre")
                q_r = r.get("cube_quat_b_pre")
                if q_p is not None and len(q_p) == 4:
                    box_p = box_dist_quat(p["ee_start_b"], p["cube_b_pre"], q_p)
                else:
                    box_p = box_dist_axis_aligned(p["ee_start_b"], p["cube_b_pre"])

                if q_r is not None and len(q_r) == 4:
                    box_r = box_dist_quat(r["ee_start_b"], r["cube_b_pre"], q_r)
                else:
                    box_r = box_dist_axis_aligned(r["ee_start_b"], r["cube_b_pre"])

                dist_m = re.search(r"Fingertip-to-cube distance: started at ([\d.]+) cm, ended at ([\d.]+)", fb)
                cg_m = re.search(r"Cube-to-goal distance: started at ([\d.]+) cm, ended at ([\d.]+)", fb)
                has_distances = dist_m is not None and cg_m is not None

                ok: Dict[str, bool] = {
                    "target==prev_target": tgt == p.get("eef_target_int"),
                    "move_from==prev_start": mv[:3] == p.get("ee_start_int"),
                    "move_to==this_start": mv[3:] == r.get("ee_start_int"),
                }

                if has_distances:
                    ts, te = map(float, dist_m.groups())
                    cs, ce = map(float, cg_m.groups())
                    ok["tip_start"] = abs(ts - 100 * box_p) <= 0.25
                    ok["tip_end"] = abs(te - 100 * box_r) <= 0.25
                    ok["cg_start"] = abs(cs - 100 * p["cube_goal_dist_m_pre"]) <= 0.15
                    ok["cg_end"] = abs(ce - 100 * r["cube_goal_dist_m_pre"]) <= 0.15

                    # Check verdict against d2 / legacy rules
                    verdict_switch_on = bool(e.get("verdict_contact_switch"))
                    if verdict_switch_on:
                        contact_strictly_before = any(
                            _round_touched(prev_round.get("contact", {}), prev_round.get("cube_disp_m", 0.0))
                            for prev_round in rs[:i - 1]
                        )
                        expected_metric = "cube_goal" if contact_strictly_before else "tip_cube"
                        delta = (ce - cs) if contact_strictly_before else (te - ts)
                        recorded_metric = r.get("verdict_metric")
                        ok["verdict_metric_match"] = (recorded_metric == expected_metric)
                    else:
                        delta = ce - cs
                        recorded_metric = r.get("verdict_metric")
                        ok["verdict_metric_match"] = (recorded_metric in ("cube_goal", None))

                    # Verdict progress / regress / flat
                    fb_lower = fb.lower()
                    if delta < -1.0 + 1e-4:
                        verdict_ok = ("progress" in fb_lower) and ("no significant" not in fb_lower)
                    elif delta > 1.0 - 1e-4:
                        verdict_ok = ("regression" in fb_lower)
                    else:
                        verdict_ok = ("no significant" in fb_lower)
                    ok["verdict_matches_delta"] = verdict_ok

                for k, v in ok.items():
                    R[f"fb_{k}_{'OK' if v else 'BAD'}"] += 1
                    if not v:
                        hard_failures.append(f"HARD: Feedback mismatch ep={ep_id} r={i+1} check={k}")
                        if len(fb_bad) < 6:
                            fb_bad.append((e.get("env_seed"), i + 1, k, fb.splitlines()))

            except Exception as ex:
                hard_failures.append(f"HARD: Feedback parsing error ep={ep_id} r={i+1}: {ex}")
                R["fb_parse_error"] += 1

        if ep_had_contact:
            contact_episodes += 1

    stats = {
        "episodes": len(eps),
        "rounds": nrounds,
        "outcomes": dict(outcomes),
        "contact_episodes": contact_episodes,
        "reach_raw": reach_raw,
        "reach_guarded": reach_guarded,
        "lowz": lowz,
        "zt": zt,
        "init_cg": init_cg,
        "min_cg": min_cg,
        "closest_tcp_cube": closest_tcp_cube,
        "img_same": img_same,
        "img_pairs": img_pairs,
        "R": dict(R),
        "fb_bad": fb_bad,
        "hard_failures": hard_failures,
        "setpoint_clamps_total": setpoint_clamps_total,
        "rounds_with_setpoint_clamps": rounds_with_setpoint_clamps,
        "setpoint_clamp_steps_max": max(setpoint_clamp_steps_list, default=0),
        "target_clamps_count": target_clamps_count,
        "ori_err_final_list": ori_err_final_list,
        "ori_err_max_last20_list": ori_err_max_last20_list,
        "ori_err_above_5deg": ori_err_above_5deg,
        "tau_flag_rounds": tau_flag_rounds,
        "tau_flag_steps_max": tau_flag_steps_max,
        "tau_warn_rounds": tau_warn_rounds,
        "tau_warn_steps_max": tau_warn_steps_max,
        "target_rel_x": target_rel_x,
        "target_rel_y": target_rel_y,
        "z_standby_count": z_standby_count,
        "z_contact_band_count": z_contact_band_count,
        "z_other_count": z_other_count,
        "box_quat_count": box_quat_count,
        "box_fallback_count": box_fallback_count,
        "d1_units_OK": R.get("d1_units_OK", 0),
        "d1_bounds_missing": R.get("d1_bounds_missing", 0),
        "has_frame_convention": any(e.get("frame_convention") for e in eps),
        "total_injected_lessons": total_injected_lessons,
        "leaked_lesson_count": leaked_lesson_count,
        "preamble_coord_redactions_total": preamble_coord_redactions_total,
        "preamble_coords_mode": eps[0].get("preamble_coords", "on") if eps else "on",
        "geometry_mode": eps[0].get("geometry", "pin4b") if eps else "pin4b",
        "settled_dists": settled_dists,
        "settled_angles": settled_angles,
        "settled_cubes_x": settled_cubes_x,
        "settled_cubes_y": settled_cubes_y,
    }
    from scripts.analysis.wp3a_rho_segments import analyze_rho_segments
    stats["rho_segments"] = analyze_rho_segments(eps)
    return len(hard_failures) == 0, stats


def print_report(stats: Dict[str, Any]) -> None:
    n_eps = stats["episodes"]
    n_rounds = stats["rounds"]
    print(f"episodes={n_eps} rounds={n_rounds} outcomes={stats['outcomes']}")
    print(f"[task] successes={stats['outcomes'].get('success', 0)}/{n_eps}; contact_episodes={stats['contact_episodes']}/{n_eps}")

    if stats["closest_tcp_cube"]:
        print(f"[task] closest TCP->cube cm: min={100*min(stats['closest_tcp_cube']):.1f} median={100*st.median(stats['closest_tcp_cube']):.1f}")
    else:
        print("[task] closest TCP->cube: N/A")

    if stats["init_cg"]:
        print(f"[task] initial cube->goal cm: min={100*min(stats['init_cg']):.1f} median={100*st.median(stats['init_cg']):.1f} max={100*max(stats['init_cg']):.1f}; success needs <= {100*SUCC_M:.0f} cm")
    else:
        print("[task] initial cube->goal: N/A")

    if stats["min_cg"]:
        print(f"[task] best cube->goal reached per episode cm: min={100*min(stats['min_cg']):.1f} median={100*st.median(stats['min_cg']):.1f}")
    else:
        print("[task] best cube->goal: N/A")

    # Target distributions
    if stats["target_rel_x"]:
        rx, ry = stats["target_rel_x"], stats["target_rel_y"]
        print(f"[distribution] target relative to cube (m): X range [{min(rx):.3f}, {max(rx):.3f}] median {st.median(rx):.3f}; Y range [{min(ry):.3f}, {max(ry):.3f}] median {st.median(ry):.3f}")
    else:
        print("[distribution] target relative to cube: N/A")

    print(f"[z] counts: standby_z={stats['z_standby_count']} (defined as z_int == init_tcp_z_int) contact_band={stats['z_contact_band_count']} (cube centre ± half-height mapped to z_int) other={stats['z_other_count']} | target z-int top: {stats['zt'].most_common(6)}")

    # d1 status
    if stats.get("d1_units_OK", 0) > 0:
        print(f"[d1] frame_convention verified: {stats['d1_units_OK']} episodes checked against meta workspace_bounds (OK)")
    elif stats.get("d1_bounds_missing", 0) > 0:
        print(f"[d1] frame_convention units check: N/A (workspace_bounds missing from meta in {stats['d1_bounds_missing']} episodes)")
    elif stats.get("has_frame_convention", False):
        print("[d1] frame_convention: failed or missing line")
    else:
        print("[d1] frame_convention: off")

    # Telemetry: Reach errors (raw vs guarded)
    rr = stats["reach_raw"]
    rg = stats["reach_guarded"]
    if rr:
        p95_raw = sorted(rr)[int(0.95 * len(rr))]
        p95_g = sorted(rg)[int(0.95 * len(rg))] if rg else 0.0
        print(f"[exec] reach_err_cm RAW: median={st.median(rr):.2f} p95={p95_raw:.2f} max={max(rr):.2f}")
        print(f"[exec] reach_err_cm GUARDED: median={st.median(rg):.2f} p95={p95_g:.2f} max={max(rg):.2f}")
    else:
        print("[exec] reach_err_cm: N/A")

    # Telemetry: Table guard setpoint clamps
    print(f"[guard] target_clamps={stats['target_clamps_count']}; setpoint_clamps: total={stats['setpoint_clamps_total']} in {stats['rounds_with_setpoint_clamps']} rounds (max={stats['setpoint_clamp_steps_max']})")

    # Telemetry: ORI
    of = stats["ori_err_final_list"]
    if of:
        print(f"[ori] final err deg: median={st.median(of):.2f} max={max(of):.2f}; rounds > 5 deg: {stats['ori_err_above_5deg']}/{len(of)}")
    else:
        print("[ori] final err deg: N/A (old run without ORI telemetry)")

    # Telemetry: Tau
    print(f"[tau] saturation (tau_flag_steps > 0): {stats['tau_flag_rounds']}/{n_rounds} rounds (max={stats['tau_flag_steps_max']}); warn: {stats['tau_warn_rounds']} rounds (max={stats['tau_warn_steps_max']})")

    # Box fallback report
    if stats["box_fallback_count"] > 0:
        print(f"[box] used quaternion distance in {stats['box_quat_count']} checks; fell back to axis-aligned approx in {stats['box_fallback_count']} checks")
    else:
        print(f"[box] used quaternion distance in {stats['box_quat_count']} checks; 0 fallbacks")

    # Feedback checks
    fb_stats = {k: v for k, v in sorted(stats["R"].items()) if k.startswith("fb_")}
    print("[feedback]", fb_stats)
    for b in stats["fb_bad"]:
        print("  BAD", b)

    # Geometry telemetry
    geom_mode = stats.get("geometry_mode", "pin4b")
    if stats.get("settled_dists"):
        sd = stats["settled_dists"]
        sa = stats["settled_angles"]
        cx = stats["settled_cubes_x"]
        cy = stats["settled_cubes_y"]
        print(f"[geometry] geometry={geom_mode}; settled goal-cube dist (m): min={min(sd):.3f} median={st.median(sd):.3f} max={max(sd):.3f}; settled angle (deg): min={min(sa):.1f} median={st.median(sa):.1f} max={max(sa):.1f}; cube X: [{min(cx):.3f}, {max(cx):.3f}] Y: [{min(cy):.3f}, {max(cy):.3f}]")

    # (e) Preamble and Leak rate telemetry
    p_coords = stats.get("preamble_coords_mode", "on")
    redactions = stats.get("preamble_coord_redactions_total", 0)
    tot_lessons = stats.get("total_injected_lessons", 0)
    leak_lessons = stats.get("leaked_lesson_count", 0)
    leak_rate_pct = (100.0 * leak_lessons / tot_lessons) if tot_lessons > 0 else 0.0
    print(f"[preamble] preamble_coords={p_coords}; coord_redactions={redactions}; lesson_leak_rate={leak_lessons}/{tot_lessons} ({leak_rate_pct:.1f}%)")

    # Segment rho / circular correlation / (c) pass verdict
    rho_res = stats.get("rho_segments")
    if rho_res and rho_res.get("segments"):
        for name, s in rho_res["segments"].items():
            if s.get("status") == "too_few":
                print(f"[segment:{name}] n={s['n']} (too few)")
                continue
            seeds = s["seeds"]
            out = [
                f"rho_X={s['rho_X']:+.3f} p_one_sided={s['p_X']:.4f} band95={s['band95_X']:+.3f}",
                f"rho_Y={s['rho_Y']:+.3f} p_one_sided={s['p_Y']:.4f} band95={s['band95_Y']:+.3f}",
                f"circ_corr={s['circ_corr']:+.3f} p_circ={s['p_circ']:.4f}",
            ]
            print(f"[segment:{name}] n={s['n']} seeds {seeds[0]}-{seeds[1]} | " + " | ".join(out) + f" | unique_R1_targets={s['unique_R1_targets']}")
        count_str = "yes" if rho_res["count_met"] else "no"
        sig_str = "yes" if rho_res["rho_sig"] else "no"
        verdict_str = "PASS" if rho_res["pass_step_c"] else "NOT PASSED"
        print(f"[(c) verdict] count>=5: {count_str}; rho_X significant: {sig_str} -> {verdict_str}")

    if stats["hard_failures"]:
        print(f"\n[FAIL] {len(stats['hard_failures'])} HARD checks failed:")
        for hf in stats["hard_failures"][:10]:
            print(" ", hf)
        if len(stats["hard_failures"]) > 10:
            print(f"  ... and {len(stats['hard_failures']) - 10} more")
    else:
        print("\n[PASS] All hard checks passed.")


def main() -> int:
    parser = argparse.ArgumentParser(description="WP1-3a Push Run Validator")
    parser.add_argument("--run", type=str, default="71134939", help="Run ID to validate")
    parser.add_argument("--data-dir", type=str, default="/home/control/AionGenos/data/collect_dumps",
                        help="Collect dumps root directory")
    args = parser.parse_args()

    run_dir = os.path.join(args.data_dir, args.run)
    files = sorted(glob.glob(os.path.join(run_dir, "*", "meta.json")))
    if not files:
        files = sorted(glob.glob(os.path.join(run_dir, "meta.json")))
    if not files:
        print(f"Error: No meta.json files found for run {args.run} under {args.data_dir}")
        return 1

    eps = []
    ep_dirs = []
    for f in files:
        with open(f, "r", encoding="utf-8") as fp:
            eps.append(json.load(fp))
        ep_dirs.append(os.path.dirname(f))

    success, stats = validate_episodes(eps, ep_dirs)
    print_report(stats)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
