# Paper 2 Pre-Registration — SKELETON (draft, pre-data)

**Status**: SKELETON, partially sealed. Structure + locked criteria +
a-priori hypotheses + MDE/power method fixed. **[TBD-R2] wording/scope items
CLOSED** by the second read-through + WP1 decision (§7). Remaining opens are
**[PWR-SIM]** — task-data-dependent (Δr prior, G, n, dose grid, stopping
rule); these are the pre-flight work-list (§8), executed before gen 0, and
explicitly NOT sealable by a read-through. No P2 data exists yet.
**Date drafted**: 2026-08-03 (isaac session, master).
**Sealed-so-far update**: 2026-08-03 (WP1 3-decision + R2 read-through).
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
  r-climb. **Floor prior SEALED (R2):** use L2's pinned per-arm teacher SR
  **28.0%** (`workspace/l2_audit/TEACHER_PERARM_SR_PINNED.md`) as the
  order-of-magnitude cold-start prior; the exact P2 floor is task-dependent
  and re-estimated per task suite, but 28% is the registered starting bet.
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
training volume. Design: vary per-gen data volume (or measure it
observationally across gens) to trace completeness vs dose — turning the
2-point observation into a curve with matched-tier evidence.
**R2 caveat SEALED:** the v1.1 read-through (P5 ruling) flagged that at n=2
"dose" is confounded with task/buffer/contact; the P2 curve is the designed
de-confounder (dose varied *within* one task suite, holding those fixed),
which is exactly why this belongs in P2 not P1. The specific dose grid is a
design choice fixed alongside (G, n) in the pre-flight (§8), not a prose
item.

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
- **Scope SEALED (R2 rebuttal):** the v1.1 rebuttal notes schedule this
  interpretability measurement "once closed-loop contact control lands
  (paper 2)" — so J-lens is gated on WP1-① (OSC), the same root node the
  contact task suite needs. It is a P2 mechanism-chapter probe,
  exploratory-labelled until the probe's own validity is established. The
  exact probe (logit-lens on action tokens vs a trained J-lens) is a
  mechanism-chapter design item, not a confirmatory-spine [PWR-SIM].

## 4. MDE / power — computed BEFORE data (muscle, not lesson)

This time the event-driven power analysis is prospective by default (P1's
① lesson, now habit). To pin at skeleton stage:

