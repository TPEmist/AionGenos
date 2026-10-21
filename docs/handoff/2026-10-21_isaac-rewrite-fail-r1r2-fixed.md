# Handoff → isaac: rewrite re-audit FAIL-R1 / FAIL-R2 fixed (reply to f891b39)

**From:** paper session, 2026-10-21.

## New SHAs
- `paper-v1.1-wip` @ **`94e258c`**
- `paper-v1.1-cameraready` @ **`b94391a`**

Upload archive, rebuilt from `b94391a`: sha256 **`c0f0768b…61b3`**. The
cleaner reports "PDF text identical".

Diff from `6e44c36`: 2 files, +9/−6, prose only, no number.

| item | change |
|---|---|
| **FAIL-R1** (`methods_l2.tex`) | §5.6: "pre-specified in an analysis-adaptation dry run (`\repopath{docs/paper/l2_analysis_adaptation.md}`; its commit timestamp precedes any L2 five-protocol result)". §5.7: the first sentence now reads "This redefinition was locked before any L2 data, in `\repopath{docs/paper/l2_analysis_adaptation.md}`". The pointer sits in the body; the heading stays plain, so TMLR does not print a placeholder in a heading |
| advisory, also done | §5.1: "…not pushable objects (`\repopath{docs/paper/l2_diagnosis.md}`, Step 1)" |
| **FAIL-R2** (`results_d11.tex`, Figure 2 caption) | your suggested wording, verbatim: "Mean ± SD per arm, plotted from the per-arm summary statistics stored by the original exploratory output; per-episode values are recomputable from the replays. The σ contrast, 8–10 vs 14.4, is the reported effect." |
| draft-reference advisory | not restored; the PI can rule on it |

Both files are on `origin/master`. In the TMLR build they print as
"[path anonymised for review]"; the anon check PASSes.

## Builds
| build | result |
|---|---|
| `make bar` | gate OK, page guard 5/5 |
| `make arxiv` | gate OK |
| `make tmlr` | gate OK, TMLR anon check PASS |

An agy agent (`reviewer1`) is independently pre-checking these points; the
result goes to `/tmp/qa_fix_r1r2.md`. That check is support, not the audit.
