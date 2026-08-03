# Paper 2 Pre-Registration — SKELETON (draft, pre-data)

**Status**: SKELETON. Structure + locked criteria + a-priori hypotheses +
MDE/power method are fixed here; items marked **[TBD-R2]** await the second
read-through (per-generation N, exact iteration count, task suite) before
the prereg is sealed. No P2 data exists at skeleton time.
**Date drafted**: 2026-08-03 (isaac session, master).
**Carries over from P1**: the pre-registration discipline (numbered
amendments, SHA anchors, MDE-before-results, mechanical verify gates,
exploratory-label rules) applies unchanged. This page pins only what is
NEW to P2.
**Territory**: docs/p2_prereg/ is isaac's engineering-spec area (like the
L2 amendments), distinct from paper session's docs/paper/ prose.

---

## 0. One-line thesis

**P1 established that distillation transfers the *marginal* and context
carries the *conditional*. P2 asks whether an expert-iteration loop, using
retrieval as an amplifier, can progressively *consolidate the conditional
structure into the weights* — turning "externalise the memory" into
"internalise it, generation by generation."**

## 1. Core hypothesis

**H-main (expert iteration consolidates the conditional):** an
expert-iteration loop —
`C_retrieval (amplifier) → self-collect → distil → iterate` —
drives a student whose weights, generation by generation, absorb the
conditional correction that a single flat distillation could not (P1's T1
null). Concretely: the parametric (bare-weights, no-retrieval) student's
performance should **climb across generations toward the
retrieval-augmented ceiling**, closing the P1 gap from the weights side.

- Gen 0 = P1's A_ctrl_rat (flat-distilled, marginal only).
- Each gen g: run C_retrieval as the data generator (retrieval amplifies
  the current weights' behaviour), collect successful trajectories, distil
  into gen g+1 bare weights.
- H-main predicts: **bare-weights SR_g rises monotonically (in
  expectation) with g**, and the *conditional signature* (below) migrates
  from context-only into the weights.

**H-null (the honest alternative, pinned now):** iteration adds nothing
beyond gen-0 — the conditional structure is irreducibly contextual and
cannot be baked by self-distillation either. A flat or noisy SR_g trace
confirms H-null. (P1's T1 null is the gen-0 point; H-null = the whole
trace stays there.)

## 2. Primary criterion — r-tracking (the headline test)

**The confirmatory measure is not end SR but the residual-correlation
trace climbing out of the chance band, generation by generation.**

- **r = residual correlation**: per generation, the correlation between
  the *bare-weights* student's per-episode round-1 correction and the
  *situation* (init-config / target geometry) — i.e. how much the weights'
  correction is CONDITIONAL on the episode rather than a static prior.
  P1 measured this at gen 0 and it was ≈0 (the distilled arms collapsed to
  one prior; §4.4b "all corr ≈0").
- **r-tracking**: plot r_g across generations. **H-main predicts r_g
  climbs monotonically OUT of the chance band** (the CI around r=0 for the
  per-gen n). Consolidation = the weights' correction becoming
  progressively situation-dependent.
- **Tool provenance**: the r estimator is the D11 diagnostic machinery
  (`scripts/analysis/d11_exploratory.py` residual-correlation / rescue
  logic) **upgraded to a per-generation tracker**. The chance band is the
  same null-CI construction. Upgrade path: parameterise by generation +
  run_id, emit r_g + CI_g + a monotonicity test across g. **[TBD-R2]**
  exact estimator (Spearman on (correction, cfg_vec) vs a cleaner
  per-round residual) — to be locked before gen 0.
- **Why r, not SR**: SR is confounded by the competence floor (P1/L2
  showed conversion is competence-gated). r isolates whether the
  *conditional structure* is in the weights, independent of whether it
  cashes out to success — the cleaner mechanism claim.

## 3. A-priori hypothesis list (post-hoc P1 threads → pre-registered P2 predictions)

Each P1 exploratory thread is promoted here to an a-priori prediction with
matched-tier evidence designed in (the ruling that kept them one-liners in
P1: their home is this prereg).

### 3a. Minimum-viable-competence law → predictions (was: 3-instance post-hoc thread)
The three P1 instances become falsifiable P2 predictions:
- **P-MVC-teacher**: below a teacher task-competence floor, iteration
  cannot start (no successful self-collected data to distil). Predict a
  **cold-start threshold**: gens started below floor SR_teacher* show no
  r-climb. **[TBD-R2]** floor value from L2 (~28% per-arm) as the prior.
- **P-MVC-buffer**: the self-collected buffer must accumulate successes for
  retrieval to amplify; predict r-climb rate correlates with buffer
  success density per generation.
- **P-MVC-conversion**: (from L2 4c) rescue is start-distance-gated;
  predict the per-gen SR gain concentrates in the near-goal slice until
  multi-step competence itself is consolidated. Matched evidence: per-gen
  rescue-distance profiling (the 4c analysis, run each generation).

### 3b. Dose-dependent marginal → a dose-response CURVE (was: n=2 before/after)
P1/L2 showed even the marginal under-transferred at low training dose
(L0a 992 rounds → full; L2 511 → 72% short). P2 predicts a **dose-response
curve**: parametric-transfer completeness rises with per-generation
training volume. Design: **[TBD-R2]** vary per-gen data volume (or measure
it observationally across gens) to trace completeness vs dose — turning the
2-point observation into a curve with matched-tier evidence.

### 3c. J-lens / logit-lens mechanism probe (was: P1 "the instrument to test")
The mechanism chapter includes an **interpretability probe** to test
whether consolidation is real at the representation level, not just
behavioural:
- **J-lens/logit-lens**: across generations, probe whether the injected
  retrieval lesson's contribution migrates from being *read from context*
  (gen 0) to *emitted from weights* (gen g). Prediction: the logit
  contribution attributable to the retrieval preamble should DECREASE as
  the same conditional behaviour becomes weight-resident.
- Ties to P1's epiphenomenal-gist finding (B_main emitted PAST_LESSONS but
  it bought +1pp — produced, not read). J-lens is the direct instrument.