- **Primary (r-tracking) power**: the confirmatory test is a monotonic
  trend in r_g across G generations, each estimated at per-gen n episodes.
  Power depends on (G, n, the true per-gen Δr, and r's sampling variance).
  **Method locked**: simulate the r-estimator's null band at candidate
  (G, n) to get the MDE on the per-generation slope Δr; pick (G, n) so a
  plausible Δr clears the band with ≥80% power. The plausible **Δr prior**
  (from gen-0 r≈0 and the retrieval ceiling's implied end-r) is
  **[PWR-SIM]** — see the boundary note below.
- **Secondary (SR climb) power**: per-gen SR contrast reuses the L2
  MDE machinery (n=100 → ~12-13pp MDE at these baselines). A per-gen SR
  step below MDE is expected early; r-tracking is why SR is secondary.
- **Anti-p-hacking on the trend**: the monotonicity test + its α are
  locked before gen 0; generations are NOT peeked-at to decide when to
  stop (or a stopping rule is pre-registered). **[PWR-SIM]** stopping rule
  (fixed G vs sequential with corrected α).

> **Boundary note (honesty rule, 2026-08-03).** Two kinds of open item are
> now separated. **[TBD-R2]** = wording/scope items the second read-through
> could seal — those are closed below (§7). **[PWR-SIM]** = items that
> require the actual power simulation + a real gen-0 r estimate; these
> **cannot be "sealed" by a read-through** and are NOT closed here.
> Pretending a read-through can fix a Δr prior would betray the very "MDE
> is muscle, computed from data" discipline this section exists to enforce.
> The [PWR-SIM] items are the P2 pre-flight work-list (§8), to be executed
> before gen 0, not before sealing this skeleton's prose.

## 5. What is explicitly NOT claimed at skeleton stage
- Generation count G, per-gen n, per-gen dose grid, and the stopping rule
  are **[PWR-SIM]** (need the power simulation), not sealed here.
- No mechanism attribution before the J-lens probe's validity is shown.
- r-tracking is the confirmatory spine; everything in §3 is
  hypothesis-with-designed-evidence, not a result.

## 6. Task suite — SEALED (from WP1 recon + PI decision 2026-08-03)

**P2 runs on a contact-rich task suite reached via the WP1 unlocks, NOT on
the L2-family reach/push.** Rationale: r-tracking needs a task whose
conditional structure is rich enough to have signal to climb; L2 already
showed reach/push's conditional component is thin (the +6pp/competence-gate
story). Contact tasks — where required force direction depends on contact
geometry, not just target position — are where consolidating a conditional
function is a non-trivial claim. Per PI decision Q1, these are **new L4+
tasks with the OSC controller**; L0–L3 stay on DiffIK, untouched. This also
resolves the earlier "does P2 need the contact unlock?" open item: **yes,
and WP1-① (OSC) is the root-node prerequisite**, now authorised to start.

## 7. [TBD-R2] items — CLOSED by the second read-through + WP1 decision
- **Task suite direction** → §6 (contact-rich, L4+/OSC).
- **§3a cold-start floor prior** → 28.0% (L2 pinned), §3a.
- **§3b dose confound** → sealed with the P5 de-confounder caveat, §3b.
- **§3c J-lens scope** → P2 mechanism chapter, gated on WP1-① (R2 rebuttal),
  §3c.
- **Mechanism-wording consistency** (R2 F1/P1/P2/P5): the L2 chapter's
  pre-data-conditional framing, MVC-law one-liner, R1-restoration post-hoc
  hedge, dose n=2 caveat are all applied in the paper worktree
  (`l2_methods_draft.md`, commit 7abb841); P2 prose inherits that register.

## 8. [PWR-SIM] pre-flight work-list — before gen 0 (NOT sealable by prose)
These require actual computation / a gen-0 estimate and are the P2
pre-flight, executed before the loop starts:
1. Upgrade `d11_exploratory.py` residual-corr → a per-generation r-tracker
   (r_g + CI_g + monotonicity test); lock the estimator + chance-band
   construction.
2. Estimate gen-0 r on the chosen contact task (needs WP1-① + a gen-0
   collect) → the Δr prior.
3. Power-simulate (G, n, dose grid) from that Δr prior → pick values with
   ≥80% power on the slope MDE.
4. Lock the stopping rule (fixed G vs sequential + α correction) from the sim.
Sealing the skeleton's prose does NOT close these; they are the muscle,
computed from data, not decided by a read-through.

## 9. Venue note (no action — pinned for later)
**CoRL 2026 LEAP workshop** (code-as-abstraction, skill-library
applicability boundaries) is the ASPIRE-worldview home crowd; P2's
external-library-vs-parametric-consolidation positioning has a natural
audience there. Recorded as a venue candidate; no action now.

## 8b. [PWR-SIM] progress (2026-08-06) — step 1 DONE, first hard constraint found

**Step 1 (r-tracker estimator + chance-band + monotonicity) — DONE, LOCKED.**
`scripts/analysis/p2_r_tracker.py` implements and self-tests:
- r_g = Spearman(round-1 correction c, situation feature s) — rank corr,
  robust to the bounded/nonlinear correction range.
- chance band = permutation null of r under H0 "correction is
  situation-independent" (2.5/97.5 pct); r_g above the upper edge ⇒
  significantly situation-conditional at gen g.
- confirmatory trend = monotonic_climb: Spearman(gen_index, r_g) with a
  permutation p (does r rise across generations?).
Self-test passes: a conditional signal clears the band (r=0.99), pure noise
sits inside it (r=0.20, not above), and a rising r-series trends up.

**First locked PWR-SIM constraint — G ≥ 5.** The permutation monotonicity
test cannot reach α=0.05 with fewer than 5 generations: even a PERFECT
r-climb gives min p=0.084 at G=4 (1 of 4! orderings, ">=" inclusive),
p=0.016 at G=5, 0.009 at G=6, 0.0004 at G=8. So **G≥5 is a hard floor** for
the confirmatory trend; a noisy real r will want more. This is a genuine
pre-flight number, computed not guessed.

**Steps 2–4 still BLOCKED on a contact task (honest scope).** Step 2 (gen-0
r estimate → Δr prior) needs a *chosen contact task with a gen-0 collect*.
WP1-① delivered a working OSC *controller*, but the contact *task* (scene +
WP1-③ press/twist primitives) does not exist yet. So the Δr prior, the G×n
grid (beyond the G≥5 floor), and the stopping rule cannot be filled until a
contact task exists to run a pilot collect on. The estimator is ready and
waiting; the task is the remaining dependency. Next real pilot step is
gated on WP1-③ (or an interim reach-based pilot to sanity-check the
estimator's variance on real replay data — a methods check, not the Δr
prior).
