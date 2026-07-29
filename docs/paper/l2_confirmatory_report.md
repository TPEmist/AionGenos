# L2 Confirmatory Report + Diagnostic Appendix

**From:** isaac session (L2 pipeline & analysis)
**To:** paper session (v1.1 writing) — for translation into the L2 chapter.
**Date:** 2026-07-28.
**Verdict authority:** this report's wording is bound to
`workspace/l2_audit/PRE_ANALYSIS_LOCK.md` (committed `65d70c1`, before any
p-value) and the per-diagnostic prediction/result pairs (commits `7c06923`
/ `f270425`, `d3705e6` / `b1bb934`, `28f7c9c` / `01884b7`). **The paper
session translates this into prose but does not re-interpret the verdict.**

---

## 1. Confirmatory result (the headline number)

**Question (Amendment 2 scope):** does the identical-weights retrieval
effect (C_retrieval − A_ctrl_rat) replicate on the harder L2 task?

**Per-arm eval (Amendment 3, left-scored, n=100 paired, seed_base 4600):**

| protocol | successes / n | SR |
|---|---|---|
| A_ctrl_rat (bare) | 14 / 100 | 14% |
| C_retrieval | 20 / 100 | 20% |

- **C_retrieval − A_ctrl_rat = +6.0 pp.**
- **Newcombe 95% CI: [−4.5, +16.4] pp.**
- Primary test: two-proportion z = 1.129, **p = 0.259 → n.s.** (α=0.010,
  T4-class). The paired McNemar was the intended primary; the pairing gate
  fell back to z per A14 §14.2 (see §1.1). Under McNemar the discordant
  cells are 9 vs 3 — same n.s. conclusion.

**Locked verdict (verbatim from the pre-analysis lock, do not soften or
strengthen):**
> The point estimate is below the pre-registered MDE (+20 pp for 76%
> power, Amendment 2); the direction agrees with L0a; the confidence
> interval simultaneously admits zero and a moderate effect.

This is the **"not-significant → DIAGNOSE"** branch of Amendment 2 — a
sub-MDE point estimate is met with the diagnostic pack (§3), not with more
arms. The verdict was fixed before the number was seen; a +6pp result was
predicted n.s. in advance and is.

### 1.1 Pairing integrity (why z, not McNemar)

seed was identical across the two protocols on 100/100 episodes; the
frozen right arm (Amendment 3 holds it in place) matched at integer + RPY
resolution on 94/100. The float fingerprint gate (eps=1e-4) failed on 17
episodes at ~1e-4 drift, because `trajectory[0]` is already servo'd one
step and the scored (left) arm's differing first action perturbs the
shared-sim float state. **Pairing is physically real but not
machine-verifiable from the persisted replay → mechanical z fallback
(A14 §14.2), which is n.s. anyway.** No discretion was exercised; the
mechanical rule chose the test.

---

## 2. Headroom-normalized cross-task framing (POST-HOC, EXPLORATORY)

**Label is mandatory and non-droppable** (PRE_ANALYSIS_LOCK.md §b): this
framing was introduced after the raw SR was known.

Raw pp is misleading across tasks with different achievable headroom. On a
gap-to-teacher basis:
- **L0a:** retrieval closed ≈100% of the parity gap to the teacher.
- **L2:** retrieval closes **42.9%** of the per-arm gap (A_ctrl_rat 14% →
  L2 per-arm teacher **28.0%**; headroom 14 pp; +6 pp recovered = 6/14 =
  42.9%).

**Teacher per-arm SR is now PINNED (no "≈"):** `left_reached = 28 / 100`
at the registered 0.05m threshold, from `workspace/l2_audit/
per_arm_rescore.json` (run a6e6c917; right_reached also 28, both 10,
per_arm_any 46). So the left-scored headroom denominator is exactly 28.0%
and the gap-closed figure is exactly 42.9%.

Cross-task statements should use the gap-closed proportion **with the raw
pp always reported alongside and the exploratory label attached.** The
gap-closed framing itself remains POST-HOC/exploratory (introduced after
raw SR); pinning the denominator does not change that label — only removes
the "≈".

---

## 3. Diagnostic appendix — why the effect is small, not absent

Three pre-registered diagnostics (each prediction committed before its
result). Every sentence here is exploratory and cross-checked; none is a
sole-cause claim.

### 3a. Retrieval quality degraded — a CROSS-TASK correlate (not a within-task predictor)
L2 retrieves systematically less-similar neighbours than L0a (identical
retriever config, n=100 each):
- top-1 median 0.900 → 0.870 (MW p=4.7e-17); top-3 median 0.883 → 0.827
  (MW p=1.3e-26); L2 has a low tail (min 0.73) L0a lacks.
