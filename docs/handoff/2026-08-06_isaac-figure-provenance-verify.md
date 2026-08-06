# Handoff: figure provenance cross-check (B10) — for isaac awareness/confirmation

**From:** paper session
**To:** isaac session (owns the data dir + replay/config source)
**Date:** 2026-08-06

## What this is
The v1.1 PDF review flagged a cross-territory verification (B10): confirm
the qualitative figure's caption numbers against the actual collect config
and replay data. The paper session **already verified these against the
committed data** (read-only); this handoff records the result and asks
isaac to confirm nothing is stale on the data side.

## Verified (paper session, against committed source)
Termination criteria in the figure caption vs `aiongenos/config.py`:
- max_subgoals_per_episode = **40** ✓
- subgoal_success_threshold_m = **0.05** ✓
- plateau_patience = **5** ✓

3-panel episode final EE→target distances vs replay `trajectory`:
| arm | run/episode | start→final | outcome |
|---|---|---|---|
| A_ctrl_rat | 56ee684b / e6f690d6-775 | 20.3→13.2 cm | timeout (plateau) |
| B_main | a7b11544 / 16e50879-8d4 | 20.1→19.0 cm (min 8.4) | timeout (plateau) |
| C_retrieval | 09817322 / e1837c00-399 | 19.2→4.3 cm | success |

All match the figure. SHAs recorded in
`AionGenos-paper/docs/paper/arxiv/figs/MANIFEST.md`.

## Two items for isaac (optional / awareness)
1. **C_retrieval success episode carries `near_singularity` ×12 flags** — it
   reached target through near-singular arm configs. Paper notes this in the
   manifest (provenance honesty); flagging in case isaac wants a
   cleaner exemplar substituted (not required — the reach/timeout claim holds).
2. **Figure 2 (R1 mechanism) is mean±SD, not a violin**, because
   `exploratory.json` stores per-arm summary stats only, not raw
   per-episode R1 ΔX. If isaac can re-extract raw round-1 ΔX per episode
   from the replays, the paper session will swap in a true violin (mechanism
   reads identically). Low priority — current figure is faithful to the
   data on disk.

No action strictly required; this is a provenance-confirmation record.
Push freeze still in effect (nothing pushed pending company clearance).
