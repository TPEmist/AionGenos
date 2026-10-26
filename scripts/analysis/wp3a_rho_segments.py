"""ρ_X / ρ_Y between round-1 target and cube position, split by first success.
Usage: python3 wp3a_rho_segments.py <run_id> [--perm 10000] [--seed 20261026] [--data-dir path]
Segments: all episodes; before the first success (seed order, exclusive); from the first success on (inclusive).
One-sided permutation test (H1: ρ > 0): p = (1 + #{ρ_perm ≥ ρ_obs}) / (1 + N); band95 = 95th percentile of ρ_perm.
Telemetry: circular correlation between round-1 target direction relative to cube and goal direction θ (R13).
"""
from __future__ import annotations

import argparse
import glob
import json
import math
from pathlib import Path
import random
import statistics as st
from typing import Any, Dict, List, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[2]


def rho(a: Sequence[float], b: Sequence[float]) -> float:
    if len(a) < 3 or len(a) != len(b):
        return float("nan")
    ma, mb = st.mean(a), st.mean(b)
    sa = sum((x - ma) ** 2 for x in a) ** 0.5
    sb = sum((y - mb) ** 2 for y in b) ** 0.5
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / (sa * sb) if sa and sb else float("nan")


def perm_test(t: Sequence[float], c: Sequence[float], n: int, rng: random.Random) -> Tuple[float, float, float]:
    obs = rho(t, c)
    if obs != obs or math.isnan(obs):
        return obs, float("nan"), float("nan")
    cc = list(c)
    null = []
    for _ in range(n):
        rng.shuffle(cc)
        null.append(rho(t, cc))
    null.sort()
    p = (1 + sum(v >= obs for v in null)) / (1 + n)
    band = null[int(0.95 * n) - 1] if null else float("nan")
    return obs, p, band


def circular_mean(angles: Sequence[float]) -> float:
    sa = sum(math.sin(a) for a in angles)
    ca = sum(math.cos(a) for a in angles)
    return math.atan2(sa, ca)


def circular_corr(a: Sequence[float], b: Sequence[float]) -> float:
    """Jammalamadaka & Sarma (1988) circular correlation coefficient between two angle arrays."""
    if len(a) < 3 or len(a) != len(b):
        return float("nan")
    ma = circular_mean(a)
    mb = circular_mean(b)
    sin_a = [math.sin(x - ma) for x in a]
    sin_b = [math.sin(y - mb) for y in b]
    num = sum(sa * sb for sa, sb in zip(sin_a, sin_b))
    den = (sum(sa ** 2 for sa in sin_a) * sum(sb ** 2 for sb in sin_b)) ** 0.5
    return num / den if den > 1e-12 else float("nan")


def perm_test_circular(a: Sequence[float], b: Sequence[float], n: int, rng: random.Random) -> Tuple[float, float, float]:
    obs = circular_corr(a, b)
    if obs != obs or math.isnan(obs):
        return obs, float("nan"), float("nan")
    bb = list(b)
    null = []
    for _ in range(n):
        rng.shuffle(bb)
        null.append(circular_corr(a, bb))
    null.sort()
    p = (1 + sum(v >= obs for v in null)) / (1 + n)
    band = null[int(0.95 * n) - 1] if null else float("nan")
    return obs, p, band


def extract_angles(s: List[Dict[str, Any]]) -> Tuple[List[float], List[float]]:
    """Extract round-1 target direction relative to cube (alpha) and goal direction (theta)."""
    alphas, thetas = [], []
    for e in s:
        rs = e.get("rounds", [])
        if not rs:
            continue
        r0 = rs[0]
        # target pos: tcp_target_b or eef_target_m or eef_target_int
        tgt = r0.get("tcp_target_b") or r0.get("eef_target_m")
        if tgt is not None:
            tx, ty = tgt[0], tgt[1]
        elif r0.get("eef_target_int") is not None:
            # integer grid proxy
            tx, ty = float(r0["eef_target_int"][0]), float(r0["eef_target_int"][1])
        else:
            continue

        c_pre = r0.get("cube_b_pre")
        if c_pre is None:
            continue
        cx, cy = c_pre[0], c_pre[1]

        # goal pos or theta
        gs = e.get("goal_sample")
        if gs is not None and "theta" in gs:
            th = float(gs["theta"])
        else:
            g_pre = r0.get("goal_b_pre") or e.get("goal_pose_b")
            if g_pre is None:
                continue
            th = math.atan2(g_pre[1] - cy, g_pre[0] - cx)

        al = math.atan2(ty - cy, tx - cx)
        alphas.append(al)
        thetas.append(th)
    return alphas, thetas


