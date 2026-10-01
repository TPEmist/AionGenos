# Handoff: A15 — lock into pre-reg chain, THEN run (for isaac)

**From:** paper session
**To:** isaac session (owns master + the pre-registration chain + runs)
**Date:** 2026-10-01

## What
A15 draft is ready: `docs/paper/amendments/A15_draft.md` (on
`paper-v1.1-wip`). Four inference-only protocols + an R1' re-analysis,
each with prediction + locked fallback. It continues the D11 chain (A14
was last).

## The discipline (pre-registration integrity — do this in order)
1. **Lift A15 into the master D11 pre-reg chain as a LOCK COMMIT first.**
   The lock commit's hash is the amendment's anchor (same as A1–A14). The
   predictions/fallbacks must be committed *before* any A15 number exists.
2. **Only then run.** No protocol starts before the lock commit.
3. Tag/anchor the run outputs to that commit so the pre-result timestamp
   is auditable.

## The four protocols (full spec in A15_draft.md)
- **(a)** base Gemma + frozen buffer, NO adapter, n=100 seed 4500 paired.
  Pred SR < C_retrieval (49); fallback SR≈C_retrieval → "distil the
  competence" downgraded.
- **(b)** frozen buffer attached to A_action_only / B_main / D_gist, n=100
  each. Pred all rise to 45–55%; fallback any-no-rise → +34pp scoped
  A_ctrl_rat-specific.
- **(c)** R1' slope probe: round-1 ΔX vs required correction
  (target_X − init_EE_X), Spearman + permutation band (p2_r_tracker),
  5 arms + D10 teacher pool. Pred C_ret slope>0, distilled≈0, teacher>0
  wide σ. Fallback C_ret in-band → mechanism downgraded, σ withdrawn.
- **(d)** D6 memoryless-teacher true SR if a log exists; else keep derived.

## Resources
- All inference-only (attach/detach retrieval, swap base) → no training;
  runs on the frozen D10-ext buffer + existing adapters.
- Needs the teacher/student servers (your territory) + the frozen buffer
  (SHA-pinned). Seed base 4500, paired with the five D11 arms.

## Return path
Report A15 results as a confirmatory/exploratory-tagged pack (like the L2
confirmatory report). Paper session fills the TMLR + camera-ready numbers
from your pack per the routing table in A15_draft.md — paper does not
self-interpret. Push freeze note: this env has no push creds; actual
pushes are user-run.
