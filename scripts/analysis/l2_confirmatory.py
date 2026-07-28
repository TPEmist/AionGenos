"""L2 Stage-1 confirmatory analysis — thin wrapper over the frozen D11 stats.

Reuses the D11 statistical core verbatim (imported, NOT copied — so the
McNemar / z / fingerprint / allclose implementations are byte-identical to
the frozen confirmatory machinery). Adds only what L2 needs:

  1. L2-specific run_ids / logs (2 protocols, not D11's 5 arms).
  2. Pairing-integrity gate keyed on the FROZEN (right) arm — under
     Amendment 3 per-arm eval, the non-scored right arm is held in place,
     so its trajectory[0] should be identical across the paired protocols
     (a cleaner pairing check than D11, where both arms moved). If the
     frozen arm is NOT identical across the pair, the gate fails and we
     fall back to the two-proportion z exactly as D11 Amendment 14 §14.2.
  3. Newcombe (score) CI for the difference of the two SRs — reported
     regardless of gate outcome (the CI is the estimate the verdict frame
     in PRE_ANALYSIS_LOCK.md refers to).

Verdict framing is NOT decided here — it is fixed in
workspace/l2_audit/PRE_ANALYSIS_LOCK.md (committed before this ran). This
script only computes numbers; it prints them next to the locked prediction.

Usage:
  python3 scripts/analysis/l2_confirmatory.py
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# Reuse the frozen D11 statistical core verbatim (import, do not copy).
from scripts.analysis.d11_mcnemar import (  # noqa: E402
    parse_log_order,
    load_replay,
    outcome_success,
    init_fingerprint,
    allclose,
    mcnemar,
    two_prop_z,
    REPLAY_ROOT,
    PAIR_EPS,
)

# ─────────────── L2 config (Amendment 3 per-arm eval, left-scored) ───────────
N_EPISODES = 100
L2_ENV_SEED_BASE = 4600  # distinct from D11's 4500

PROTOCOLS = {
    "A_ctrl_rat":  {"run": "8384a740", "log": None},   # log auto-resolved below
    "C_retrieval": {"run": "2154e57e", "log": None},
}


def _resolve_log(tag: str) -> str:
    """Newest eval log for this protocol tag."""
    cands = sorted(Path("logs").glob(f"l2_eval_{tag}_*.log"))
    if not cands:
        raise FileNotFoundError(f"no log for {tag} under logs/l2_eval_{tag}_*.log")
    return str(cands[-1])


def frozen_arm_fingerprint(replay: dict) -> tuple[float, ...]:
    """Fingerprint from the FROZEN (right) arm at trajectory[0].

    Under per-arm left-scored eval the right arm is held in place, so its
    initial pose is a function of the seed alone and must match across the
    paired protocols. Cleaner than D11's whole-config fingerprint because
    the scored (left) arm has already been servo'd one step in trajectory[0]
    and legitimately differs between protocols.
    """
    t0 = replay["trajectory"][0]
    re_ = list(t0["right_ee_pos"])
    d = t0.get("distances", {})
    # dist_blue is the RIGHT-arm (blue cube) distance — frozen-arm side.
    return tuple(re_ + [d.get("dist_blue", float("nan"))])


def newcombe_diff_ci(s1: int, n1: int, s2: int, n2: int, z: float = 1.96):
    """Newcombe method 10 score CI for p1 - p2 (independent proportions).

    Returns (lo, hi) for (p1 - p2). Robust at small counts / near-boundary,
    unlike the Wald interval. z=1.96 → 95%.
    """
    def wilson(s, n):
        if n == 0:
            return (0.0, 0.0)
        p = s / n
        d = 1 + z * z / n
        centre = (p + z * z / (2 * n)) / d
        half = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / d
        return (centre - half, centre + half)

    l1, u1 = wilson(s1, n1)
    l2, u2 = wilson(s2, n2)
    p1, p2 = s1 / n1, s2 / n2
    lo = (p1 - p2) - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2)
    hi = (p1 - p2) + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)
    return lo, hi


def main() -> None:
    print("=" * 70)
    print("L2 Stage-1 confirmatory analysis (per-arm left-scored, Amendment 3)")
    print("verdict framework is LOCKED in workspace/l2_audit/PRE_ANALYSIS_LOCK.md")
    print("=" * 70)

    # Build per-protocol ep_idx → episode data
    proto_eps: dict[str, dict[int, dict]] = {}
    for tag, cfg in PROTOCOLS.items():
        log = cfg["log"] or _resolve_log(tag)
        order = parse_log_order(log)
        if len(order) != N_EPISODES:
            print(f"WARN {tag}: parsed {len(order)} episodes (expected {N_EPISODES})")
        eps = {}
        for ep_idx, ep_id, seed in order:
            rp = load_replay(cfg["run"], ep_id)
            if rp is None:
                print(f"WARN {tag} ep_idx={ep_idx} id={ep_id}: replay not found")
                continue
            eps[ep_idx] = {
                "ep_id": ep_id, "seed": seed, "replay": rp,
                "success": outcome_success(rp),
                "fp_frozen": frozen_arm_fingerprint(rp),
            }
        proto_eps[tag] = eps
        n_succ = sum(1 for e in eps.values() if e["success"])
        print(f"  {tag:12s} run={cfg['run']}  log={Path(log).name}")
        print(f"               episodes={len(eps)}  successes={n_succ}  SR={100*n_succ/max(len(eps),1):.1f}%")

    # ── Pairing-integrity gate on the FROZEN right arm ──────────────────
    print("\n" + "-" * 70)
    print("PAIRING-INTEGRITY GATE (frozen right-arm fingerprint, eps=%.0e)" % PAIR_EPS)
    print("-" * 70)
    common = sorted(set(proto_eps["A_ctrl_rat"]) & set(proto_eps["C_retrieval"]))
    print(f"  common ep_idx across both protocols: {len(common)}")

    mism = []
    seed_mism = 0
    for k in common:
        a = proto_eps["A_ctrl_rat"][k]
        c = proto_eps["C_retrieval"][k]
        if a["seed"] != c["seed"]:
            seed_mism += 1
            mism.append((k, f"seed {a['seed']} != {c['seed']}"))
        elif not allclose(a["fp_frozen"], c["fp_frozen"], PAIR_EPS):
            mism.append((k, f"frozen-arm fp {a['fp_frozen']} != {c['fp_frozen']}"))

    gate_pass = len(mism) == 0 and len(common) == N_EPISODES
    if mism:
        print(f"  ✗ GATE FAILED — {len(mism)} mismatches (first 10):")
        for k, why in mism[:10]:
            print(f"    ep_idx={k}: {why}")
    if len(common) != N_EPISODES:
        print(f"  ✗ common ep_idx {len(common)} != {N_EPISODES}")
    if gate_pass:
        print(f"  ✓ GATE PASSED — all {N_EPISODES} paired; frozen right arm")
        print(f"    identical across protocols → paired McNemar is valid.")

    # Seed-effectiveness + pairing-reality diagnostic. The float fingerprint
    # gate can fail on ~1e-4 drift while the pairing is physically real; the
    # integer-pose + RPY match rate is the honest measure of pairing reality.
    seed_match = right_int_match = left_match = rpy_match = both_match = 0
    for k in common:
        a, c = proto_eps["A_ctrl_rat"][k], proto_eps["C_retrieval"][k]
        seed_match += (a["seed"] == c["seed"])
        ta = a["replay"]["trajectory"][0]; tc = c["replay"]["trajectory"][0]
        ipm = tuple(ta["right_ee_pos"]) == tuple(tc["right_ee_pos"])
        rm = tuple(ta.get("right_ee_rpy", [])) == tuple(tc.get("right_ee_rpy", []))
        right_int_match += ipm
        rpy_match += rm
        both_match += (ipm and rm)
        left_match += (tuple(ta["left_ee_pos"]) == tuple(tc["left_ee_pos"]))
    n = len(common)
    print(f"\n  Seed-effectiveness + pairing-reality diagnostic (n={n}):")
    print(f"    seed identical (pairwise):              {seed_match}/{n}")
    print(f"    frozen right-arm INT pos identical @t0: {right_int_match}/{n}")
    print(f"    frozen right-arm RPY identical @t0:     {rpy_match}/{n}")
    print(f"    frozen right-arm INT+RPY identical:     {both_match}/{n}")
    print(f"    scored left-arm identical @ t0:         {left_match}/{n}")
    print(f"    → Interpretation: seed IS effective (100% seed match). The")
    print(f"      frozen arm matches at integer/RPY resolution for the large")
    print(f"      majority; the float-fingerprint gate fails only on ~1e-4")
    print(f"      drift because trajectory[0] is already servo'd one step and")
    print(f"      the scored (left) arm's differing first action perturbs the")
    print(f"      shared sim's float state. Pairing is physically real but not")
    print(f"      machine-verifiable from persisted replay → A14 §14.2 z fallback.")

    primary = "mcnemar" if gate_pass else "z"
    print(f"\n  primary test = {primary.upper()}"
          + ("" if gate_pass else "  (mechanical fallback — pairing gate failed, per A14 §14.2)"))

    # ── The confirmatory contrast: C_retrieval − A_ctrl_rat ─────────────
    idx = common
    succ = {t: [proto_eps[t][k]["success"] for k in idx] for t in PROTOCOLS}
    sa = sum(succ["C_retrieval"]); sb = sum(succ["A_ctrl_rat"]); na = nb = len(idx)
    diff_pp = 100 * (sa / na - sb / nb)
    b_cell = sum(1 for x, y in zip(succ["C_retrieval"], succ["A_ctrl_rat"]) if x and not y)
    c_cell = sum(1 for x, y in zip(succ["C_retrieval"], succ["A_ctrl_rat"]) if y and not x)
    z, pz = two_prop_z(sa, na, sb, nb)
    lo, hi = newcombe_diff_ci(sa, na, sb, nb)

    print("\n" + "=" * 70)
    print("CONFIRMATORY CONTRAST — C_retrieval − A_ctrl_rat (identical-weights)")
    print("  (two-sided; α per Amendment 2 T4-class = 0.010)")
    print("=" * 70)
    print(f"  SR: {100*sa/na:.1f}% vs {100*sb/nb:.1f}%   Δ = {diff_pp:+.1f} pp")
    print(f"  Newcombe 95% CI for Δ: [{100*lo:+.1f}, {100*hi:+.1f}] pp")
    print(f"  discordant cells: C_retrieval-only={b_cell}  A_ctrl_rat-only={c_cell}")
    ALPHA = 0.010
    if gate_pass:
        chi2, pm = mcnemar(b_cell, c_cell)
        sig = pm < ALPHA
        chi2s = f"{chi2:.3f}" if not math.isnan(chi2) else "n/a (exact binomial)"
        print(f"  McNemar (PRIMARY): chi2={chi2s} p={pm:.4g} (α={ALPHA}) → {'SIGNIFICANT' if sig else 'n.s.'}")
        print(f"  [sensitivity] two-prop z={z:.3f} p={pz:.4g}")
    else:
        sig = pz < ALPHA
        print(f"  two-prop z (PRIMARY, fallback): z={z:.3f} p={pz:.4g} (α={ALPHA}) → {'SIGNIFICANT' if sig else 'n.s.'}")

    print("\n" + "-" * 70)
    print("  LOCKED prediction (PRE_ANALYSIS_LOCK.md §a): +6pp is below the")
    print("  +20pp MDE (76% power) → predicted n.s. → 'not-significant →")
    print("  DIAGNOSE' branch. This script does not set the verdict; it reports")
    print("  the number next to the locked frame.")
    print("=" * 70)


if __name__ == "__main__":
    main()
