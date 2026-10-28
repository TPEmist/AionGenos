"""Window analysis for WP1-3a memory time-axis pilot (long life).

Spec: docs/p2_prereg/wp3a_push_provenance.md (§ "PRE-REGISTERED before data:
memory time-axis pilot" + "Clarifications").
Authority: PI 2026-10-28.

Usage:
  python3 scripts/analysis/wp3a_life_windows.py <run_id> [--window 50] [--perm 10000] [--seed 20261026]
  python3 scripts/analysis/wp3a_life_windows.py --joint <run1> <run2> [--window 50] [--perm 10000] [--seed 20261026]
"""

from __future__ import annotations

import argparse
import glob
import itertools
import json
import math
from pathlib import Path
import random
import sys
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Reuse existing functions per spec — import, do not copy
from scripts.analysis.wp3a_rho_segments import (
    circular_corr,
    extract_angles,
    perm_test,
    perm_test_circular,
    rho,
)
from scripts.analysis.wp3a_pilot_report import confabulation_check


def calc_slope(x: Sequence[float], y: Sequence[float]) -> float:
    """Ordinary least squares slope of y against x."""
    n = len(x)
    if n < 2 or len(y) != n:
        return float("nan")
    mx = sum(x) / n
    my = sum(y) / n
    cov = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
    var = sum((xi - mx) ** 2 for xi in x)
    return cov / var if var > 1e-12 else 0.0


def perm_test_slope(
    x: Sequence[float],
    y: Sequence[float],
    n_perm: int = 10000,
    seed: int = 20261026,
) -> Tuple[float, float]:
    """Test significance of slope against window index.
    
    Exact enumeration of all k! permutations if k <= 8 (e.g. 720 for 6 windows).
    Monte Carlo permutation test if k > 8.
    Two-sided p = fraction of permutations where |slope_perm| >= |slope_obs| - 1e-12.
    """
    k = len(x)
    if k < 2 or len(y) != k:
        return float("nan"), float("nan")
    obs = calc_slope(x, y)
    if math.isnan(obs):
        return float("nan"), float("nan")

    # If observed slope is zero, every permutation yields identical absolute slope
    if abs(obs) < 1e-12:
        return 0.0, 1.0

    if k <= 8:
        # Exact enumeration of all k! permutations
        perms = itertools.permutations(y)
        total = math.factorial(k)
        count = sum(1 for p in perms if abs(calc_slope(x, p)) >= abs(obs) - 1e-12)
        return obs, count / total
    else:
        # Monte Carlo permutation test
        rng = random.Random(seed)
        count = 0
        yy = list(y)
        for _ in range(n_perm):
            rng.shuffle(yy)
            if abs(calc_slope(x, yy)) >= abs(obs) - 1e-12:
                count += 1
        return obs, (1 + count) / (1 + n_perm)


def compute_joint_verdict(v1: str, v2: str) -> Tuple[str, str]:
    """Joint verdict for two lives per pre-registration:
    - Climb claimed only if both lives show climb.
    - Degrade claimed only if both lives show degrade.
    - If only one shows climb or degrade -> 'not reproduced'.
    - If both show plateau -> 'plateau'.
    - If both show shortcut -> 'shortcut'.
    - If either is uninformative -> 'uninformative'.
    """
    if v1 == "uninformative" or v2 == "uninformative":
        return "uninformative", f"life1={v1}, life2={v2}; at least one life is uninformative"
    if v1 == "climb" and v2 == "climb":
        return "climb", "both lives show climb"
    if v1 == "degrade" and v2 == "degrade":
        return "degrade", "both lives show degrade"
    if v1 in ("climb", "degrade") or v2 in ("climb", "degrade"):
        return "not reproduced", f"claimed only if both lives show it (life1={v1}, life2={v2})"
    if v1 == v2:
        return v1, f"both lives show {v1}"
    return "not reproduced", f"lives differ (life1={v1}, life2={v2})"


