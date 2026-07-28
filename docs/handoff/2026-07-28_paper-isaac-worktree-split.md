# Handoff: paper/isaac worktree split + L2 GGUF fix relocated to master

**From:** paper session (v1.1 writing)
**To:** isaac session (L2 pipeline & eval)
**Date:** 2026-07-28

## What happened (why master moved once)

The L2 GGUF-export fix commit `ae75ada` had accidentally landed on the
`paper-v1.1-wip` branch (the working tree was left on the paper branch
after v1.1 was opened, so isaac-territory work got committed onto the
paper branch — the "one working tree, two hands" accident). This was
untangled:

- `ae75ada` was **cherry-picked onto master** as `154e974` (verified
  reachable). The GGUF fix + the `run_l2_stage1_pipeline.sh` changes +
  `train_shas.txt` + the l2_amendment_2.md 2026-07-21 addendum are all
  **present on master now**.
- `paper-v1.1-wip` was reset to `134086d` (paper §5.3 only, no L2
  engineering files).
- A dedicated worktree was created for paper writing:
  `/home/control/AionGenos-paper` → `paper-v1.1-wip`.

## Territory boundary (physical, from now on)

| worktree | branch | owner | touches |
|---|---|---|---|
| `/home/control/AionGenos` | master | **isaac** | L2 pipeline, eval, servers |
| `/home/control/AionGenos-paper` | paper-v1.1-wip | **paper** | `docs/paper/` only |

**isaac: pull the L2 line from master (154e974) — the GGUF fix is there.**
This was the one authorized master write by the paper session; the paper
session's territory is now `/home/control/AionGenos-paper` exclusively.

## ⚠️ One gap for isaac to close (NOT a cherry-pick miss)

`docs/paper/l2_amendment_2.md` (2026-07-21 addendum) references
`server_side/gguf_tools/README.md` (+ `patch_arch`, `read_gguf_meta`) as
"full recipe". **That directory was never committed and is not on disk.**
It was only *named* in the addendum text, not added to version control by
`ae75ada`. The untangle did not drop it — it never existed in any commit.
isaac should recover/commit `server_side/gguf_tools/` (the stock converter
+ arch byte-patch tooling) so the addendum's provenance pointer resolves,
or the GGUF fix recipe is documented-but-not-reproducible.
