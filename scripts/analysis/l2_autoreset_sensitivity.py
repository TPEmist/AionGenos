"""L2 inherited 24 s auto-reset check + sensitivity (same rule as D11 A15 pin 8).

L2DualPushEnvCfg (aiongenos/tasks/L2_dual_push/dual_push_cfg.py) extends
AionGenosReachEnvBaseCfg → IsaacLab openarm bimanual ReachEnvCfg, which sets
episode_length_s = 24 (720 env steps); no AionGenos class overrides it. L2 eval
allows up to 40 rounds × 30 steps = 1200 steps, so crossing is possible.

Reuses, unchanged: the L2 confirmatory loader/statistics (l2_confirmatory.py:
log-order pairing, outcome_success, z, McNemar, Newcombe CI) and the pin-8
boundary derivation (a15_p1_autoreset_sensitivity.analyse_run: counter-derived
boundary + frozen-right-arm jump cross-check).

Usage: python3 scripts/analysis/l2_autoreset_sensitivity.py [--json logs/l2_autoreset_sensitivity.json]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from scripts.analysis import l2_confirmatory as L2  # noqa: E402
from scripts.analysis.a15_p1_autoreset_sensitivity import analyse_run  # noqa: E402

ALPHA = 0.010  # L2 report: T4-class α (l2_confirmatory_report.md §0)


def load(tag: str, cfg: dict) -> list:
    log = cfg["log"] or L2._resolve_log(tag)
    out = []
    for k, eid, _seed in L2.parse_log_order(log):
        rp = L2.load_replay(cfg["run"], eid)
        out.append((k, eid, rp, bool(rp is not None and L2.outcome_success(rp))))
    return out


def contrast(sa_list, sb_list):
    n = len(sa_list)
    sa, sb = sum(sa_list), sum(sb_list)
    b = sum(x and not y for x, y in zip(sa_list, sb_list))
    c = sum(y and not x for x, y in zip(sa_list, sb_list))
    z, pz = L2.two_prop_z(sa, n, sb, n)
    _, pm = L2.mcnemar(b, c)
    lo, hi = L2.newcombe_diff_ci(sa, n, sb, n)
    return {"sa": sa, "sb": sb, "n": n, "diff_pp": 100 * (sa - sb) / n, "z": round(z, 3),
            "p_z": pz, "mcnemar_b_c": [b, c], "p_mcnemar": pm,
            "newcombe95_pp": [round(100 * lo, 1), round(100 * hi, 1)],
            "significant_z_at_alpha": pz < ALPHA}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="logs/l2_autoreset_sensitivity.json")
    a = ap.parse_args()
    res, succ, sens = {}, {}, {}
    for tag, cfg in L2.PROTOCOLS.items():
        eps = load(tag, cfg)
        r = analyse_run(eps)
        lens = sorted(row["len"] for row in r["rows"])
        res[tag] = {k: v for k, v in r.items() if k != "rows"}
        res[tag]["traj_len_quartiles"] = [lens[len(lens) // 4], lens[len(lens) // 2], lens[3 * len(lens) // 4], lens[-1]]
        by_k = {row["k"]: row for row in r["rows"]}
        ks = sorted(by_k)
        succ[tag] = {k: by_k[k]["success"] for k in ks}
        sens[tag] = {k: by_k[k]["sens_success"] for k in ks}
        print(f"[L2ar] {tag:12s} as-run {r['as_run_success']}/{r['n']}  crossing {r['n_cross']}  "
              f"succ-after-boundary {r['n_success_after_b']}  sensitivity {r['sens_success']}/{r['n']}  "
              f"ambiguous {r['n_ambiguous']}  boundary idx {r['boundary_idx_set']}  len q1/med/q3/max {res[tag]['traj_len_quartiles']}")
    common = sorted(set(succ["C_retrieval"]) & set(succ["A_ctrl_rat"]))
    for name, src in (("as_run", succ), ("sensitivity_pin8", sens)):
        cc = contrast([src["C_retrieval"][k] for k in common], [src["A_ctrl_rat"][k] for k in common])
        res[f"C_retrieval_minus_A_ctrl_rat_{name}"] = cc
        print(f"[L2ar] C_ret − A_ctrl_rat ({name}): {cc['sa']} vs {cc['sb']} Δ={cc['diff_pp']:+.1f}pp "
              f"CI {cc['newcombe95_pp']} z={cc['z']:+.2f} p={cc['p_z']:.3g} McNemar {cc['mcnemar_b_c']} p={cc['p_mcnemar']:.3g} "
              f"→ {'SIG' if cc['significant_z_at_alpha'] else 'n.s.'} at α={ALPHA}")
    Path(a.json).write_text(json.dumps(res, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
