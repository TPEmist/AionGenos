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
- **L2:** retrieval closes ≈43% of the per-arm gap (A_ctrl_rat 14% → L2
  per-arm teacher ≈28%; headroom 14 pp; +6 pp recovered ≈ 43%).

Cross-task statements should use the gap-closed proportion **with the raw
pp always reported alongside and the exploratory label attached.** (The
teacher per-arm SR denominator is the lock-time estimate ≈28%; if the
paper needs it pinned exactly, isaac can compute it from a6e6c917 per-arm
— currently used as the ≈ figure the lock recorded.)

---

## 3. Diagnostic appendix — why the effect is small, not absent

Three pre-registered diagnostics (each prediction committed before its
result). Every sentence here is exploratory and cross-checked; none is a
sole-cause claim.

### 3a. Retrieval quality degraded but functional
L2 retrieves systematically less-similar neighbours than L0a (identical
retriever config, n=100 each):
- top-1 median 0.900 → 0.870 (MW p=4.7e-17); top-3 median 0.883 → 0.827
  (MW p=1.3e-26); L2 has a low tail (min 0.73) L0a lacks.
- Consistent with the **5.5× thinner buffer** (547 vs 100 recaps, ~28
  usable left-aligned). "Attenuation ∝ buffer coverage" **quantitatively
  supported** — but necessary-not-sufficient (a close match to a
  near-failing recap is still a poor lesson).

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
end-task success is competence-gated: the one-shot retrieved correction
converts only where the start is already within reach of the 0.05m gate
(3c), so far-start episodes fire the correction yet miss the goal. The
effect is therefore small (+6pp, n.s.) rather than absent.** This is the
L2 face of the memory-success-floor / minimum-viable-competence law:
memory conditions the correction; it does not manufacture the multi-step
competence to execute it from far configurations. The thin L2 buffer (3a)
compounds this by degrading match quality, but 3b shows the mechanism
channel survives even so.

---

## 4. What the paper may and may not say

**May (bound to audit log):**
- "+6pp, n.s., CI [−4.5,+16.4]; below the pre-registered +20pp MDE;
  direction agrees with L0a." (§1)
- The competence-gated-conversion synthesis (§3 combined), exploratory.
- Headroom-normalized ≈43% gap-closed, **explicitly exploratory + raw pp
  alongside.** (§2)

**May NOT:**
- Call +6pp a positive replication of the effect size (it is n.s. and
  sub-MDE).
- Drop the exploratory label from §2 or §3.
- Attribute the attenuation to buffer coverage ALONE (3a is
  necessary-not-sufficient; 3b/3c qualify it).
- Upgrade the n=9 rescue clustering into a confirmatory claim (it explains
  the smallness; it does not change the n.s. verdict).

## 5. Reproducibility pointers
- Confirmatory: `scripts/analysis/l2_confirmatory.py` →
  `workspace/l2_audit/l2_confirmatory_output.txt`.
- Diagnostics: `workspace/l2_audit/DIAGNOSTIC_4{a,b,c}_{PREDICTION,RESULT}.md`
  + `_output.txt`.
- Pre-analysis lock: `workspace/l2_audit/PRE_ANALYSIS_LOCK.md`.
- Per-arm eval spec: `docs/paper/l2_amendment_3.md`.
- run_ids: A_ctrl_rat=`8384a740`, C_retrieval=`2154e57e`,
  L2-teacher(collect)=`a6e6c917`.