def analyze_rho_segments(
    eps: List[Dict[str, Any]],
    perm: int = 10000,
    seed: int = 20261026,
) -> Dict[str, Any]:
    """Run segment analysis over episodes: 'all', 'before_first_success', 'from_first_success'.
    Returns structured stats dictionary including (c) pass verdict data.
    """
    sorted_eps = sorted(eps, key=lambda e: e.get("env_seed", 0))
    first = next((i for i, e in enumerate(sorted_eps) if e.get("outcome") == "success"), None)
    segs = {
        "all": sorted_eps,
        "before_first_success": sorted_eps[:first] if first is not None else sorted_eps,
        "from_first_success": sorted_eps[first:] if first is not None else [],
    }

    n_success = sum(1 for e in sorted_eps if e.get("outcome") == "success")
    seg_results = {}

    for name, s in segs.items():
        valid_episodes = [e for e in s if e.get("rounds") and len(e["rounds"]) > 0]
        if len(valid_episodes) < 3:
            seg_results[name] = {"n": len(valid_episodes), "status": "too_few"}
            continue

        t1 = [e["rounds"][0].get("eef_target_int", [0, 0, 0]) for e in valid_episodes]
        c1 = [e["rounds"][0].get("cube_b_pre", [0, 0, 0]) for e in valid_episodes]

        rng_x = random.Random(seed)
        rng_y = random.Random(seed)
        r_x, p_x, band_x = perm_test([t[0] for t in t1], [c[0] for c in c1], perm, rng_x)
        r_y, p_y, band_y = perm_test([t[1] for t in t1], [c[1] for c in c1], perm, rng_y)

        # Circular correlation
        alphas, thetas = extract_angles(valid_episodes)
        if len(alphas) >= 3:
            rng_circ = random.Random(seed)
            r_circ, p_circ, band_circ = perm_test_circular(alphas, thetas, perm, rng_circ)
        else:
            r_circ, p_circ, band_circ = float("nan"), float("nan"), float("nan")

        uniq = len({tuple(t) for t in t1})
        seeds_range = (valid_episodes[0].get("env_seed"), valid_episodes[-1].get("env_seed"))

        seg_results[name] = {
            "n": len(valid_episodes),
            "seeds": seeds_range,
            "rho_X": r_x,
            "p_X": p_x,
            "band95_X": band_x,
            "rho_Y": r_y,
            "p_Y": p_y,
            "band95_Y": band_y,
            "circ_corr": r_circ,
            "p_circ": p_circ,
            "band95_circ": band_circ,
            "unique_R1_targets": uniq,
        }

    # (c) pass verdict: count >= 5 AND rho_X significant (p < 0.05 on 'all' segment)
    all_res = seg_results.get("all", {})
    p_x_all = all_res.get("p_X", float("nan"))
    count_met = (n_success >= 5)
    rho_sig = (not math.isnan(p_x_all) and p_x_all < 0.05)
    pass_step_c = count_met and rho_sig

    return {
        "n_episodes": len(sorted_eps),
        "n_success": n_success,
        "first_success_seed": sorted_eps[first].get("env_seed") if first is not None else None,
        "segments": seg_results,
        "count_met": count_met,
        "rho_sig": rho_sig,
        "pass_step_c": pass_step_c,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--perm", type=int, default=10000)
    ap.add_argument("--seed", type=int, default=20261026)
    ap.add_argument("--data-dir", type=str, default=None)
    a = ap.parse_args()

    candidates = []
    if a.data_dir:
        candidates.append(Path(a.data_dir))
    candidates.append(ROOT / "data/collect_dumps")
    candidates.append(Path("/home/control/AionGenos/data/collect_dumps"))

    files = []
    for base in candidates:
        pattern = str(base / f"{a.run}/*/meta.json")
        found = glob.glob(pattern)
        if found:
            files = sorted(found)
            break
        pattern_flat = str(base / f"{a.run}/meta.json")
        found = glob.glob(pattern_flat)
        if found:
            files = sorted(found)
            break

    if not files:
        print(f"Error: run {a.run} not found in {[str(p) for p in candidates]}")
        return

    eps = [json.load(open(f)) for f in files]
    res = analyze_rho_segments(eps, perm=a.perm, seed=a.seed)

    print(f"run={a.run} episodes={res['n_episodes']} first_success_seed={res['first_success_seed']} perm={a.perm} seed={a.seed}")
    for name, s in res["segments"].items():
        if s.get("status") == "too_few":
            print(f"[{name}] n={s['n']} (too few)")
            continue
        out = [
            f"rho_X={s['rho_X']:+.3f} p_one_sided={s['p_X']:.4f} band95={s['band95_X']:+.3f}",
            f"rho_Y={s['rho_Y']:+.3f} p_one_sided={s['p_Y']:.4f} band95={s['band95_Y']:+.3f}",
            f"circ_corr={s['circ_corr']:+.3f} p_circ={s['p_circ']:.4f}",
        ]
        seeds = s["seeds"]
        print(f"[{name}] n={s['n']} seeds {seeds[0]}-{seeds[1]} | " + " | ".join(out) + f" | unique_R1_targets={s['unique_R1_targets']}")

    count_str = "yes" if res["count_met"] else "no"
    sig_str = "yes" if res["rho_sig"] else "no"
    verdict_str = "PASS" if res["pass_step_c"] else "NOT PASSED"
    print(f"(c) pass verdict: count>=5: {count_str}; rho_X significant: {sig_str} -> {verdict_str}")


if __name__ == "__main__":
    main()
