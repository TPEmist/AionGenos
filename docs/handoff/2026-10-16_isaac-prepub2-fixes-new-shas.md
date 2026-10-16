# Handoff → isaac: PREPUB #2 fixes, new SHAs for the full re-audit

**From:** paper session, 2026-10-16. Reply to `85ea8f4` (audit #2) and
`f911825` (step-5 review and the TMLR checker).

## SHAs to audit
| target | branch @ SHA | path |
|---|---|---|
| workshop camera-ready (named) | `paper-v1.1-cameraready` @ **`154f1a5`** | `docs/paper/bar/main.tex` |
| arXiv v1 (named) | `paper-v1.1-cameraready` @ **`154f1a5`** | `docs/paper/arxiv/main.tex`. **The upload archive** is built by `python3 docs/paper/arxiv_upload.py` and written to `docs/paper/arxiv_upload.tar.gz` (not committed; rebuild it from the SHA) |
| TMLR submission (anonymous) | `paper-v1.1-wip` @ **`8292c39`** | `docs/paper/arxiv/main_tmlr.tex` (new; see FAIL-6/7) |

`main_tmlr.tex` is identical on both branches; `make tmlr` passes on both.
Build: `make -C docs/paper bar | arxiv | tmlr`, with the gate first. The
generators now need `--data-root` or `$AIONGENOS_DATA_ROOT`; the Makefile
passes the data root.

## FAIL → fix (commit on wip; cameraready merges them all)
| item | fix | commit |
|---|---|---|
| FAIL-1 | New `coverage_claims()`. It certifies and gates the 21 listed literals: 109/221; 15/100 sens 12; 26/100 sens 19; 15--26; 11 pp; 547; 517/547; 0.45 cm (now also in BAR). It checks **every** pp literal in the workshop against the set of certified or pinned values. It checks the teacher reference at **every** occurrence, in any digits, across the workshop and the TMLR abstract, intro, results and discussion. It checks the lock constants −23.5 / −15.8 / 45--55 / +10 pp against `docs/d11_preregistration.md`. The σ-range and grid-unit slots now accept any digits. Your MISSED cases are all CAUGHT now: `bar:67` 49.3→48.3, 15/100 sens 12, 26/100, 517, 45--55, plus a +34 repeat, 0.45, −15.8, 11 pp and 547 | `1c7f26b` |
| FAIL-2 | Per the PI ruling, a sensitivity value now sits beside the SR at all 6 places, plus 2 more in §4.2b: TMLR abstract, §4.2 ×2, §4.2b (and "48--55 / 15--26"), §6.1, workshop abstract. Every value is a gate literal rebuilt from `derived_stats.txt`, which reads `autoreset_sensitivity.json` / `a15_ab_stats.json`. Page guard: 5/5 | `1c7f26b` |
| FAIL-3 | (a)/(b) are tagged "confirmatory for the Amendment 15 prediction"; TMLR adds "α = 0.05 is a disclosed choice". (c) is tagged "descriptive, non-inferential" in both versions | `dfccccd` |
| FAIL-4 | `discussion.tex:216–222`: the item title becomes "The marginal/conditional split on a second task (direction-consistent, post hoc)"; "corroborates" becomes "is consistent with"; "replicates" becomes "points the same way … which is not a replication". `results_d11:251` "localises" becomes "points to … (exploratory)". `discussion:157` and `bar:294`: "localising" becomes "points to". Also synced in `methods_l2:303,364`, which had the same wording | `dfccccd` |
| FAIL-5 | voyager2023 and dinov2_2023 → TMLR 2024, verified on jmlr.org/tmlr/papers by curl. awm2024 → ICML 2025, PMLR 267:63897–63911, verified on proceedings.mlr.press. lora2021 → ICLR 2022 and memmel2024strap → ICLR 2025: **agent-verified only**, because OpenReview's challenge blocked me; the agy raw text is in `/tmp/agy_fail5_raw_*.txt`. Every changed entry keeps its arXiv ID as a note. Recorded in `bib_verification.md` | `f710141` |
| FAIL-6 | `main_tmlr.tex` uses the official `tmlr.sty` / `tmlr.bst` / `fancyhdr.sty` from JmlrOrg commit `7bf90ef`, unmodified; `tmlr.sty` md5 `e302463e…` equals your value. It builds in submission mode ("Anonymous authors / Paper under double-blind review"); provenance is in `arxiv/TMLR_STYLE_SOURCE.md`. arXiv keeps its own layout | `8292c39` |
| FAIL-7 | The `\anonymised` switch (`arxiv/anon.tex`) works as follows. 21 commit SHAs become `\commit{}` (including the all-digit `0398568`, which your category-5 regex would not flag). 11 repo paths become `\repopath{}`; the TMLR build prints "[commit anonymised for review]" / "[path anonymised for review]". The availability section gives no link in TMLR ("…will be released with the camera-ready"). The one "workshop version" mention is hidden in TMLR. The PDF metadata is empty. `make tmlr` runs your `tmlr_anon_check.sh`: **6 categories 0 hits, metadata 0, sty md5 = official → PASS**. The certificates still bind to the source SHAs (`shas_resolve` reads `\commit{…}`). Per the PI, please record the F1 route and its reason, with the TMLR policy URL, in the report | `8292c39` |
| FAIL-8 | `docs/paper/arxiv_upload.py` builds the arXiv archive from `main.tex`, `anon.tex`, the input sections, the .bbl, the .bib with comment lines dropped, and the 3 used figures, with **all comments stripped**. It rebuilds the cleaned tree and exits unless the PDF text equals the gated build's. On cameraready `154f1a5`: OK, 12 tex files, 0 comments left; "permission/NRCA/granted/clearance" gives 0 hits in the archive. The stale CORAL comment in `main.tex` is replaced | `8292c39` |
| FAIL-9 (text) | New `sections/availability.tex`. The named version gives the repo URL, the release tag `paper-v1-artifacts`, and an explicit "**not released**" for `logs/`, `workspace/`, `exploratory.json`, `per_arm_rescore.json` and `training_meta.json`. The workshop Reproducibility paragraph now names `https://github.com/TPEmist/AionGenos` and the release tag (page guard 5/5). The push itself is the PI's (release-step5-clean) | `8292c39` |
| FAIL-10 | The `[McNemar sens …]` lines are certified and asserted equal to the pin-8 file; the `[T3 sens]` z is certified. The main-row McNemar lines are also certified (redundant with WRAP, harmless). Rule: exact if b+c<25, else cc-χ². `mcnemar_table()` gates the column and the T3 sens z | `6262f8a` |
| S-1 | `--data-root` is required or read from `$AIONGENOS_DATA_ROOT` in both generators and in `check.py`; the outputs are byte-identical. Your re-review: PASS | `ca7ccde` (wip); `1ec45af` → `2577d70` (clean) |
| PI | `birth_certificate_audit.md` row: A15 (b) B_main z=3.91 (3.9055; your 3.90 erratum, `7424bf1`) | `ca7ccde` |

**Negative tests.** Every new check was mutated and restored; all CAUGHT,
md5 restored. Three of my sed restores damaged a file: `&` in a
replacement, `^` in a replacement, and `\n`. The md5 check caught all
three; they were repaired by exact-string replacement and re-verified.
From now on I use exact-string Python mutation.

## PI-open
- **F2:** the PI confirmed on 2026-10-15 that "Nikon Research Corporation of
  America" is the exact affiliation string in the permission. Please record
  F2 PASS (PI).
- **E6:** the arXiv ID comes after the upload.
- **H4:** the PI traces the abstract numbers.

## Audit context: a second file from the 14:46:42 overwrite
`paper-v1.1-cameraready` also had `docs/paper/bar/main.tex` overwritten at
**14:46:42.851**. The working tree had the R1 slope caption back, i.e. the
pre-`acfd91d` content. No commit was changed; your audit of `fab376a` read
committed content. I saved the diff to `/tmp/cameraready_stale_worktree_1446.patch`
and restored the file to HEAD before merging. That makes 5 files at the same
second across 2 worktrees, plus the untracked copies in AionGenos-publish.

## Release
- Noted: `release-step5` is void.
- Any later release edit goes on `release-step5-clean` (`2577d70`).
- My worktree `/home/control/AionGenos-step5` is still on the void branch;
  I will not commit there.
