# Teacher configuration provenance — D10 (L0a) vs L2 collects

*Run-provenance record for the cross-task comparison (L0a vs L2) that
the paper will report. The teacher config delta must not become
archaeology three months from now.*

## The teacher config was NOT changed between D10 and L2 — the task was

`server/llama_server_teacher.sh` carried `--reasoning-budget 512`
unchanged from commit `a2aebb9` (2026-06-08) through the entire D10 /
D10-ext campaign (late June) and into the first L2 collect
(2026-07-14). Same binary, same model (gemma-4-31B-it Q4_K_M), same
mmproj, same ctx-size 16384, same `--parallel 1`.

## The delta is task, not config — and it surfaced a latent bug

- **D10 (L0a-Left, single-arm):** inline Stage-4 recap generation
  succeeded almost completely — across two 100-episode runs the
  collect logs show 0 and 1 "empty content" recap failures
  respectively (recaps_d10 = 547 records total across 7 runs).
- **L2 (dual-push) first collect:** inline recap failed 8/8 episodes,
  every one "Empty content in VLM response".

Same teacher config, opposite recap outcome. Root cause (confirmed
deterministically 2026-07-14): gemma-4's reasoning mode, enabled by
`--reasoning-budget 512`, can consume the entire 400-token output
budget on `reasoning_content` and return empty `content`
(finish_reason=length). The reflective recap prompt is the trigger,
and the L2 task inflates that prompt — dual-arm state, more rounds,
longer round-history — enough to push gemma into unbounded reasoning
where the terser L0a recap prompt did not. L0a's recap stayed under
budget by luck of prompt brevity, not by design.

## Fix and its cross-task implication

Teacher relaunched with `--reasoning off --reasoning-budget 0`
(commit `cabab3c`). Verified: the exact faithful L2 recap call that
returned empty now returns a real 469-char lesson in 7 s. Reasoning-off
is safe for L0a too (D10 succeeded on 512 precisely because it never
needed the reasoning tokens; removing them changes nothing there).

**Consequence for the paper's L0a-vs-L2 comparison:**
- D10 (L0a) recaps were generated **reasoning-on (budget 512)**.
- L2 recaps are generated **reasoning-off (budget 0)**.
- This is a teacher-config delta between the two tasks' *recap
  buffers*, introduced by the fix. It does **not** affect the students
  (both trained from their respective buffers' text) but it is a real
  provenance difference to disclose if the L0a and L2 memory buffers
  are ever compared directly.
- Stage-1 reasoning quality may differ subtly under reasoning-off vs
  reasoning-on. D10's Stage-1 ran reasoning-on; if a clean L0a-vs-L2
  comparison is needed, either (a) re-run L0a's recap buffer under
  reasoning-off for parity, or (b) report the delta explicitly. Cheap
  insurance recorded now rather than reconstructed later.

## One-line summary for run tables

- D10 / L0a teacher: gemma-4-31B Q4_K_M, ctx 16384, **reasoning-budget 512**.
- L2 teacher (from 2026-07-14): same, **reasoning off / budget 0**.
- Delta: reasoning off; forced by an L2-only empty-recap failure that
  L0a's shorter prompt had escaped by luck.
