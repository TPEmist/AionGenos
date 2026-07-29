# Diagnostic 4a — retrieval-quality audit: PREDICTION (pre-registered)

**Timestamp intent: written and committed BEFORE the 4a script runs.** The
git commit time is the proof the interpretation was fixed before seeing the
similarity distributions.

**Filed:** 2026-07-28 (isaac session, master), after the confirmatory
result (Step 3: +6pp, n.s.) and under the locked "not-significant →
DIAGNOSE" branch (PRE_ANALYSIS_LOCK.md).

## What 4a measures

The head diagnostic (pure CPU): the retrieval top-1 / top-3 **visual
similarity distributions**, L0a eval vs L2 eval, side by side. Both eval
runs log, per episode, one line:

    memory: injected 3 past eps [id,id,id] sims=[s1,s2,s3]

- L0a source: `logs/d11_C_retrieval_20260712_222441.log` (100 lines).
- L2 source:  `logs/l2_eval_C_retrieval_20260722_195917.log` (100 lines).

Extract top-1 (= s1, the max) and the top-3 mean per episode; compare the
two runs' distributions (median, IQR, and a two-sample location read).

## Hypothesis under test

**"Attenuation ∝ buffer coverage."** The retrieval effect shrank from
L0a's large margin to L2's +6pp. One candidate cause: the L2 retrieval
buffer is far thinner in usable (arm-aligned, success-floored) recaps than
L0a's, so L2 retrieves systematically *less similar* neighbours — the
memory it supplies is worse-matched, hence less able to carry the
conditional correction.

Coverage figures (buffer sizes, verified from the two logs' retriever
ready-lines — both configs identical: top_k=3, image_weight=0.4,
state_scale_cm=30.0, success_floor=0.67):
- L0a buffer: **547 recaps** in buffer.
- L2 buffer:  **100 recaps** in buffer, of which only ~28 are left-aligned
  desirable (per Amendment 1a; the L2 collect was 1/100 joint-success, so
  usable left-arm recaps are scarce). The success_floor=0.67 filter then
  further restricts what is retrievable at query time.
The ~5.5× smaller buffer (and far smaller usable-recap count) is the prior
that motivates the coverage hypothesis; 4a tests whether it actually
manifests as lower retrieved-neighbour similarity.

## Pre-registered interpretation (BOTH branches fixed now)

- **If L2 top-1/top-3 similarity is systematically LOWER than L0a**
  (distributions clearly shifted down, non-trivial gap in medians):
  → the "attenuation ∝ buffer coverage" hypothesis gains **quantitative
  support** — a thin buffer retrieves more-distant neighbours, consistent
  with a weaker retrieval effect. This becomes a reported diagnostic
  finding (still not a sole-cause claim; see red-line).

- **If the two similarity distributions are CLOSE** (largely overlapping,
  medians within noise):
  → the coverage hypothesis is **weakened** — L2 retrieves neighbours about
  as visually similar as L0a, so the +6pp attenuation must have another
  cause (candidate: even a similar-looking neighbour carries less useful
  *conditional correction* when the buffer's recaps are near-failing —
  the memory-success-floor finding; that would push attention to 4b/4c
  rather than to buffer size).

## Red-line (inherited from PRE_ANALYSIS_LOCK.md §c)

4a alone does not license a mechanism sentence. It sharpens or weakens ONE
candidate cause. A final attribution requires the 4a/4b/4c picture
together. Report 4a as evidence-for/against the coverage hypothesis, not as
"the reason retrieval attenuated on L2."

## Caveat to record with the numbers

similarity here is the retriever's own α-weighted image-cosine score
(image_weight=0.4 blended, per the injected-line `sims=`), identical
metric/config across both runs (top_k=3, image_weight=0.4,
state_scale_cm=30, success_floor=0.67 — verified from both logs' retriever
ready-line), so the comparison is apples-to-apples. It is NOT ground-truth
task relevance; a high cosine to a near-failing recap is still a poorly
useful lesson (that gap is exactly what branch-2 above points at).
