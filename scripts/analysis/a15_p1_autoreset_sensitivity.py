"""A15 pin 8 — inherited 24 s auto-reset: per-episode boundary + sensitivity SR.

Read-only re-analysis of existing replays (no sim, no servers). Reuses the
Amendment-14 analysis code (scripts/analysis/d11_mcnemar.py, anchor 73e712b)
for D11 episode loading, outcome rule and every statistic.

Boundary derivation (documented rule):
  * IsaacLab ReachEnvCfg (openarm bimanual) sets episode_length_s=24,
    sim.dt=1/60, decimation=2 -> step_dt=1/30 -> max_episode_length = 720.
    Time-out fires inside env.step when episode_length_buf >= 720, and the
    env is reset inside that same step (manager_based_rl_env.py).
  * Replay t = common_step_counter * sim.dt  =>  counter c_i = round(t_i*60).
    common_step_counter is never reset (starts at 0 at env construction).
  * Episode reset counter c_reset = last recorded counter of the previous
    episode in log order (0 for the first episode). Recorded index i has
    episode_length_buf = c_i - c_reset, so the first auto-reset lands on the
    index where c_i - c_reset == 720 (counter boundary). With the single
    unrecorded warm-up step in IsaacLabEnvInterface.reset this is index 718.
  * Discontinuity cross-check at that index: the frozen right arm's EE
    integer position (static except at a reset re-sample) must jump by
    >= JUMP_MIN_GRID AND by > JUMP_RATIO x the largest step-to-step right-EE
    change anywhere else in the episode, and that index must also be the
    argmax of the right-EE step change. Left-EE jump and dist_red jump are
    reported too. Crossing episodes failing any check are "ambiguous".
  * Sensitivity success: outcome success AND success index (= last
    trajectory index; success is evaluated on the round's final step)
    < boundary index.

Usage:  python3 scripts/analysis/a15_p1_autoreset_sensitivity.py [--json OUT]
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from d11_mcnemar import (  # noqa: E402  (A14-anchored code, reused verbatim)
    ARMS, MEMORY_TEACHER_SR, load_replay, mcnemar, one_prop_z_floor,
    outcome_success, parse_log_order, two_prop_z,
)
from l2_confirmatory import newcombe_diff_ci  # noqa: E402

MAX_EPISODE_LENGTH = math.ceil(24.0 / ((1.0 / 60.0) * 2))  # 720
COUNTER_PER_T = 60  # t = counter * sim.dt, sim.dt = 1/60
JUMP_MIN_GRID = 5.0
JUMP_RATIO = 2.0
REPLAY_ROOT = Path("data/replays")
_EP_RE = re.compile(r"Episode (\d+)/\d+ \| [^|]+\| ([0-9a-f-]+)")

OTHER_RUNS = {  # unseeded: order from log only
    "D10_6b9ef134": ("6b9ef134", "logs/d10_l0a_left_teacher_mem_20260625_132350.log"),
    "D10_70028c23": ("70028c23", "logs/d10ext1_l0a_left_teacher_mem_20260629_113025.log"),
    "D10_18581c81": ("18581c81", "logs/d10ext2_l0a_left_teacher_mem_20260629_125805.log"),
    "D10_b74d9f38": ("b74d9f38", "logs/d10ext3_l0a_left_teacher_mem_20260630_111227.log"),
    "D10_0eb35c80": ("0eb35c80", "logs/d10ext3b_l0a_left_teacher_mem_20260630_125331.log"),
    "D10_54bcc2d4": ("54bcc2d4", "logs/d10ext4_l0a_left_teacher_mem_20260630_183612.log"),
    "D10_aa08bb4c": ("aa08bb4c", "logs/d10ext5b_l0a_left_teacher_mem_20260701_134934.log"),
    "D6b_fa7f4571": ("fa7f4571", "logs/d6b_l0a_left_no_memory_fix_20260702_125800.log"),
    "D6_67685984": ("67685984", "logs/d6_l0a_left_20260617_111817.log"),
}


def load_other(run: str, log: str) -> list[tuple[int, str, dict | None, bool]]:
    out = []
    for line in Path(log).read_text().splitlines():
        m = _EP_RE.search(line)
        if not m:
            continue
        k, eid = int(m.group(1)) - 1, m.group(2)
        rp, succ = None, False
        for sub in ("success", "failure", "parse_fail_quarantine"):
            p = REPLAY_ROOT / run / sub / f"{eid}.json"
            if p.exists():
                rp = json.loads(p.read_text())
                succ = sub == "success"
                break
        out.append((k, eid, rp, succ))
    return out


def load_d11(cfg: dict) -> list[tuple[int, str, dict | None, bool]]:
    out = []
    for k, eid, _seed in parse_log_order(cfg["log"]):
        rp = load_replay(cfg["run"], eid)
        out.append((k, eid, rp, bool(rp is not None and outcome_success(rp))))
    return out


def _jump(a: list, b: list) -> float:
    return math.dist(a, b)


def analyse_run(eps: list[tuple[int, str, dict | None, bool]]) -> dict:
    prev_last = 0  # counter at env construction
    rows = []
    for k, eid, rp, succ in eps:
        tr = (rp or {}).get("trajectory") or []
        if not tr:
            # parse-fail episode (no execute steps recorded): its reset +
            # warm-up step still advanced the counter by exactly 1, so the
            # next reset happens at prev_last + 1. Verified by the next
            # episode's offset coming out as the same value as everywhere.
            rows.append({"k": k, "id": eid, "len": 0, "success": succ,
                         "cross": False, "sens_success": succ})
            prev_last = None if prev_last is None else prev_last + 1
            continue
        c = [round(x["t"] * COUNTER_PER_T) for x in tr]
        offset = (c[0] - prev_last) if prev_last is not None else None
        prev_last = c[-1]
        # counter boundary: first i with c_i - c_reset == 720
        b_counter = (MAX_EPISODE_LENGTH - offset) if offset is not None else None
        b = b_counter if b_counter is not None else MAX_EPISODE_LENGTH - 2
        cross = len(tr) > b
        row = {"k": k, "id": eid, "len": len(tr), "success": succ,
               "warmup_offset": offset, "boundary_idx": b, "cross": cross}
        if cross:
            dR = [_jump(tr[i - 1]["right_ee_pos"], tr[i]["right_ee_pos"]) for i in range(1, len(tr))]
            dL = [_jump(tr[i - 1]["left_ee_pos"], tr[i]["left_ee_pos"]) for i in range(1, len(tr))]
            at_R, at_L = dR[b - 1], dL[b - 1]
            bg_R = max(v for i, v in enumerate(dR, start=1) if i != b)
            bg_L = max(v for i, v in enumerate(dL, start=1) if i != b)
            argmax_R = 1 + max(range(len(dR)), key=lambda j: dR[j])
            ddr = abs(tr[b]["distances"]["dist_red"] - tr[b - 1]["distances"]["dist_red"])
            confirmed = (at_R >= JUMP_MIN_GRID and at_R > JUMP_RATIO * bg_R
                         and argmax_R == b and b_counter is not None)
            row.update({"dR_at_b": at_R, "dR_bg_max": bg_R, "dL_at_b": at_L,
                        "dL_bg_max": bg_L, "argmax_dR": argmax_R,
                        "d_dist_red_at_b_cm": 100 * ddr, "confirmed": confirmed})
        succ_idx = len(tr) - 1
        row["success_after_b"] = bool(succ and cross and succ_idx >= b)
        row["sens_success"] = bool(succ and succ_idx < b)
        rows.append(row)
    n = len(rows)
    cross = [r for r in rows if r["cross"]]
    return {
        "n": n,
        "as_run_success": sum(r["success"] for r in rows),
        "n_cross": len(cross),
        "n_success_after_b": sum(r.get("success_after_b", False) for r in rows),
        "sens_success": sum(r["sens_success"] for r in rows),
        "n_ambiguous": sum(not r["confirmed"] for r in cross),
        "n_dist_red_jump_gt4cm": sum(r["d_dist_red_at_b_cm"] > 4 for r in cross),
        "boundary_idx_set": sorted({r["boundary_idx"] for r in rows if "boundary_idx" in r}),
        "warmup_offset_set": sorted({r["warmup_offset"] for r in rows if r.get("warmup_offset") is not None}),
        "n_offset_unknown": sum(1 for r in rows if r["len"] and r.get("warmup_offset") is None),
        "min_dR_at_b": min((r["dR_at_b"] for r in cross), default=None),
        "max_dR_bg": max((r["dR_bg_max"] for r in cross), default=None),
        "min_dL_at_b": min((r["dL_at_b"] for r in cross), default=None),
        "max_dL_bg": max((r["dL_bg_max"] for r in cross), default=None),
        "rows": rows,
    }


def contrast(name, a, b, alpha, succ):
    sa, sb = sum(succ[a]), sum(succ[b])
    n = len(succ[a])
    bc = sum(1 for x, y in zip(succ[a], succ[b]) if x and not y)
    cc = sum(1 for x, y in zip(succ[a], succ[b]) if y and not x)
    z, pz = two_prop_z(sa, n, sb, n)
    chi2, pm = mcnemar(bc, cc)
    lo, hi = newcombe_diff_ci(sa, n, sb, n)
    return {"name": name, "a": a, "b": b, "sa": sa, "sb": sb, "n": n,
            "diff_pp": 100 * (sa - sb) / n, "z": z, "p_z": pz,
            "disc_a_only": bc, "disc_b_only": cc, "p_mcnemar": pm,
            "newcombe95_pp": [100 * lo, 100 * hi], "alpha": alpha,
            "sig_z": pz < alpha, "sig_mcnemar": pm < alpha}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="workspace/a15_p1/autoreset_sensitivity.json")
    args = ap.parse_args()

    print(f"max_episode_length = {MAX_EPISODE_LENGTH}")
    results = {}
    for arm, cfg in ARMS.items():
        results[arm] = analyse_run(load_d11(cfg))
    for name, (run, log) in OTHER_RUNS.items():
        results[name] = analyse_run(load_other(run, log))

    hdr = f"{'run':15s} {'n':>3s} {'asrun':>5s} {'cross':>5s} {'succ>b':>6s} {'sens':>4s} {'ambig':>5s} {'dred>4cm':>8s} b_idx  offsets  minΔR@b maxΔR_bg minΔL@b maxΔL_bg"
    print(hdr)
    for name, r in results.items():
        f = lambda v: "-" if v is None else f"{v:.1f}"
        print(f"{name:15s} {r['n']:3d} {r['as_run_success']:5d} {r['n_cross']:5d} "
              f"{r['n_success_after_b']:6d} {r['sens_success']:4d} {r['n_ambiguous']:5d} "
              f"{r['n_dist_red_jump_gt4cm']:8d} {r['boundary_idx_set']} {r['warmup_offset_set']} "
              f"{f(r['min_dR_at_b'])} {f(r['max_dR_bg'])} {f(r['min_dL_at_b'])} {f(r['max_dL_bg'])}"
              + (f"  offset-unknown={r['n_offset_unknown']}" if r['n_offset_unknown'] else ""))

    # D11 contrasts, as-run vs sensitivity, ep_idx-aligned (A14 code path)
    out_contrasts = {}
    for label, key in (("as_run", "success"), ("sensitivity", "sens_success")):
        succ = {}
        for arm in ARMS:
            rows = sorted(results[arm]["rows"], key=lambda r: r["k"])
            assert [r["k"] for r in rows] == list(range(100)), arm
            succ[arm] = [bool(r[key]) for r in rows]
        cs = [
            contrast("T1", "B_main", "A_action_only", 0.020, succ),
            contrast("T1a", "B_main", "A_ctrl_rat", 0.020, succ),
            contrast("T4", "C_retrieval", "B_main", 0.010, succ),
            contrast("ID_weights_+34pp", "C_retrieval", "A_ctrl_rat", 0.05, succ),
        ]
        t1 = cs[0]
        floor = 0.7 * MEMORY_TEACHER_SR
        zf, pf = one_prop_z_floor(sum(succ["B_main"]), 100, floor)
        out_contrasts[label] = {
            "contrasts": cs,
            "T1_strong_pass": bool(t1["sig_z"] and t1["diff_pp"] >= 10),
            "T1_weak_pass": bool(t1["p_z"] < 0.010 and t1["diff_pp"] > 0),
            "T3": {"B_main_sr": sum(succ["B_main"]) / 100, "floor": floor,
                   "z": zf, "p": pf, "above_floor": pf < 0.010},
        }
        print(f"\n== {label} (primary test = z per A14 §14.2 gate-fail; McNemar = sensitivity per §14.5b)")
        for c in cs:
            print(f"  {c['name']:17s} {c['a']}−{c['b']}: {c['sa']}/{c['n']} vs {c['sb']}/{c['n']} "
                  f"Δ={c['diff_pp']:+.1f}pp z={c['z']:.3f} p_z={c['p_z']:.4g} "
                  f"Newcombe95=[{c['newcombe95_pp'][0]:+.1f},{c['newcombe95_pp'][1]:+.1f}] "
                  f"disc={c['disc_a_only']}/{c['disc_b_only']} p_McN={c['p_mcnemar']:.4g} "
                  f"α={c['alpha']} sig_z={c['sig_z']} sig_McN={c['sig_mcnemar']}")
        o = out_contrasts[label]
        print(f"  T1-strong {'PASS' if o['T1_strong_pass'] else 'FAIL'}  T1-weak {'PASS' if o['T1_weak_pass'] else 'FAIL'}"
              f"  T3 B_main={o['T3']['B_main_sr']:.2f} floor={floor:.3f} z={zf:.3f} p={pf:.4g} "
              f"{'ABOVE' if o['T3']['above_floor'] else 'BELOW/n.s.'}")

    outp = Path(args.json)
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(json.dumps({"runs": results, "contrasts": out_contrasts}, indent=1, default=str))
    print(f"\nwrote {outp}")


if __name__ == "__main__":
    main()
