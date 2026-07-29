# Diagnostic 4b — R1 per-arm probe: PREDICTION (pre-registered)

**Timestamp intent: written and committed BEFORE the 4b script runs.**

**Filed:** 2026-07-28 (isaac session, master), under the locked
"not-significant → DIAGNOSE" branch. Probe definition is pre-specified in
`docs/paper/l2_analysis_adaptation.md` §23 (itself audit-log timestamped
before any L2 eval number).

## What 4b measures

The R1 (round-1) lateral-bias probe, adapted to L2 per-arm left-scored
eval (Amendment 3: right arm frozen, so the probe is single-arm on the
LEFT — structurally identical to L0a's R1 ΔX, no dual-arm generalisation
needed here).

For each eval episode:  **ΔX_L = (round-1 VLM left-target X) − (init
left-EE X)** = `vlm_interactions[0].parsed_left_pos[0] −
trajectory[0].left_ee_pos[0]` (reuses the frozen `d11_exploratory.r1_dx`
logic verbatim).

Computed for both eval protocols (A_ctrl_rat, C_retrieval) and compared
against the **L2-teacher's OWN R1 distribution**, measured from the L2
collect run `a6e6c917` (teacher-with-memory, 100 episodes). We do NOT
import L0a's −23.5 / −15.8 cm reference fingerprints (per §23): the L2
task has its own R1 signature.

## Hypothesis under test (marginal vs conditional — the paper's core probe)

The L0a mechanism finding: distillation transfers the *marginal* (a single
static R1 prior, low σ, same correction regardless of episode), while
retrieval supplies the *conditional* (per-episode-variable R1, higher σ,
tracks the situation). If that mechanism holds on L2:

## Pre-registered predictions (fixed now, both directions interpretable)

1. **A_ctrl_rat (distilled) left-arm R1 collapses to a static prior:**
   its ΔX_L distribution should be TIGHT (low σ) and centred on roughly
   one value — a marginal approximation, episode-independent.

2. **C_retrieval left-arm R1 is more conditional:** its ΔX_L should show
   HIGHER σ (per-episode variation) than A_ctrl_rat, because the retrieved
   lesson differs per episode. **This is the L2 analogue of the L0a σ
   finding.**
   - Caveat locked in advance: C_retrieval and A_ctrl_rat share identical
     weights (per Amendment 2/3); the ONLY inference-time difference is the
     retrieval preamble. So any σ difference is attributable to the
     preamble conditioning, not to weights.

3. **Reference to the L2-teacher's own R1:** report where each protocol's
   R1 mean/σ sits relative to the teacher's R1 mean/σ. No pass/fail
   threshold is pre-set (this is exploratory characterisation, not a
   confirmatory test) — we describe the relationship, we do not score it.

### What would WEAKEN the mechanism story (recorded so it can't be hidden)

- If A_ctrl_rat's ΔX_L σ is NOT lower than C_retrieval's (they're
  comparable), the "distillation = marginal collapse" reading does not
  reproduce on L2 — report that plainly.
- If BOTH σ are large and similar, R1 is not discriminating marginal from
  conditional at this task/n — report as inconclusive, not as support.

## Red-line (PRE_ANALYSIS_LOCK.md §c)

4b is exploratory mechanism characterisation. At n=100 with L2's low SR
(14/20 successes), the σ estimates are noisy; 4b contributes a *direction*
to the mechanism narrative, cross-checked against 4a (retrieval quality)
and 4c (rescue), never a standalone attribution. All 4b framing carries
the exploratory label.
