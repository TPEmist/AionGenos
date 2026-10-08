"""D11 Amendment 15 (a)/(b), all four arms — paired statistics vs the locked predictions.

Reuses the Amendment-14 analysis code UNCHANGED (scripts/analysis/d11_mcnemar.py:
log-order pairing, outcome rule, init fingerprint, mcnemar, two_prop_z) and the
pin-8 boundary rule (a15_p1_autoreset_sensitivity.py) for the sensitivity SR.

Decision rules (A15 "Analysis rules", locked): paired on seed base 4500;
McNemar primary iff the pairing gate (A14 §14.1, eps 1e-4) passes, else
two-proportion z primary (A14 §14.2), the other as sensitivity. Two-sided.
A15 fixes no α → D11 §4 default α = 0.05 two-sided (disclosed). A15's
"within the paired MDE" is not given a number in the lock: the MDE is
computed here (two-sided α 0.05, power 0.8, n = 100, at the C_retrieval rate)
and disclosed as an operationalisation.

Usage: python3 scripts/analysis/a15_ab_stats.py [--json logs/a15_ab_stats.json]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import d11_mcnemar as A14  # noqa: E402

ALPHA = 0.05
A15_RUNS = {   # from logs/a15_manifest.jsonl
    "a_base_ret": {"run": "995f496c", "log": "logs/a15_a_base_ret_20261005_183416.log"},
    "b_action_only_ret": {"run": "9be74fc2", "log": "logs/a15_b_action_only_ret_20261005_232131.log"},
    "b_B_main_ret": {"run": "13c5c402", "log": "logs/a15_b_B_main_ret_20261006_180050.log"},
    "b_D_gist_ret": {"run": "fdb2a9b0", "log": "logs/a15_b_D_gist_ret_20261007_133730.log"},
}
OWN_BASELINE = {"b_action_only_ret": "A_action_only", "b_B_main_ret": "B_main",
                "b_D_gist_ret": "D_gist"}   # (b): rise vs the arm's own no-retrieval D11 run
BOUNDARY_IDX = 718   # pin 8 / a15_p1_autoreset_sensitivity.py (counter-derived, all runs)


def load_arm(cfg: dict) -> dict[int, dict]:
    out = {}
    for ep_idx, ep_id, seed in A14.parse_log_order(cfg["log"]):
        rp = A14.load_replay(cfg["run"], ep_id)
        if rp is None:
            continue
        succ = A14.outcome_success(rp)
        out[ep_idx] = {"seed": seed, "succ": succ, "fp": A14.init_fingerprint(rp),
                       "succ_sens": succ and (len(rp["trajectory"]) - 1) < BOUNDARY_IDX}
    return out


def mde_paired_two_prop(p: float, n: int, alpha: float = ALPHA, power: float = 0.8) -> float:
    """Normal-approx MDE (absolute) for a two-proportion difference at rate p."""
    za = 1.959963984540054 if alpha == 0.05 else None
    zb = 0.8416212335729143
    return (za + zb) * math.sqrt(2 * p * (1 - p) / n)


def contrast(x: dict, y: dict, key: str = "succ") -> dict:
    common = sorted(set(x) & set(y))
    sx = sum(x[k][key] for k in common)
    sy = sum(y[k][key] for k in common)
    b = sum(x[k][key] and not y[k][key] for k in common)
    c = sum(y[k][key] and not x[k][key] for k in common)
    mism = [k for k in common if x[k]["seed"] != y[k]["seed"]
            or not A14.allclose(x[k]["fp"], y[k]["fp"], A14.PAIR_EPS)]
    seed_mism = [k for k in common if x[k]["seed"] != y[k]["seed"]]
    z, pz = A14.two_prop_z(sx, len(common), sy, len(common))
    chi2, pm = A14.mcnemar(b, c)
    gate = not mism
    return {"n": len(common), "sr_x": sx, "sr_y": sy, "diff_pp": sx - sy,
            "discordant_b_x_only": b, "discordant_c_y_only": c,
            "pairing_gate_pass": gate, "fingerprint_mismatches": len(mism),
            "seed_mismatches": len(seed_mism),
            "primary": "mcnemar" if gate else "two_prop_z",
            "z": round(z, 3), "p_z": pz, "mcnemar_chi2": chi2, "p_mcnemar": pm,
            "p_primary": pm if gate else pz,
            "significant_primary": (pm if gate else pz) < ALPHA}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="logs/a15_ab_stats.json")
    a = ap.parse_args()
    cret = load_arm(A14.ARMS["C_retrieval"])
    mde = mde_paired_two_prop(sum(v["succ"] for v in cret.values()) / len(cret), len(cret))
    res = {"alpha": ALPHA, "mde_pp_at_C_retrieval_rate": round(mde * 100, 1)}
    for prot, cfg in A15_RUNS.items():
        arm = load_arm(cfg)
        r = {"vs_C_retrieval": contrast(arm, cret),
             "vs_C_retrieval_sensitivity_pin8": contrast(arm, cret, key="succ_sens")}
        if prot in OWN_BASELINE:
            own = load_arm(A14.ARMS[OWN_BASELINE[prot]])
            r["vs_own_D11_no_retrieval"] = contrast(arm, own)
            r["vs_own_D11_no_retrieval_sensitivity_pin8"] = contrast(arm, own, key="succ_sens")
        res[prot] = r
        for name, cc in r.items():
            print(f"[A15ab] {prot:18s} {name:42s} {cc['sr_x']}/{cc['n']} vs {cc['sr_y']}/{cc['n']} "
                  f"Δ={cc['diff_pp']:+d}pp gate={'PASS' if cc['pairing_gate_pass'] else 'FAIL'}"
                  f"({cc['fingerprint_mismatches']} fp, {cc['seed_mismatches']} seed mism) "
                  f"z={cc['z']:+.2f} p_z={cc['p_z']:.3g} McNemar b={cc['discordant_b_x_only']} "
                  f"c={cc['discordant_c_y_only']} p={cc['p_mcnemar']:.3g} → primary {cc['primary']} "
                  f"{'SIG' if cc['significant_primary'] else 'n.s.'}")
    print(f"[A15ab] MDE (two-sided α .05, power .8, n=100, p=C_retrieval) = {res['mde_pp_at_C_retrieval_rate']} pp")
    Path(a.json).write_text(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