def _normalize_episodes(eps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Ensure both rounds and round_meta point to the list of round dicts."""
    for e in eps:
        if not isinstance(e.get("rounds"), list) and isinstance(e.get("round_meta"), list):
            e["rounds"] = e["round_meta"]
        elif not isinstance(e.get("round_meta"), list) and isinstance(e.get("rounds"), list):
            e["round_meta"] = e["rounds"]
    return eps


def find_run_data(
    run_id: str,
    smoke_file: Optional[str] = None,
    data_dir: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Locate and load episodes for run_id."""
    if smoke_file and Path(smoke_file).exists():
        d = json.loads(Path(smoke_file).read_text())
        return _normalize_episodes(d.get("episodes", []))

    # Check logs/push_smoke_<run_id>.json
    candidates = [
        Path(f"logs/push_smoke_{run_id}.json"),
        ROOT / f"logs/push_smoke_{run_id}.json",
        Path(f"/home/control/AionGenos/logs/push_smoke_{run_id}.json"),
    ]
    for p in candidates:
        if p.exists():
            d = json.loads(p.read_text())
            return _normalize_episodes(d.get("episodes", []))

    # Check collect dumps
    dump_bases = []
    if data_dir:
        dump_bases.append(Path(data_dir))
    dump_bases.extend([
        ROOT / "data/collect_dumps",
        Path("/home/control/AionGenos/data/collect_dumps"),
    ])
    for base in dump_bases:
        pat = base / run_id / "*" / "meta.json"
        files = sorted(glob.glob(str(pat)))
        if not files:
            files = sorted(glob.glob(str(base / run_id / "meta.json")))
        if files:
            eps = [json.load(open(f)) for f in files]
            return _normalize_episodes(eps)

    # Check replays
    replay_bases = [
        ROOT / "data/replays",
        Path("/home/control/AionGenos/data/replays"),
    ]
    for base in replay_bases:
        pat = base / run_id / "*" / "meta.json"
        files = sorted(glob.glob(str(pat)))
        if files:
            eps = [json.load(open(f)) for f in files]
            return _normalize_episodes(eps)

    return []


def find_recap_lessons(
    run_id: str,
    recap_root: Optional[str] = None,
) -> Tuple[Dict[str, str], Set[str]]:
    """Locate and load recap lessons and set of episode IDs in recap buffer."""
    search_dirs = []
    if recap_root:
        p = Path(recap_root)
        if (p / run_id).is_dir():
            search_dirs.append(p / run_id)
        else:
            search_dirs.append(p)

    base_dirs = [
        Path("workspace"),
        ROOT / "workspace",
        Path("/home/control/AionGenos/workspace"),
    ]
    for b in base_dirs:
        if b.is_dir():
            for d in b.glob(f"recaps_push_*/{run_id}"):
                if d.is_dir():
                    search_dirs.append(d)
            for d in b.glob(f"recaps_push_{run_id}"):
                if d.is_dir():
                    search_dirs.append(d)

    lessons = {}
    ep_ids = set()
    for sdir in search_dirs:
        for f in sdir.glob("*.json"):
            if f.name == "INDEX.json":
                continue
            try:
                data = json.loads(f.read_text())
                ep_id = data.get("ep_id") or f.stem
                ep_ids.add(ep_id)
                lesson = data.get("text_lesson") or data.get("lesson") or ""
                if lesson:
                    lessons[ep_id] = lesson
            except Exception:
                pass
        if ep_ids:
            break
    return lessons, ep_ids


def analyze_life_windows(
    eps: List[Dict[str, Any]],
    window_size: int = 50,
    perm: int = 10000,
    seed: int = 20261026,
    lessons: Optional[Dict[str, str]] = None,
    recap_ep_ids: Optional[Set[str]] = None,
    run_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Analyze episodes grouped into sequential windows of window_size (in seed order)."""
    eps = _normalize_episodes(eps)
    if lessons is None:
        lessons = {}
    if recap_ep_ids is None:
        recap_ep_ids = set()

    # Sort episodes in seed order
    def _ep_seed(e: Dict[str, Any]) -> int:
        s = e.get("env_seed")
        if s is not None:
            return int(s)
        s = e.get("seed")
        if s is not None:
            return int(s)
        return 0

    sorted_eps = sorted(eps, key=_ep_seed)
    n_eps = len(sorted_eps)

    num_windows = n_eps // window_size
    if num_windows == 0 and n_eps > 0:
        num_windows = 1

    windows_data: List[Dict[str, Any]] = []

    for w_idx in range(num_windows):
        start_idx = w_idx * window_size
        end_idx = min(start_idx + window_size, n_eps) if num_windows == 1 else (w_idx + 1) * window_size
        w_eps = sorted_eps[start_idx:end_idx]

        # Seed range
        seeds = [e.get("env_seed") for e in w_eps if e.get("env_seed") is not None]
        if not seeds:
            seeds = [e.get("seed") for e in w_eps if e.get("seed") is not None]
        seed_min = min(seeds) if seeds else None
        seed_max = max(seeds) if seeds else None

        # Success rate
        n_succ = sum(1 for e in w_eps if e.get("outcome") == "success")
        sr = (n_succ / len(w_eps)) if w_eps else 0.0

        # Buffer size at window start (= number of recaps written before the window)
        earlier_eps = sorted_eps[:start_idx]
        buffer_size_start = sum(
            1 for e in earlier_eps
            if (e.get("ep_id") in recap_ep_ids) or e.get("has_recap") or e.get("recap_written")
        )

        # Retrieval hit rate (fraction of memory_hits with outcome success)
        all_hits = []
        for e in w_eps:
            all_hits.extend(e.get("memory_hits", []))
        n_hits = len(all_hits)
        n_hit_success = sum(1 for h in all_hits if h.get("outcome") == "success" or h.get("is_success") is True)
        retrieval_hit_rate = (n_hit_success / n_hits) if n_hits > 0 else None

        # Confabulation check (assertive count & rate vs cube motion)
        w_ep_ids = {e.get("ep_id") for e in w_eps if e.get("ep_id")}
        w_lessons = {eid: lessons[eid] for eid in w_ep_ids if eid in lessons}
        if w_lessons:
            c_res = confabulation_check(w_eps, w_lessons)
            confab_count = c_res["assertive_flagged"]
            confab_rate = c_res["assertive_rate"]
            confab_kw_count = c_res["keyword_flagged"]
            confab_kw_rate = c_res["keyword_rate"]
            confab_still = c_res["n_recaps_cube_never_moved"]
        else:
            confab_count = 0
            confab_rate = None
            confab_kw_count = 0
            confab_kw_rate = None
            confab_still = 0

        # Primary metric: circular correlation with one-sided permutation p
        alphas, thetas = extract_angles(w_eps)
        if len(alphas) < 5:
            is_valid = False
            nan_reason = f"fewer than 5 valid episodes ({len(alphas)})"
            circ_corr = float("nan")
            p_circ = float("nan")
            band_circ = float("nan")
        else:
            r_val = circular_corr(alphas, thetas)
            if math.isnan(r_val):
                is_valid = False
                nan_reason = "zero variance / circular correlation undefined"
                circ_corr = float("nan")
                p_circ = float("nan")
                band_circ = float("nan")
            else:
                is_valid = True
                nan_reason = None
                rng_circ = random.Random(seed)
                circ_corr, p_circ, band_circ = perm_test_circular(alphas, thetas, perm, rng_circ)

        # rho_X, rho_Y (secondary) & unique round-1 targets
        valid_episodes = [e for e in w_eps if e.get("rounds") and len(e["rounds"]) > 0]
        if len(valid_episodes) >= 3:
            t1 = []
            for e in valid_episodes:
                r0 = e["rounds"][0]
                tgt = r0.get("eef_target_int") or r0.get("tcp_target_b") or r0.get("eef_target_m") or [0, 0, 0]
                t1.append(tgt)
            c1 = [e["rounds"][0].get("cube_b_pre", [0, 0, 0]) for e in valid_episodes]
            rng_x = random.Random(seed)
            rng_y = random.Random(seed)
            r_x, p_x, band_x = perm_test([t[0] for t in t1], [c[0] for c in c1], perm, rng_x)
            r_y, p_y, band_y = perm_test([t[1] for t in t1], [c[1] for c in c1], perm, rng_y)
            uniq_r1 = len({tuple(t) for t in t1})
        else:
            r_x, p_x, band_x = float("nan"), float("nan"), float("nan")
            r_y, p_y, band_y = float("nan"), float("nan"), float("nan")
            uniq_r1 = len(valid_episodes)

        windows_data.append({
            "window": w_idx + 1,
            "seed_min": seed_min,
            "seed_max": seed_max,
            "n_episodes": len(w_eps),
            "n_success": n_succ,
            "sr": sr,
            "circ_corr": None if math.isnan(circ_corr) else circ_corr,
            "p_circ": None if math.isnan(p_circ) else p_circ,
            "band95_circ": None if math.isnan(band_circ) else band_circ,
            "rho_X": None if math.isnan(r_x) else r_x,
            "p_X": None if math.isnan(p_x) else p_x,
            "band95_X": None if math.isnan(band_x) else band_x,
            "rho_Y": None if math.isnan(r_y) else r_y,
            "p_Y": None if math.isnan(p_y) else p_y,
            "band95_Y": None if math.isnan(band_y) else band_y,
            "buffer_size_start": buffer_size_start,
            "retrieval_hit_rate": retrieval_hit_rate,
            "n_retrieval_hits": n_hits,
            "n_retrieval_success": n_hit_success,
            "confab_count": confab_count,
            "confab_rate": confab_rate,
            "confab_keyword_count": confab_kw_count,
            "confab_keyword_rate": confab_kw_rate,
            "confab_still_episodes": confab_still,
            "unique_r1_targets": uniq_r1,
            "is_valid": is_valid,
            "nan_reason": nan_reason,
        })

    # Trend and verdict rules
    valid_windows = [w for w in windows_data if w["is_valid"]]
    excluded_windows = [w["window"] for w in windows_data if not w["is_valid"]]
    n_excluded = len(excluded_windows)

    if n_excluded >= 2:
        verdict = "uninformative"
        verdict_reason = f"≥ 2 windows excluded due to NaN ({n_excluded} excluded: windows {excluded_windows})"
        slope_prim, p_slope_prim = None, None
        slope_sr, p_slope_sr = None, None
        win6_p = None
    elif len(valid_windows) < 2:
        verdict = "uninformative"
        verdict_reason = f"insufficient valid windows ({len(valid_windows)} valid, minimum 2 required for trend)"
        slope_prim, p_slope_prim = None, None
        slope_sr, p_slope_sr = None, None
        win6_p = None
    else:
        x_indices = [float(w["window"]) for w in valid_windows]
        y_prim = [float(w["circ_corr"]) for w in valid_windows]
        y_sr = [float(w["sr"]) for w in valid_windows]

        slope_prim, p_slope_prim = perm_test_slope(x_indices, y_prim, n_perm=perm, seed=seed)
        slope_sr, p_slope_sr = perm_test_slope(x_indices, y_sr, n_perm=perm, seed=seed)

        # Window 6 check
        w6 = next((w for w in valid_windows if w["window"] == 6), None)
        if w6 is not None and w6.get("p_circ") is not None:
            win6_p = float(w6["p_circ"])
            win6_sig = (win6_p < 0.05)
        else:
            win6_p = None
            win6_sig = False

        is_climb = (slope_prim > 0 and p_slope_prim < 0.05 and win6_sig)
        is_shortcut = (slope_sr > 0 and p_slope_sr < 0.05 and (slope_prim <= 0 or p_slope_prim >= 0.05))
        is_degrade = (slope_prim < 0 and p_slope_prim < 0.05 and not is_shortcut)

        if is_climb:
            verdict = "climb"
            verdict_reason = (
                f"primary slope > 0 ({slope_prim:+.4f}, p={p_slope_prim:.4f} < 0.05) "
                f"and window 6 p < 0.05 (p={win6_p:.4f})"
            )
        elif is_shortcut:
            verdict = "shortcut"
            verdict_reason = (
                f"SR slope > 0 ({slope_sr:+.4f}, p={p_slope_sr:.4f} < 0.05) "
                f"while primary slope is not significant (slope={slope_prim:+.4f}, p={p_slope_prim:.4f})"
            )
        elif is_degrade:
            verdict = "degrade"
            verdict_reason = f"primary slope < 0 ({slope_prim:+.4f}, p={p_slope_prim:.4f} < 0.05)"
        else:
            verdict = "plateau"
            verdict_reason = (
                f"neither climb, degrade, nor shortcut; primary slope={slope_prim:+.4f} (p={p_slope_prim:.4f})"
            )

    return {
        "run_id": run_id,
        "window_size": window_size,
        "n_episodes": n_eps,
        "n_windows": len(windows_data),
        "perm": perm,
        "seed": seed,
        "windows": windows_data,
        "excluded_windows": excluded_windows,
        "n_excluded": n_excluded,
        "trend": {
            "slope_primary": slope_prim,
            "p_slope_primary": p_slope_prim,
            "slope_sr": slope_sr,
            "p_slope_sr": p_slope_sr,
            "win6_p_circ": win6_p,
            "n_valid_windows": len(valid_windows),
        },
        "verdict": verdict,
        "verdict_reason": verdict_reason,
    }


def format_window_table(res: Dict[str, Any]) -> str:
    """Format analysis result into a clean text table for stdout."""
    lines = []
    run_hdr = f"run={res.get('run_id', 'unknown')}"
    lines.append("=" * 120)
    lines.append(
        f"WP1-3a Life Window Analysis: {run_hdr} (episodes={res['n_episodes']}, "
        f"window_size={res['window_size']}, perm={res['perm']}, seed={res['seed']})"
    )
    lines.append("=" * 120)
    hdr = (
        f"{'Win':<4} {'Seeds':<11} {'SR (k/N)':<14} {'circ_corr (p)':<20} "
        f"{'rho_X (p)':<19} {'rho_Y (p)':<19} {'BufStart':<9} {'RetrHitRate':<12} "
        f"{'Confab (cnt, rate)':<20} {'UniqR1':<7}"
    )
    lines.append(hdr)
    lines.append("-" * 120)

    for w in res["windows"]:
        win_idx = w["window"]
        s_min = w["seed_min"] if w["seed_min"] is not None else "?"
        s_max = w["seed_max"] if w["seed_max"] is not None else "?"
        seeds_str = f"{s_min}-{s_max}"
        sr_str = f"{w['sr']:.3f} ({w['n_success']}/{w['n_episodes']})"

        if w["circ_corr"] is not None and w["p_circ"] is not None:
            circ_str = f"{w['circ_corr']:+.3f} (p={w['p_circ']:.4f})"
        else:
            circ_str = "NaN (excluded)"

        if w["rho_X"] is not None and w["p_X"] is not None:
            rx_str = f"{w['rho_X']:+.3f} (p={w['p_X']:.4f})"
        else:
            rx_str = "NaN"

        if w["rho_Y"] is not None and w["p_Y"] is not None:
            ry_str = f"{w['rho_Y']:+.3f} (p={w['p_Y']:.4f})"
        else:
            ry_str = "NaN"

        buf_str = str(w["buffer_size_start"])
        if w["retrieval_hit_rate"] is not None:
            rhr_str = f"{w['retrieval_hit_rate']:.3f} ({w['n_retrieval_success']}/{w['n_retrieval_hits']})"
        else:
            rhr_str = "N/A"

        if w["confab_rate"] is not None:
            cfb_str = f"{w['confab_count']}/{w['confab_still_episodes']} ({w['confab_rate']:.3f})"
        else:
            cfb_str = "N/A"

        u_str = str(w["unique_r1_targets"])

        row = (
            f"{win_idx:<4} {seeds_str:<11} {sr_str:<14} {circ_str:<20} "
            f"{rx_str:<19} {ry_str:<19} {buf_str:<9} {rhr_str:<12} "
            f"{cfb_str:<20} {u_str:<7}"
        )
        lines.append(row)

    lines.append("-" * 120)
    t = res["trend"]
    lines.append("Trend:")
    lines.append(f"  Valid windows: {t['n_valid_windows']} / {res['n_windows']} (excluded: {res['n_excluded']})")
    if t["slope_primary"] is not None:
        lines.append(f"  Primary slope: {t['slope_primary']:+.4f}, exact 2-sided p = {t['p_slope_primary']:.4f}")
    else:
        lines.append("  Primary slope: N/A, p = N/A")

    if t["slope_sr"] is not None:
        lines.append(f"  SR slope:      {t['slope_sr']:+.4f}, exact 2-sided p = {t['p_slope_sr']:.4f}")
    else:
        lines.append("  SR slope:      N/A, p = N/A")

    if t["win6_p_circ"] is not None:
        lines.append(f"  Window 6 within-window p: {t['win6_p_circ']:.4f}")
    else:
        lines.append("  Window 6 within-window p: N/A")

    lines.append(f"Verdict: {res['verdict']} ({res['verdict_reason']})")
    lines.append("=" * 120)
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="WP1-3a life window analysis")
    parser.add_argument("run", nargs="*", default=[], help="Run ID(s) to analyze")
    parser.add_argument("--window", type=int, default=50, help="Window size (episodes)")
    parser.add_argument("--perm", type=int, default=10000, help="Permutation count")
    parser.add_argument("--seed", type=int, default=20261026, help="Random seed")
    parser.add_argument(
        "--joint",
        nargs=2,
        metavar=("RUN1", "RUN2"),
        default=None,
        help="Evaluate two lives jointly",
    )
    parser.add_argument("--data-dir", type=str, default=None, help="Root directory for collect dumps")
    parser.add_argument("--smoke-file", type=str, default=None, help="Explicit push_smoke_<run>.json path")
    parser.add_argument("--recap-root", type=str, default=None, help="Recap buffer root")
    args = parser.parse_args()

    joint_mode = False
    run_list: List[str] = []

    if args.joint:
        joint_mode = True
        run_list = [args.joint[0], args.joint[1]]
    elif len(args.run) >= 2:
        joint_mode = True
        run_list = [args.run[0], args.run[1]]
    elif len(args.run) == 1:
        run_list = [args.run[0]]
    else:
        print("Error: Specify at least one run_id or use --joint run1 run2")
        return 1

    results = []
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True, parents=True)

    for rid in run_list:
        eps = find_run_data(rid, smoke_file=args.smoke_file, data_dir=args.data_dir)
        if not eps:
            print(f"Error: No episode data found for run '{rid}'")
            return 1

        lessons, recap_ep_ids = find_recap_lessons(rid, recap_root=args.recap_root)
        res = analyze_life_windows(
            eps,
            window_size=args.window,
            perm=args.perm,
            seed=args.seed,
            lessons=lessons,
            recap_ep_ids=recap_ep_ids,
            run_id=rid,
        )
        results.append(res)

        table_str = format_window_table(res)
        print(table_str)

        out_path = logs_dir / f"life_windows_{rid}.json"
        out_path.write_text(json.dumps(res, indent=2))
        print(f"Wrote {out_path}")

    if joint_mode and len(results) == 2:
        v1 = results[0]["verdict"]
        v2 = results[1]["verdict"]
        j_verdict, j_reason = compute_joint_verdict(v1, v2)
        joint_info = {
            "run1_id": run_list[0],
            "run2_id": run_list[1],
            "run1_verdict": v1,
            "run2_verdict": v2,
            "joint_verdict": j_verdict,
            "joint_reason": j_reason,
        }
        print("\n" + "=" * 120)
        print(f"Joint Verdict: {j_verdict} ({j_reason})")
        print(f"  Life 1 ({run_list[0]}): {v1}")
        print(f"  Life 2 ({run_list[1]}): {v2}")
        print("=" * 120 + "\n")

        joint_path = logs_dir / f"life_windows_joint_{run_list[0]}_{run_list[1]}.json"
        joint_path.write_text(json.dumps(joint_info, indent=2))
        print(f"Wrote {joint_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
