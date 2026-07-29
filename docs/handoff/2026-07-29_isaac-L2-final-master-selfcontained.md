# Handoff: L2 confirmatory FINAL — master self-contained, push pending user

**From:** isaac session (L2 pipeline & analysis)
**To:** paper session (v1.1 writing)
**Date:** 2026-07-29

## Bottom line

The four-surgery revision of `docs/paper/l2_confirmatory_report.md` is the
**final** version. master is now **self-contained**: every path the report
references (eval scripts, format-contract gate, buffer pin, diagnostic
pack, per-arm eval spec) exists on master and is reproducibility-verified.

## Reproducibility hole closed (was blocking)

The per-arm eval code + the format-contract gate had been stray on the old
paper branch (`eb93ebb`) and the buffer pin (`9c2568a`) too — neither was
carried onto master in the 2026-07-28 untangle. Both cherry-picked:
- `125e270` ← eb93ebb: parser `scored_arm`, POSITION_RPY_2DOF templates,
  `scripts/diagnostics/check_eval_format_contract.py`, collect
  `eval_scored_arm`, driver `8.contract` step.
- `db8413f` ← 9c2568a: `workspace/l2_audit/frozen_buffer.sha256`.

**Verified from a CLEAN master-only export** (`git archive HEAD`): per-arm
code present (parser scored_arm×4, prompts RPY2 map×3, collect
eval_scored_arm×5, driver contract step×2); the format-contract gate script
runs and passes (3/3) using its master-committed imports. `l2_sft_*.jsonl`
is correctly gitignored (runtime training data, not repo content) — the
report references the gate *script*, which is present, not the data.

## Verdict / discipline (unchanged, still binding)

- +6pp, n.s., CI [−4.5,+16.4], sub-MDE; direction agrees with L0a.
- Two-level split (coverage=between-task size correlate n=2 consistent-with;
  start-distance=within-task conversion gate) — the anti-contradiction
  structure. §4 lists may / may-not; do not re-interpret.
- teacher per-arm SR pinned 28.0% → gap-closed 42.9% (exploratory label
  kept, only "≈" removed).
- MVC law: **one Discussion sentence only**; §4b now records the structural
  reason (mixed evidence tiers) so it is not built out — its home is the
  paper-2 pre-registration.

## Push status — ACTION NEEDED FROM USER

master is 4 commits ahead of origin/master (`b6df6b8`), fast-forward:
  `fe17349` (four surgeries) → `125e270` (per-arm code) →
  `db8413f` (buffer pin) → `6b1594d` (§4b structural reason)
This background isaac session has **no push credentials** (HTTPS remote, no
gh CLI, no usable SSH key). The user runs the push manually:
  `! git push origin master`
Territory rule now recorded: master push is isaac-only, executed by the
user on isaac's behalf. Until pushed, origin still shows the pre-surgery
`b6df6b8`; **paper session should read the report from the local master
worktree, or wait for the push, not from origin.**

## isaac next
Standing by in territory. Next isaac task is the paper-2 pre-registration
skeleton, but that waits for the second read-through results before opening.
