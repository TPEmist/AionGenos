# Spec — prose-layer re-audit of the editorial rewrite (arXiv/TMLR sections)

Lead: isaac. Date 2026-10-21. Protocol: PREPUB_AUDIT v1.1 sections A (numbers), C (labels), D (scope).

## What changed
The paper session rewrote 8 section files (+ availability.tex in c75af6d) of the arXiv/TMLR paper
for style ("remove AI-writing traces"). The author claims: NO number / statistic / claim / scope /
label / citation / SHA / \repopath / \commit / \label / \ref change, except one deliberate label fix
in results_d11.tex §4.3 (σ paragraph: "μ-based branch selection ... confirmatory" → "exploratory under
the analysis lock, Amendment 14 §14.5").
Do NOT trust that claim. Your job is to find every place where the rewrite changed MEANING.

## Inputs (all read-only)
- Old version = commit 7bdb057; new version = commit 720772b.
- Read-only checkouts: OLD = /home/control/audit/7bdb057/docs/paper/arxiv/sections/
                       NEW = /home/control/AionGenos-cameraready/docs/paper/arxiv/sections/
- Word diffs (`[-old-]{+new+}`): /home/control/audit/rewrite_720772b/diffs/<file>.wdiff ; line diffs <file>.diff
- Sources for checking labels/claims: /home/control/AionGenos-cameraready/docs/paper/ (l2_amendment_*.md,
  l2_prereg.md, l2_confirmatory_report.md, l2_analysis_adaptation.md, a15_ab_results.md, birth_certificates/,
  arxiv/sections/appendix_amendments.tex for Amendment 14 §14.5 = analysis lock).

## For every changed sentence, check
1. NUMBERS (A): any number added, removed, or changed (incl. %, pp, n, z, p, cm, ×, counts, dates, SHAs). Rounding changes count.
2. LABELS (C1–C5): every result keeps exactly its old label (confirmatory / exploratory / post-hoc / descriptive / non-inferential);
   a former status tag ([CONFIRMATORY], [EXPLORATORY…], MISS/HIT, [null]) must now be prose carrying the SAME label and the SAME
   met/not-met outcome. Exploratory results must not gain confirmatory voice ("shows", "establishes", "demonstrates", "replicates",
   "confirms"). n.s. results must not read as "trend"/"replicates". "not found" must not become "ruled out" (withdraw ≠ refute).
3. SCOPE (D2): every qualifier at "cannot"/"does not"/"no effect" (recipe, task, data scale, capacity, interface paradigm,
   "in this setting", "at this n") still present. A dropped hedge or a dropped "post hoc" = FAIL.
4. NAMING (D1): task names follow the amendment naming rule (pose-reach / position reach, NOT push; reach, NOT manipulation).
5. CAPTIONS (D4): captions still disclose quantities not plotted and data limits.
6. NEW FACTS: any assertion present in NEW but not in OLD (e.g. "round 1 reproduces the original exploratory output exactly",
   "per-episode values are recomputable from the replays") — name the file on disk that supports it, or mark UNSOURCED.
7. DROPPED CONTENT: any caveat, limitation, disclosure, or condition present in OLD but absent in NEW.
8. Citations, \ref, \label, \commit, \repopath, footnotes: any added/removed/changed.

## May / may not
- MAY: read any file; run read-only commands (git show/diff/grep, python reading files).
- MAY NOT: edit, create, or delete any file except your own output file; no git commit/checkout/switch/stash/push;
  no builds (`make`) — the lead runs builds; no kill.

## Output
Write `/home/control/audit/rewrite_720772b/review_<yourname>.md`:
- Table: `| severity (FAIL/WARN/OK-note) | file:line (NEW) | check # | OLD text (quote) | NEW text (quote) | why |`
  List ONLY FAIL and WARN rows, plus at most 5 OK-notes for the riskiest changes you cleared.
- Then a line `Coverage: <files> reviewed fully, <N> hunks read`.
- FAIL = meaning/number/label/scope changed or new unsourced fact. WARN = arguable, needs lead judgment.
Reply with only: output path + one line `FAIL=<n> WARN=<n>`.
