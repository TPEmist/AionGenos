# Amendment 8 §8.4 — Cross-arm target length distributions

Row-set: 992 desirable + 1799 undesirable = 2791 rows, aligned across
all four arms via `--restrict_to_retrievable` (ep must have a rationale_map
hit).

Reference implementation: `scripts/training/prep_training_data.py`,
target composed exclusively via `_build_action_lines(inter)` + optional
gist / thought blocks.

## Per-arm target word count

| arm | n | min | p25 | median | p75 | p95 | max | mean | stdev |
|---|---|---|---|---|---|---|---|---|---|
| A_ctrl     | 2791 | 10 | 10  | 10  | 10  | 10  | 10  | 10  | 0.0  |
| A_ctrl_rat | 2791 | 88 | 123 | 131 | 140 | 146 | 146 | 131 | 11.2 |
| D_gist     | 2791 | 58 | 144 | 144 | 144 | 144 | 144 | 144 | 4.9  |
| B_main     | 2791 | 156| 256 | 265 | 274 | 280 | 280 | 264 | 12.5 |

## Pairwise median deltas (residual confounds)

| contrast | Δ median tokens | interpretation |
|---|---|---|
| B_main − A_ctrl_rat | +134 | retrieved gist content (+ ~134 length) |
| B_main − D_gist     | +121 | native thought (+ ~121 length)          |
| A_ctrl_rat − A_ctrl | +121 | native thought (+ ~121 length)          |
| D_gist − A_ctrl     | +134 | retrieved gist (+ ~134 length)          |

The two Δ pairs match to within ~0 tokens ⇒ the two factors (gist / thought)
are near-perfectly additive on target length. Length confound reduces to
two known constants and can be regressed out post-hoc if needed.

## Sensitivity analyses on record

1. **Token-count regression**: for each pairwise Δ SR, report the residual
   after regressing SR on target-token count across all four arms.
2. **D_gist secondary arm**: if T1 gives a significant B_main − A_ctrl, then
   B_main − D_gist isolates the "native thought" contribution and D_gist −
   A_ctrl isolates the "retrieved gist" contribution — each 121/134-token
   contrast has an equal-length partner arm to control against.
3. **C_retrieval** (see §8.5): weights identical to A_ctrl_rat, so C_retrieval
   − A_ctrl_rat is a pure inference-protocol contrast with no target-length
   confound in the training signal.
