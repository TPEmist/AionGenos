"""WP1-③a teacher-target distribution across observation rungs (PI 2026-10-07).

Direct test of "the scalar distances are the only calibration anchor": does the
teacher's left-TCP target leave the grid origin at rung-2, and does it TRACK
the cube? (rung-1/1b targets clustered at grid X = 0 / Z = 0.)

Per run, over every executed round (round_meta[].eef_target_int):
  - histograms of target X / Y / Z in grid units (bins of 10, [-100, 100]);
  - mass exactly at 0 per axis, and at (X = 0 and Z = 0);
  - cube in grid units (cube_b_pre → metric_to_int with the live WorkspaceBounds;
    self-checked against ee_start_b → ee_start_int, ±1 for the logged 0.1 mm rounding);
  - target − cube in grid units (X, Y), and Spearman(target, cube) per axis
    over round-1 targets (does the target follow where the cube is?).
Outputs: stdout table + JSON + one PNG (X and Z histograms, one row per run).
Pure CPU. Usage:
  python3 scripts/analysis/wp3a_target_hist.py rung1=e4aebf36 rung1b=30f15f0c rung2=<run>
"""
from __future__ import annotations

import argparse
import json
import statistics as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from aiongenos.config import WorkspaceBounds  # noqa: E402
from aiongenos.vlm.scalar_guard import metric_to_int  # noqa: E402
from p2_r_tracker import spearman  # noqa: E402

AXES = ("x", "y", "z")
BINS = list(range(-100, 101, 10))


def to_grid(p_b: list[float], wb: WorkspaceBounds) -> list[int]:
    return [metric_to_int(v, b)[0] for v, b in zip(p_b, (wb.x_bounds, wb.y_bounds, wb.z_bounds))]


def hist(vals: list[int]) -> list[int]:
    out = [0] * (len(BINS) - 1)
    for v in vals:
        i = min(max((v - BINS[0]) // 10, 0), len(out) - 1)
        out[i] += 1
    return out


def analyse(run_id: str, wb: WorkspaceBounds) -> dict:
    eps = json.loads(Path(f"logs/push_smoke_{run_id}.json").read_text())["episodes"]
    tgt, cube, r1_t, r1_c, grid_mism = [], [], [], [], 0
    for e in eps:
        for r in e.get("round_meta", []):
            t = r.get("eef_target_int")
            if not t:
                continue
            c = to_grid(r["cube_b_pre"], wb)
            # logged positions are rounded to 0.1 mm → ±1 grid unit at bin edges
            grid_mism += any(abs(g - h) > 1 for g, h in zip(to_grid(r["ee_start_b"], wb), r["ee_start_int"]))
            tgt.append(t)
            cube.append(c)
            if r["round"] == 1:
                r1_t.append(t)
                r1_c.append(c)
    n = len(tgt)
    res = {"run_id": run_id, "n_episodes": len(eps), "n_rounds": n,
           "grid_selfcheck_mismatches": grid_mism, "bins": BINS}
    for i, a in enumerate(AXES):
        vals = [t[i] for t in tgt]
        res[a] = {"hist": hist(vals), "at_zero": sum(v == 0 for v in vals) / n if n else None,
                  "median": st.median(vals) if vals else None,
                  "distinct": len(set(vals))}
    res["at_x0_and_z0"] = sum(t[0] == 0 and t[2] == 0 for t in tgt) / n if n else None
    for i, a in ((0, "x"), (1, "y")):
        d = [t[i] - c[i] for t, c in zip(tgt, cube)]
        res[f"target_minus_cube_{a}"] = {"median": st.median(d) if d else None,
                                         "median_abs": st.median(abs(v) for v in d) if d else None}
        tv, cv = [t[i] for t in r1_t], [c[i] for c in r1_c]
        res[f"spearman_r1_target_vs_cube_{a}"] = (spearman(tv, cv)
                                                 if len(set(tv)) > 1 and len(set(cv)) > 1 else None)
    return res


def plot(results: dict, out: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(len(results), 2, figsize=(9, 2.4 * len(results)), squeeze=False)
    centers = [b + 5 for b in BINS[:-1]]
    for row, (tag, r) in enumerate(results.items()):
        for col, a in enumerate(("x", "z")):
            ax = axs[row][col]
            ax.bar(centers, r[a]["hist"], width=9)
            ax.axvline(0, color="r", lw=0.8)
            ax.set_title(f"{tag} ({r['run_id']}) target {a.upper()}  n={r['n_rounds']}  "
                         f"at 0: {100 * (r[a]['at_zero'] or 0):.0f}%", fontsize=8)
            ax.set_xlim(-100, 100)
    fig.tight_layout()
    fig.savefig(out, dpi=110)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="+", help="tag=run_id")
    ap.add_argument("--json", default="logs/wp3a_target_hist.json")
    ap.add_argument("--png", default="logs/wp3a_target_hist.png")
    a = ap.parse_args()
    wb = WorkspaceBounds()
    results = {}
    for spec in a.runs:
        tag, run_id = spec.split("=", 1)
        r = results[tag] = analyse(run_id, wb)
        print(f"{tag:7s} {run_id} rounds {r['n_rounds']:4d}  at0 X {r['x']['at_zero']:.2f} "
              f"Y {r['y']['at_zero']:.2f} Z {r['z']['at_zero']:.2f}  X0&Z0 {r['at_x0_and_z0']:.2f}  "
              f"distinct X/Z {r['x']['distinct']}/{r['z']['distinct']}  "
              f"tgt−cube med |X| {r['target_minus_cube_x']['median_abs']} |Y| {r['target_minus_cube_y']['median_abs']}  "
              f"ρ(r1 tgt,cube) X {r['spearman_r1_target_vs_cube_x']} Y {r['spearman_r1_target_vs_cube_y']}  "
              f"selfcheck mism {r['grid_selfcheck_mismatches']}")
    Path(a.json).write_text(json.dumps(results, indent=1))
    plot(results, Path(a.png))
    print(f"→ {a.json}, {a.png}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
