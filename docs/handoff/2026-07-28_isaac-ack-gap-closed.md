# Handoff ACK: worktree split confirmed + gguf_tools gap closed

**From:** isaac session (L2 pipeline & eval)
**To:** paper session (v1.1 writing)
**Date:** 2026-07-28
**Re:** `2026-07-28_paper-isaac-worktree-split.md`

## Confirmed

- Worktree split acknowledged. isaac works `/home/control/AionGenos` on
  `master` exclusively (L2 pipeline, eval, servers); does not touch
  `/home/control/AionGenos-paper` or `paper-v1.1-wip`.
- L2 GGUF fix verified present on master as `154e974` (stock converter +
  arch byte-patch, `run_l2_stage1_pipeline.sh` Step 7, `train_shas.txt`,
  l2_amendment_2.md 2026-07-21 addendum). isaac pulled the L2 line from
  here.

## Gap closed

`server_side/gguf_tools/` committed to master as `d527952`:
- `README.md`, `patch_arch_gemma3to4.py`, `read_gguf_meta.py`
- Recovered from job-tmp originals, verified **byte-identical** to the
  server copies (sha256). The l2_amendment_2.md provenance pointer now
  resolves; the GGUF fix recipe is reproducible from the repo.

## Status for paper's L2 chapter (v1.1)

L2 Stage-1 eval **completed** 2026-07-23 (both protocols, n=100, per-arm
left-scored, `parse_fails=0`). Raw SR: A_ctrl_rat 14/100, C_retrieval
20/100. Confirmatory McNemar analysis + diagnostic pack in progress
(execution order locked by PI). **Do not draft L2 result wording yet** —
the confirmatory report + diagnostic appendix will be handed to paper
session with the verdict phrasing fixed by the pre-analysis audit log
(paper session does not re-interpret). Will file a follow-up handoff when
`l2_confirmatory_report` is ready.
