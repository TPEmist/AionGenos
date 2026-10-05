# Handoff: same-hardware inference-cost re-measure (for isaac, with A15 batch)

**From:** paper session
**To:** isaac session
**Date:** 2026-10-05
**Why:** the "~50–75× lower inference cost" claim has no derivation on disk
(audit: `AionGenos-paper/docs/paper/cost_claim_audit.md`), and existing
replays can't support a cost table — student `full_response` is empty in
all 5 runs (0/≈1900 each; constrained-decode path never stored text), and
`latency_ms` is per-call wall-clock confounded by run-time server/hardware
conditions (teacher 13 s vs student 16 s on the same 31B base). We need a
clean, same-hardware measurement.

## Measurement script (NEW standalone — do NOT edit the frozen collect.py)
A measurement-only harness that hits the SAME llama-server, back-to-back,
replaying prompts stored in the replays. Replay ~20 steps for each of:
1. **teacher** (two-pass: reasoning + recap, with memory)
2. **student bare** (A_ctrl_rat, single call)
3. **student + retrieval** (C_retrieval: single call + retrieval)

Per call, record:
- **prompt tokens** and **completion tokens** from the server `usage`
  field (llama-server returns these — the real numbers, not reconstructed).
- **wall-clock per call** (same machine, back-to-back → comparable).
- **retrieval overhead** (embedding + query ms) listed SEPARATELY for the
  +retrieval condition, not folded into the LM call.
- **store the student `full_response` text in THIS harness** (fixes the
  empty-text gap — but in the measurement script, NOT by touching the
  frozen collect.py).

## What the paper needs back
A small table: protocol × {LM calls/step, prompt tok/step, completion
tok/step, wall-clock s/step, retrieval overhead ms}. From it the paper
states the honest claim: "generates N× fewer tokens/step; wall-clock
comparable on this setup because prefix-dominated." The token ratio
replaces the unanchored 50–75× with a measured number.

## Sequencing
Fold into the A15 run batch (same servers, same session) — one warm-up of
the teacher/student servers covers both. Not urgent for the workshop
camera-ready (10/10 deadline — that version already dropped the claim to
"substantially lower"); it IS needed before the TMLR full version ships.

## Territory
Measurement script + run = isaac (master, servers). Paper session fills
the TMLR cost table from the returned numbers, does not run.
