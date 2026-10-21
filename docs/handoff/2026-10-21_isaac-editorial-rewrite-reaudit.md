# Handoff → isaac: editorial rewrite of the full paper — re-audit before arXiv

**From:** paper session, 2026-10-21.

## New SHAs
| branch | SHA |
|---|---|
| `paper-v1.1-wip` | **`6e44c36`** |
| `paper-v1.1-cameraready` | **`720772b`** |

Upload archive, rebuilt from `720772b`: `docs/paper/arxiv_upload.tar.gz`,
sha256 `c85a5727…dd05`. The cleaner reports "PDF text identical", and the
archive has 0 hits for permission / NRCA / granted.

## Why
The PI read the arXiv pdflatex render (`submit/8260461`, not submitted) and
asked for AI-writing traces to be removed. The traces:
- writer-instruction leaks in §5 ("The paper must not let…", "wording is
  fixed as…", "Methods sentence … is in l2_amendment_2.md", "(one-line
  paper limitation)");
- draft self-references ("earlier draft…");
- internal-notes prose;
- test-output status tags (`[CONFIRMATORY]`, MISS/HIT);
- telegraphic arrows and caps;
- a post-mortem-style appendix;
- em-dash and "not X but Y" density.

## Scope
| part | change |
|---|---|
| sections changed | `arxiv/sections/{intro,related_work,methods_d11,results_d11,methods_l2,discussion,appendix_amendments,appendix_teacher_provenance}.tex` (8 files, +635/−637) |
| unchanged | `abstract.tex` (the arXiv metadata abstract `3c125ac1` still applies), `availability.tex`, `bar/main.tex` (workshop prose untouched; it merges only these section files, and its gate and page guard are 5/5) |
| method | four editors in separate worktrees, one per file group. Rules: no number / statistic / claim / scope / label / citation / SHA / `\repopath` / `\commit` / `\label` / `\ref` change; the gate must pass. I reviewed every word-diff, focusing on label-bearing lines |
| gate | `make arxiv` / `make tmlr` / `make bar` all OK; TMLR anon check PASS; no protected literal needed restoring |

## Items that need your eye (the only changes not purely stylistic)
1. **A label correction (FAIL-class, not style).** `results_d11.tex` §4.3,
   σ paragraph.
   - It said "whereas the μ-based branch selection above is
     **confirmatory**". That contradicts the analysis lock (A14 §14.5:
     probe exploratory) and the section's own label.
   - It now reads: "…tests pre-registered per-arm predictions (itself
     exploratory under the analysis lock, Amendment 14 §14.5)".
   - This is a leftover from the R1 relabel; no other occurrence exists in
     arxiv/ or bar/.
2. **Status tags → prose.** Every former `[CONFIRMATORY]` / `[EXPLORATORY…]`
   / MISS / HIT / `[null]` is now a sentence carrying the same label:
   - T1 / T4 / T3: "…is confirmatory";
   - §4.3 / §4.4 / §4.4b / rounds 2–3: "exploratory" (rounds 2–3:
     "exploratory, 2026-10 post-hoc");
   - A15 (a): "confirmatory … the registered prediction was not met";
   - A15 (b): "… met for all three adapters (3/3)".

   Please re-run your C1 scan.
3. **Draft self-references removed** (3, in §4).
   - The rounds-2–3 table caption now reads "All rounds are a 2026-10
     post-hoc recomputation from the persisted replays…; round 1
     reproduces the original exploratory output exactly". The note about
     unsourced earlier values is gone.
   - The Figure 2 caption: "Mean ± SD per arm; per-episode values are
     recomputable from the replays".
4. **§5 naming paragraph** is now statements about the task rather than
   writer instructions: position-only success; "6-DoF" carries no rotational
   success dimension; "a second, harder task in the same primitive family,
   not a push and not a different skill".
5. **New pointer.** `\repopath{docs/paper/l2_memory_world_asymmetry.md}`
   replaces a bare filename. The file is on `origin/master`; in TMLR it
   prints as "[path anonymised for review]".
6. **Appendix "Teacher configuration (D10/L0a and L2 collects)"** is
   rewritten as a standard appendix.
   - The run-table summary is now a 2-row table with the same values.
   - "L2 (dual-push)" is now "L2 (dual-arm position reach)".
7. **Layout.** Two more margin overflows are fixed with `\allowbreak` only:
   the LoRA module list on p5 and `left_reached` in §5.

## Request
Please re-audit the prose layer for:
- claims / scope;
- labels (C-section);
- D-scope;
- that no new number appears;
- the gate negative-test spot checks you choose.

When it is green, the PI uploads the new archive to the same arXiv draft,
replacing the files, before 10/22 11:00 PDT, so the ID is assigned the same
day.
