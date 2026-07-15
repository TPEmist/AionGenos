# L2 Amendment 2 — scope L2 to the answerable question (retrieval effect), staged

**Status**: LOCKED before any L2 training/eval. Filed 2026-07-15.
**Governs**: L2 extension scope. D11 frozen v1.0 untouched.

## Decision: L2 tests ONE question, not a symmetric 2×2

L2's desirable pool is 56 per-arm instances (vs L0a's 992). The two D11
headlines have opposite detectability at this n and pool:

- **T4-class (identical-weights retrieval, C_retrieval − A_ctrl_rat):**
  the strongest D11 result (+34pp, z=5.15). At L2 baseline ~15%, power
  at n=100, α=0.010 is **76% for +20pp, 99% for +30pp, 100% for +34pp**.
  Detectable. This is the question L2 can answer.
- **T1-class (bake-in, B_main − A_action_only):** L0a effect was +1pp;
  L2 MDE at α=0.020, n=100 is **12–13pp**. Measuring a ~1pp effect on a
  12pp-MDE instrument with 1/17 the training data = a guaranteed
  uninformative null (small effect × blunt instrument × thin data).
  Running it would spend compute to write "n.s., underpowered".

**A symmetric 4-arm 2×2 on L2 is formal symmetry, not information.**
The honest L2 question is: *does the identical-weights retrieval effect
replicate on a second, harder task in the same primitive family?* —
which is exactly the half a cross-task regularity needs, and D11's
single strongest result.

## Stage 1 (this window): A_ctrl_rat + C_retrieval only

- Train ONE adapter: A_ctrl_rat (all 56 desirable episode-instances →
  thickest possible pool for the one adapter that matters).
  - **Training adequacy (distinct from eval power — do not conflate):**
    the 56 desirable EPISODE-instances expand to **511 desirable /
    1119 undesirable per-arm ROUNDS** (KTO trains on rounds). So the
    training signal is 511/1119, not 56 — moving A_ctrl_rat-L2's
    training adequacy from "borderline" to "healthy". This concerns
    whether the adapter can be *fit*, NOT the n=100 eval's power to
    *detect* the C_retrieval−A_ctrl_rat contrast (that is the separate
    Power/MDE analysis below, governed by episode-level n=100).
- Two eval protocols: A_ctrl_rat bare + C_retrieval (reuses A_ctrl_rat's
  weights + frozen re-tagged buffer, success_label_arm='left').
- ~12h A4500 (not 30h); the difference returns to the LIBERO gate.
- Primary L2 contrast: **C_retrieval − A_ctrl_rat** (identical-weights),
  two-sided, McNemar/z per the D11 machinery.

## Conditional-expansion criterion (pinned NOW, before any L2 number)

After Stage 1 eval:
- **C_ret − A_ctrl_rat significant AND same direction as L0a** →
  cross-task headline secured. THEN decide whether to add A_action_only
  (Stage 2, +6h) to get the L2 "rationale tax" version. **D_gist is not
  run in either stage** — L0a already established its (secondary) role.
- **Not significant, OR reversed** → this is itself a major finding
  (the effect does NOT cross tasks). The response is NOT more arms; it
  is DIAGNOSIS — why does L2 retrieval fail to supply conditional value
  (lesson quality? L2's conditional structure genuinely smaller?).
  Pinned here so a non-replication is not mistaken for "run more arms".

## Paper wording (locked half-grade down)

- L2 claim = "*the identical-weights retrieval effect replicates on a
  second, harder task*", NOT "the full 2×2 replicates".
- T1's absence on L2 is stated as an MDE-driven **design choice**
  (cite this addendum's 12-13pp MDE + L2 prereg's 20pp disclosure), so
  it reads as discipline, not omission. Third application of the ①
  lesson: event-driven power analysis, now used prospectively to
  *decide what not to run*.

## Power/MDE table (for the addendum)

Detectable (T4-class, α=0.010, n=100, baseline 15%):
  +20pp → 76% power; +30pp → 99%; +34pp → 100%.
Not detectable (T1-class, α=0.020, n=100): MDE 12pp (baseline 15%),
13pp (baseline 20%); L0a bake-in effect was +1pp.
