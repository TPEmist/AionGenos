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

---

# L2 auto-reset check (pin-8 rule applied to L2), 2026-10-06

**Command:** `python3 scripts/analysis/l2_autoreset_sensitivity.py`. Results are
in `docs/paper/data/l2_autoreset_sensitivity.json`.

**The limit exists in L2.** `L2DualPushEnvCfg` inherits from the IsaacLab
openarm ReachEnvCfg, which sets `episode_length_s = 24` (720 env steps). No
AionGenos class overrides it. L2 eval allows up to 40 rounds × 30 steps = 1200
steps.
- **Boundary:** index 718 in every episode. It is derived from the step counter,
  and every crossing is confirmed by the frozen-arm jump (0 ambiguous).
- **Trajectory length** (q1 / median / q3 / max):
  - A_ctrl_rat: 300 / 420 / 570 / 1200
  - C_retrieval: 300 / 390 / 510 / 1200

| Arm (run) | As-run SR | Episodes crossing | Successes after boundary | Sensitivity SR |
|---|---|---|---|---|
| A_ctrl_rat (`8384a740`) | 14/100 | 10 | 0 | 14/100 |
| C_retrieval (`2154e57e`) | 20/100 | 9 | 0 | 20/100 |

**Contrast:**

| | Δ | Newcombe 95% CI | z | p | McNemar 9/3 | Verdict |
|---|---|---|---|---|---|---|
| C_retrieval − A_ctrl_rat, as-run | +6.0 pp | [−4.5, +16.4] | +1.13 | 0.259 | p = 0.146 | n.s. at α = 0.010 |
| C_retrieval − A_ctrl_rat, sensitivity | +6.0 pp | [−4.5, +16.4] | +1.13 | 0.259 | p = 0.146 | n.s. at α = 0.010 |

The two rows are identical because no L2 success happened after the reset. The
**verdict is unchanged**: below the +20 pp MDE, n.s., DIAGNOSE branch. For the
paper: the L2 methods should state the 24 s time-out and that 9–10 episodes per
arm crossed it, with no success after the crossing.
