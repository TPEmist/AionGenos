# D11 Amendment 15 — protocols (a) and (b), paired results (2 of 4 arms)

**Filed** 2026-10-06 by isaac. Every number in this file comes from
`python3 scripts/analysis/a15_ab_stats.py` (written to `logs/a15_ab_stats.json`)
and from `A15C_GATE_TOL_M=0.015 python3 scripts/analysis/a15_slope_probe.py`.
- Lock: `989a753`.
- Operational pins and A15.1: see `docs/d11_preregistration.md`.
- Runs, from `logs/a15_manifest.jsonl`. Every arm passed the frozen-buffer
  readonly gate: tree hash `7d4f3f9e…` before and after.
  - (a) base + buffer: run `995f496c`
  - (b) A_action_only + buffer: run `9be74fc2`
- Still pending, run order (b) B_main, then (b) D_gist. The (b) verdict cannot
  be closed until both have run.

## Analysis rules applied (locked, plus disclosed operationalisations)
- **Pairing.** Seeds are 4500+k. 0/100 seed mismatches in every contrast.
  - The A14 §14.1 fingerprint gate (eps 1e-4 on trajectory[0]) **fails** in
    every contrast: 75 / 76 / 99 mismatches. This is the same instrument
    behaviour as D11, where 377 mismatches occurred: trajectory[0] is logged
    after the first execute step, and that step depends on the arm's first
    action.
  - Consequence, by the A14 §14.2 rule, applied mechanically: **two-proportion
    z is primary**. McNemar is reported as a sensitivity check.
- **α.** A15 fixes no α. I use the D11 §4 default: **α = 0.05, two-sided**.
  This is a disclosed choice.
- **"Within the paired MDE".** The lock gives this no number. I disclose the
  following operationalisation: MDE = 19.8 pp (two-sided α .05, power .8,
  n = 100, at the C_retrieval rate). The (a) verdict does not depend on this
  choice, because |Δ| = 1 pp is inside any plausible MDE.
- **Sensitivity SR.** Pin 8 (24 s auto-reset) is applied to every contrast.

## Table

| Contrast | SR | Δ | z (primary) | p_z | McNemar b/c, p | Pin-8 sensitivity |
|---|---|---|---|---|---|---|
| (a) base+buffer vs C_retrieval | 48 vs 49 | −1 pp | −0.14 | 0.887 | 11/12, p=1.0 | 48 vs 48, Δ 0, p=1.0 |
| (b) action_only+buffer vs C_retrieval | 53 vs 49 | +4 pp | +0.57 | 0.572 | 19/15, p=0.607 | 53 vs 48, Δ +5, p=0.479 |
| (b) action_only+buffer vs A_action_only (its own D11 run, no retrieval) | 53 vs 25 | **+28 pp** | +4.06 | 4.9e-5 | 38/10, p=9.7e-5 | 53 vs 21, Δ +32, p=2.8e-6 |

## Against the lock

**(a) Prediction:** "SR < `C_retrieval` (49/100). The gap = what the adapter
contributes …"
**Result: MISS.** 48 vs 49, Δ −1 pp, p = 0.887. There is no gap.
**Fallback triggered.** Lock text, verbatim: "if SR ≈ `C_retrieval` (within
the paired MDE), then **"distil the competence" is downgraded** — the adapter
is not necessary and retrieval is independently sufficient. We rewrite the
recipe accordingly and report it plainly; no spin."
Pre-committed route: "(a) no gap → recipe rewrite (adapter non-essential)."

**(b) Prediction:** "all three rise into the teacher band (≈45–55% SR),
showing the retrieval effect is not specific to `A_ctrl_rat`'s weights."
**Result for A_action_only: HIT.**
- It rose from 25 to 53 (+28 pp, p = 4.9e-5). 53 is inside 45–55.
- The (b) verdict stays **PENDING** until B_main and D_gist have run.
- Locked fallback, for reference only; it does not apply yet: "if any adapter
  does **not** rise, we report it as **adapter-dependent**, and the +34 pp is
  explicitly scoped as `A_ctrl_rat`-specific."

## R1' slope for the new arms
These numbers have pre-registered reading status under A15.1: the 15 mm gate,
with slope > 0 iff r is above the band.
- The lock states no directional prediction for these two arms. So this is a
  reading, not a hit/miss.
- Both arms had 100/100 episodes pass the gate.

| Arm | Spearman r | Permutation band | Above band |
|---|---|---|---|
| (a) base+buffer | +0.291 | [−0.209, +0.187] | yes |
| (b) action_only+buffer | +0.487 | [−0.203, +0.186] | yes |

For context only, and labelled post-hoc per A15.1: C_retrieval r = +0.306
(above its band). The four distilled arms without retrieval have r between
−0.16 and −0.30.

## Routing for the paper session
- The (a) MISS selects the pre-committed route: **recipe rewrite. The adapter
  is non-essential; retrieval alone is sufficient on the base model.**
  The title and claims that rest on "distil the competence" fall under this
  route.
- (b) stays pending. With 1 of 3 arms in, the rise is consistent with the
  "+34 pp generalises beyond `A_ctrl_rat`" route, but that route cannot be
  selected until B_main and D_gist report.
