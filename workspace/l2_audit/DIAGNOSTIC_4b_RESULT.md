# Diagnostic 4b — R1 per-arm probe: RESULT

**Filed:** 2026-07-28, AFTER the pre-registered prediction
(`DIAGNOSTIC_4b_PREDICTION.md`, commit `d3705e6`). Raw output:
`DIAGNOSTIC_4b_output.txt`.

## Numbers (ΔX_L = round-1 left-target X − init left-EE X, grid units)

| distribution | n | mean | σ | median | range |
|---|---|---|---|---|---|
| **L2-teacher** (a6e6c917, reference) | 100 | **−17.1** | 18.2 | −15.0 | [−64, +19] |
| **A_ctrl_rat** eval (distilled)      | 100 | **−4.8**  | 15.5 | −4.0  | [−45, +19] |
| **C_retrieval** eval                 | 100 | **−17.2** | 17.3 | −17.0 | [−55, +22] |

## Verdict against the pre-registered predictions

**The σ prediction did NOT clearly fire; a stronger MEAN/bias signal did.**

- **Prediction 2 (C_retrieval higher σ than A_ctrl_rat) — WEAK / not
  supported.** σ_C = 17.3 vs σ_A = 15.5, ratio 1.12, variance-ratio
  F = 1.25. This is the "weakening condition" recorded in the prediction:
  at L2's task/n, the σ probe does **not** strongly separate marginal from
  conditional. Reported plainly, not spun as support.

- **Unregistered but clean MEAN finding (flagged exploratory):** the
  round-1 bias *magnitude* separates the arms sharply and in the
  mechanism-consistent direction:
  - A_ctrl_rat (distilled) collapses to a **too-shallow prior**: mean
    ΔX_L = −4.8 (median −4.0), peak at 0 in the histogram.
  - C_retrieval **recovers the teacher's bias almost exactly**:
    mean −17.2 vs teacher −17.1 (medians −17.0 vs −15.0).
  So distillation kept a marginal R1 prior but at ~28% of the teacher's
  displacement magnitude; the retrieval preamble (identical weights)
  pulls the round-1 target back onto the teacher's magnitude.

This is the L2 analogue of the L0a §4.3 finding ("the distilled arms
collapse onto one static prior"), seen on the **mean axis rather than the
σ axis**: on L2 the distilled prior is not just static, it is
*magnitude-deficient*, and retrieval restores the magnitude. Since
C_retrieval and A_ctrl_rat share identical weights, the −4.8 → −17.2 shift
is attributable to the retrieval preamble alone.

## Red-line held

Exploratory mechanism characterisation. The mean finding was not
pre-registered (the σ test was), so it carries the exploratory label
doubly. σ estimates are noisy at n=100 / low SR. 4b contributes a
*direction* — "distillation under-shoots the R1 bias magnitude; retrieval
restores it" — to be cross-read with 4a (retrieval quality degraded but
still functional) and 4c (which episodes retrieval rescued). Not a
standalone attribution.

## Note for the report

The pre-registration correctly anticipated the σ test might not fire and
said so; the mean result is the informative one and is labelled
post-hoc/exploratory accordingly. The honest headline: **on L2, retrieval
still moves the round-1 action back onto the teacher's bias (−4.8 →
−17.2 ≈ teacher −17.1), i.e. the conditional-correction channel is intact
at the R1 level even though the end-to-end SR gain is only +6pp** — which
sharpens the puzzle 4c must address: if R1 is corrected, why does the
success rate barely move?