- Consistent with the **5.5× thinner buffer** (547 vs 100 recaps, ~28
  usable left-aligned).

**Level-of-analysis guard (pre-empts the reviewer's "your similarity story
contradicts 4c"):** the coverage finding lives at the **cross-task** level
— *between* L0a and L2, lower buffer coverage co-occurs with lower
retrieved similarity and a smaller effect. This is **consistent-with, not
established**: it is a correlation across **n = 2 tasks**, which cannot
support a causal "∝". We state it as "the L2 attenuation is consistent with
reduced buffer coverage", and no stronger.

Crucially this is a **different level** from 4c: *within* L2, retrieval
match quality does **not** predict which episodes succeed (4c: rescue
similarity is if anything slightly LOWER, 0.847 vs 0.868, p=0.03). There is
no contradiction — coverage is a between-task correlate of the effect's
*size*; within-task *conversion* is gated by start distance (§3c), not by
match quality. Two findings, two levels; the apparent tension dissolves
once they are not conflated.

### 3b. Retrieval still restores the teacher's round-1 bias
R1 left-arm lateral bias ΔX_L (vs the L2-teacher's OWN R1, not L0a's
transplant):
- teacher mean −17.1 | A_ctrl_rat (distilled) **−4.8** | C_retrieval
  **−17.2**.
- The pre-registered σ test did **not** fire (σ 15.5 vs 17.3, F=1.25 — the
  recorded weakening condition, reported plainly). The informative signal
  is the **mean**: distillation collapses to a *magnitude-deficient* prior
  (~28% of teacher displacement); the retrieval preamble (identical
  weights) restores the teacher's magnitude almost exactly (−4.8 →
  −17.2 ≈ −17.1). The L2 analogue of L0a §4.3 static-prior collapse, on
  the mean axis. (Mean finding is post-hoc/exploratory; σ test was the
  registered one.)

**The cross-task comparison worth foregrounding (EXPLORATORY): even the
marginal transfer appears dose-dependent.** On L0a the distilled arms'
R1 fingerprint sat right on the memory-teacher's (−16.7 ≈ −15.8) — the
marginal transferred essentially in full. On L2 the distilled prior
reaches only −4.8 against the teacher's −17.1 — **~72% short; this time
even the marginal did not transfer fully.** The ready candidate is
training dose: L2's per-arm distillation saw 56 episodes / 511 rounds
versus L0a's 992 — so *learning even a constant appears to be
dose-limited*. This adds a dimension to the marginal/conditional frame:
**marginal transfer is cheap but not free** — below some data floor even
the static prior is under-learned. Same-source as 3a's coverage story (the
1/100-joint-success L2 collect starves both the training pool and the
retrieval buffer). Labelled exploratory (n=2 tasks, no dose-response
curve — a single before/after point).

### 3c. Rescue is gated by start distance, not memory match (SURPRISE)
The +6pp = 9 rescues (C✓A✗) − 3 regressions (A✓C✗). Rescues share a sharp
init-pose signature (branch 1 fired, against the recorded expectation of
diffuse noise):
- rescue init dist_red mean 13.9cm vs both-fail 21.6cm, **MW z=−3.88,
  p=1e-4** — retrieval rescues almost only episodes that start close.
- Rescue retrieval-similarity is **not** higher (0.847 vs 0.868, p=0.03) —
  rescue is not explained by better memory match; **start distance is**
  the decisive variable.

### Synthesis (licensed mechanism sentence — red-line lifted for the combined picture only)
**The identical-weights retrieval effect replicates on L2 in mechanism
(R1 correction, 3b) and in direction (+6pp), but its conversion to
end-task success is competence-gated: the single episode-level retrieved
correction converts only where the start is already within reach of the
0.05m gate (3c), so far-start episodes fire the correction yet miss the
goal. The effect is therefore small (+6pp, n.s.) rather than absent.**

**"Single episode-level correction" is literal, verified 2026-07-29:**
C_retrieval retrieves ONCE per episode, anchored on `init_L_EE`, injected
only into the round-0 prompt (`retrieve_for_episode` in the episode loop,
outside the round loop; preamble gated to `round_idx == 0`). There is no
per-round re-retrieval — later rounds ride the conversation history. So
the retrieved lesson biases the *initial* direction and nothing re-aims it
mid-trajectory; the "one-shot / limited range" reading is a fact of the
mechanism, not a metaphor.

**Two levels, kept separate (the anti-contradiction structure):**
- *Between tasks* (3a, n=2): thinner buffer → lower retrieved similarity →
  smaller effect. Consistent-with, correlational, the effect's **size**.
