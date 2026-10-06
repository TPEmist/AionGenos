# Handoff: A15 / P1 disclosure pack (for paper)

**From:** isaac session (master)
**To:** paper session
**Date:** 2026-10-05

## What
`docs/paper/a15_p1_disclosure_pack.md` is a set of numbers and labels for four
disclosures, plus a routing table. All of it is CPU-only re-analysis of on-disk
replays, logs and recaps (no sim, no servers, no `aiongenos/` edits).
Reproducible with the new read-only script
`scripts/analysis/a15_p1_autoreset_sensitivity.py`, which reuses the A14
`d11_mcnemar.py` loaders and stats unchanged.

## Key numbers (full tables + sources in the pack)
1. **24 s auto-reset (A15 pin 8).** The boundary is derived per episode from the
   step counter: `t·60` gives the counter, the reset offset is 2 in every
   episode, and the boundary is index 718 everywhere. A frozen-right-arm EE jump
   cross-checks it. 3 of 209 crossing episodes are ambiguous on the strict rule;
   all 3 are resolved by the left-EE jump.
   As-run → sensitivity SR: A_action_only 25→21, A_ctrl_rat 15→12, B_main
   26→19, D_gist 19→17, C_retrieval 49→48. D10 7-run total 233→227/700.
   D6b 22→19.
   Contrasts (z primary: A14 gate FAILED, so McNemar is sensitivity only):
   T1 +1→−2 pp (null/null), T1a +11→+7 pp (n.s./n.s.), T4 +23→+29 pp
   (sig/sig), +34→+36 pp identical-weights (sig/sig, exploratory), T3
   below the floor both ways. **No confirmatory verdict changes.**
2. **`{target_color}`.** `collect.py:622` passes the unformatted template to
   the recap prompt (`stage4_recap.py:312`). It is present since `2ce1700c`,
   before all D10 runs. 547/547 frozen-buffer `metadata.instruction` contain
   the literal. 0/547 `text_lesson` do (517/547 say "red"). Retrieval injects
   lessons, not the instruction. Disclosure only.
3. **D6 measured SR.** D6b `fa7f4571` = 22/100 (log + replays agree).
   D6 `67685984` = 21/100. Its 101st replay is a stray D4 episode
   (`run_id e227aeaa`, copied at the 06-22 a_train sync time). Measured 22%
   vs the paper's derived ≈30%. Label: "measured, not seed-paired".
4. **A15 (c).** The pinned reading is unavailable for the D11 arms. The 15 mm
   numbers are post-hoc exploratory (C_retrieval r=+0.306 above band; the
   four distilled arms are −0.156…−0.298). The teacher slope is not computable.

## What the paper needs to do
Apply the routes in pack §5. The pack gives numbers + labels only; wording is
the paper session's job within those routes. A one-line inconsistency is also
flagged: the T1 CI is [−11.1, +13.1] in text (:29) vs [−11.0, +13.0] in
Table 1 and in code.

## Territory
Analysis + pack = isaac (master). Paper prose = paper session
(`paper-v1.1-wip`). Push freeze applies: committed locally, not pushed.
