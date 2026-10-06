"""D11 Amendment 15 (c) — R1' slope probe (exploratory, pre-registered reading).

Per arm, per paired episode k: round-1 ΔX = parsed_left_pos[0] − trajectory[0]
.left_ee_pos[0] (int grid, = d11_exploratory.r1_dx) vs the REQUIRED correction
target_X − init_EE_X (int grid), target recovered by a15_recover_targets.py.
Reading (locked in A15): Spearman r + permutation band (p2_r_tracker); slope
"> 0" iff r is above the band's upper edge.

Recovery gate (op pin 5): per episode |‖EE − T‖_recovered − dist_red_t0| < 1 mm,
else the episode is excluded and counted. The D10 teacher pool is unseeded →
not computable (reported, no proxy).

Usage: python scripts/analysis/a15_slope_probe.py  (CPU, no sim)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from d11_exploratory import ARMS, arm_episodes, r1_dx  # noqa: E402
from p2_r_tracker import r_for_generation  # noqa: E402

TARGETS = Path("logs/a15_targets_seed4500.json")
GATE_TOL_M = float(__import__("os").environ.get("A15C_GATE_TOL_M", "0.001"))  # pinned 1mm; env override = disclosed post-hoc sensitivity
OUT = Path(f"logs/a15_slope_probe_gate{int(GATE_TOL_M*1000)}mm.json")


def main() -> int:
    rows = {r["ep_idx"]: r for r in json.loads(TARGETS.read_text())["rows"]}
    report = {}
    arms = dict(ARMS)
    # A15.1: (a)/(b) arms (pre-registered reading at the 15 mm gate), from the manifest
    man = Path("logs/a15_manifest.jsonl")
    if man.exists():
        for line in man.read_text().splitlines():
            m = json.loads(line)
            arms[f"A15_{m['protocol']}"] = {"run": m["run_id"], "log": m["log"]}
    for arm, cfg in arms.items():
        c, s, excl_gate, excl_parse, resid = [], [], 0, 0, []
        for ep_idx, _ep_id, rep in arm_episodes(cfg):
            t = rows.get(ep_idx)
            if t is None:
                excl_gate += 1
                continue
            d0 = rep["trajectory"][0]["distances"]["dist_red"]
            res = abs(t["dist_reset_m"] - d0)
            resid.append(res)
            if res >= GATE_TOL_M:
                excl_gate += 1
                continue
            dx = r1_dx(rep)
            if dx is None:
                excl_parse += 1
                continue
            c.append(dx)
            s.append(t["target_int"][0] - rep["trajectory"][0]["left_ee_pos"][0])
        g = r_for_generation(c, s)
        r, lo, hi, above, n = g["r"], g["band_lo"], g["band_hi"], g["above_band"], g["n"]
        resid.sort()
        report[arm] = {"r": r, "band": [lo, hi], "above_band": above, "n": n,
                       "excluded_recovery_gate": excl_gate, "excluded_no_r1": excl_parse,
                       "gate_residual_median_m": resid[len(resid) // 2] if resid else None,
                       "gate_residual_max_m": resid[-1] if resid else None}
        print(f"[A15c] {arm:14s} r={r:+.3f} band=[{lo:+.3f},{hi:+.3f}] above={above} n={n} "
              f"excl_gate={excl_gate} excl_noR1={excl_parse} "
              f"resid med/max={report[arm]['gate_residual_median_m']:.4f}/{report[arm]['gate_residual_max_m']:.4f} m")
    report["D10_teacher_pool"] = "not computable: D10 collects were unseeded, target not on disk (A15 op pin 5)"
    print(f"[A15c] D10 teacher pool: {report['D10_teacher_pool']}")
    OUT.write_text(json.dumps(report, indent=1))
    print(f"[A15c] wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