- *Within L2* (3c): conversion is gated by **start distance**, not match
  quality. The effect's **incidence**.
Coverage explains why L2's effect is smaller than L0a's; start-distance
explains which L2 episodes it lands on. No single-level story has to carry
both.

This is the L2 face of the memory-success-floor / minimum-viable-competence
law: memory conditions the correction; it does not manufacture the
multi-step competence to execute it from far configurations.

**Two-paper thread (Discussion, one sentence):** this dovetails with D11's
recovery-timing null (rescues converge monotonically *from R1*, not via a
mid-trajectory save). Both datasets say the same thing from opposite ends:
**retrieval's value is front-loaded — it sets the initial direction — and
whether that cashes out depends on how far the corrected trajectory still
has to travel.** L2's start-distance gate (3c) is the range limit of a
front-loaded correction; D11's monotonic-from-R1 convergence is its timing
signature. Worth one connecting sentence in Discussion; the two results
corroborate each other.

---

## 4. What the paper may and may not say

**May (bound to audit log):**
- "+6pp, n.s., CI [−4.5,+16.4]; below the pre-registered +20pp MDE;
  direction agrees with L0a." (§1)
- The competence-gated-conversion synthesis (§3 combined), exploratory.
- Headroom-normalized **42.9%** gap-closed (teacher per-arm SR pinned at
  28.0%), **explicitly exploratory + raw pp alongside.** (§2)
- "even the marginal transfer appears dose-dependent" (3b cross-task),
  explicitly exploratory (n=2, single before/after point).
- The two-level framing (coverage = between-task size correlate;
  start-distance = within-task conversion gate) — this is the intended
  defence against the "similarity explains attenuation but not rescue"
  reviewer objection.
- "single episode-level / front-loaded retrieved correction" — verified
  literal (round-0-only injection, init_L_EE anchor).

**May NOT:**
- Call +6pp a positive replication of the effect size (it is n.s. and
  sub-MDE).
- Drop the exploratory label from §2 or §3 (pinning 28.0%/42.9% removes
  the "≈", NOT the exploratory label).
- Attribute the attenuation to buffer coverage ALONE, OR state a causal
  "∝" — 3a is a cross-task correlate over **n=2 tasks** (consistent-with,
  not established); 3b/3c qualify it.
- Say retrieval match quality predicts within-L2 success (3c: it does not).
- Upgrade the n=9 rescue clustering into a confirmatory claim (it explains
  the smallness; it does not change the n.s. verdict).

## 4b. Discussion thread — the minimum-viable-competence law, now with three faces (paper-2 seed, NOT a paper-1 claim)

One connecting sentence in Discussion, no more. A single threshold law now
shows up at three points in the pipeline, each an instance of "below some
competence/experience floor, the mechanism has nothing to act on":

1. **Teacher → distillation/RL:** the teacher must clear a task-competence
   floor before its behaviour is worth distilling (cf. SimpleVLA-RL's
   RL cold-start; and L2 dual-push at 1% joint SR sitting below it).
2. **Buffer → retrieval:** the retrieval buffer must contain success
   experiences to condition on — L2's near-failing teacher buffer supplies
   "others also failed here", not a correct-correction map (the
   memory-success-floor finding already in v1.1_notes.md).
3. **Student → conversion (NEW, from 4c):** the student needs a
   close-enough start for a single front-loaded correction to convert —
   far-start episodes fire the R1 correction but cannot reach the goal
   (4c: rescue dist_red 13.9 vs 21.6cm, p=1e-4).

The same floor seen at the teacher (can it be learned from), the buffer
(is there success to retrieve), and the student (is the start within one
correction's range). **Frame as paper-2 foreshadowing — the unifying
observation, not a paper-1 result.** Do not over-develop; one sentence
noting the three instances converge on a minimum-viable-competence law.

## 5. Reproducibility pointers
- Confirmatory: `scripts/analysis/l2_confirmatory.py` →
  `workspace/l2_audit/l2_confirmatory_output.txt`.
- Teacher per-arm SR pin: `workspace/l2_audit/TEACHER_PERARM_SR_PINNED.md`
  (left_reached 28/100 → 28.0%; gap-closed 42.9%).
- Diagnostics: `workspace/l2_audit/DIAGNOSTIC_4{a,b,c}_{PREDICTION,RESULT}.md`
  + `_output.txt`.
- Pre-analysis lock: `workspace/l2_audit/PRE_ANALYSIS_LOCK.md`.
- Per-arm eval spec: `docs/paper/l2_amendment_3.md`.
- run_ids: A_ctrl_rat=`8384a740`, C_retrieval=`2154e57e`,
  L2-teacher(collect)=`a6e6c917`.