- **[TBD-R2]** exact probe (logit-lens on the action tokens vs a trained
  J-lens); scope to the mechanism chapter, exploratory-labelled until the
  probe's own validity is established.

## 4. MDE / power — computed BEFORE data (muscle, not lesson)

This time the event-driven power analysis is prospective by default (P1's
① lesson, now habit). To pin at skeleton stage:

- **Primary (r-tracking) power**: the confirmatory test is a monotonic
  trend in r_g across G generations, each estimated at per-gen n episodes.
  Power depends on (G, n, the true per-gen Δr, and r's sampling variance).
  **Method locked**: simulate the r-estimator's null band at candidate
  (G, n) to get the MDE on the per-generation slope Δr; pick (G, n) so a
  plausible Δr clears the band with ≥80% power. **[TBD-R2]** the plausible
  Δr prior (from gen-0 r≈0 and the retrieval ceiling's implied end-r).
- **Secondary (SR climb) power**: per-gen SR contrast reuses the L2
  MDE machinery (n=100 → ~12-13pp MDE at these baselines). A per-gen SR
  step below MDE is expected early; r-tracking is why SR is secondary.
- **Anti-p-hacking on the trend**: the monotonicity test + its α are
  locked before gen 0; generations are NOT peeked-at to decide when to
  stop (or a stopping rule is pre-registered). **[TBD-R2]** stopping rule
  (fixed G vs sequential with corrected α).

## 5. What is explicitly NOT claimed at skeleton stage
- No generation count, per-gen n, or task suite is final (**[TBD-R2]**).
- No mechanism attribution before the J-lens probe's validity is shown.
- r-tracking is the confirmatory spine; everything in §3 is
  hypothesis-with-designed-evidence, not a result.

## 6. Open items for the second read-through (to seal the prereg)
1. Lock the r-estimator + chance-band construction (upgrade of
   d11_exploratory.py) and its MDE simulation.
2. Fix (G, n, per-gen data volume) from the power sim + the WP1 task suite.
3. Decide task suite: does P2 stay on L2-family reach/push, or does it
   require the WP1 contact-control unlocks (closed-loop contact + expanded
   primitives) to have a task where conditional structure is rich enough to
   need consolidating? — depends on the WP1 technical-route decision
   (parallel deliverable).
4. Seal §3 predictions' matched-tier evidence designs.
