# Handoff → paper session: A15 (a)/(b) paired table + L2 auto-reset check

**From:** isaac · **Date:** 2026-10-06

## Files
- Table: `docs/paper/a15_ab_results.md`. Covers A15 (a)/(b) hit/miss with the
  lock's fallback text quoted verbatim, plus the L2 section.
- JSON: `docs/paper/data/a15_ab_stats.json` and
  `docs/paper/data/l2_autoreset_sensitivity.json`.
- Scripts that produce every number: `scripts/analysis/a15_ab_stats.py`,
  `scripts/analysis/l2_autoreset_sensitivity.py`, and
  `scripts/analysis/a15_slope_probe.py` (with `A15C_GATE_TOL_M=0.015`).

## Headline (labels as in the file)
- **(a) MISS.** base+buffer 48 vs C_retrieval 49, Δ −1 pp, z −0.14,
  p = 0.887. The lock's fallback is triggered: "distil the competence" is
  downgraded, and the pre-committed route is recipe rewrite (adapter
  non-essential).
- **(b) A_action_only: HIT.** action_only+buffer 53 vs its own no-retrieval
  D11 run 25, +28 pp, p = 4.9e-5; vs C_retrieval +4 pp, n.s. The (b) verdict
  is PENDING: B_main runs tonight, D_gist tomorrow night.
- Pairing: z is primary by the A14 §14.2 rule (fingerprint gate fails, 0 seed
  mismatches).
- Disclosed choices: α = 0.05 (D11 §4 default; A15 fixes none); MDE = 19.8 pp
  (the lock gives no number).
- **L2 auto-reset:** the limit exists, and 10 / 9 episodes per arm cross it.
  There are 0 successes after the crossing, so the sensitivity table is
  identical: +6 pp, CI [−4.5, +16.4], z 1.13, p 0.259, n.s. The verdict is
  unchanged.
