# Handoff → isaac: second editorial pass (PI's arXiv render 2) — re-audit before upload

**From:** paper session, 2026-10-21.

## New SHAs
- `paper-v1.1-wip` @ **`c69e85a`**
- `paper-v1.1-cameraready` @ **`67f29a6`**

Upload archive, rebuilt from `67f29a6`: sha256 **`53445496…e09c`**.

Diff from your green `94e258c`: commits `817a9a2` and `c69e85a`. Only prose,
placement, and bib note text changed.

| change | detail |
|---|---|
| bib (both copies) | Removed the descriptive `note` text: orbit2023 "; NVIDIA Isaac Lab / Isaac Sim", pistar06_2025 "RECAP: …", tmem2026 "introduces the TMEM framework". Every arXiv ID is kept, and the PI-ruled acceptance notes (EMNLP / NeurIPS-PTA / ECCV-workshop) are kept. **The workshop cites one of these 3 entries, so its reference list changes**: please re-run `bar` gate + page guard (mine: 5/5) |
| removed | the "workshop version does not report the slope readings" clause, so the A15.1 limitation ends "…though the margin is thin."; also "(report §3, §4)", which pointed at an internal report |
| repo paths and run IDs in body prose → `\footnote{}` | 12 sites. Pointers are kept; unreleased files are marked "(not released)". Two sites now point back instead of repeating the path: the second `l2_analysis_adaptation.md` reads "the same pre-specification file as §5.6", and per_arm_rescore.json reads "the per-arm re-score", whose footnote is in §5.4. The FAIL-R1 pointer at §5.6 is kept, in a footnote: "…; its commit timestamp is the pre-specification" |
| note-style | `(unexpected)` dropped. "; verified as literal, not a metaphor" dropped. "(Speculative.) If" → "More speculatively, if": the speculative label is kept, as running text. §5.4 colon phrases → sentences. §5.9.3(b) "Exploratory: n=2 tasks…" merged into the previous sentence. §6.5 "(Exploratory. We state it…)" → "We state this as an exploratory hypothesis…". "The variance (exploratory; …)" → "Variance analysis (exploratory)." Inline "collect.py" → "the evaluation loop" |
| layout | the Table 3 notes ($^1$ T3, two-tier T1, α budget, reading the CIs) moved inside the table float as a footnotesize minipage |

## Builds
| build | result |
|---|---|
| `make bar` | gate OK, page guard 5/5 |
| `make arxiv` | gate OK |
| `make tmlr` | gate OK, anon PASS |

## agy pre-checks (support, not the audit)
- **reviewer2** (`/tmp/qa_pass2_diff.md`): diff `94e258c..817a9a2`.
  - (a) No number, SHA or run ID was deleted or changed; the only digit
    dropped is the "4" in "(report §3, §4)".
  - (b) No label was removed or weakened.
  - (c) All 12 relocated `\repopath` are traceable.
  - (d) Bib: only note text changed.
- **reviewer1** (`/tmp/qa_pass2_items.md`): every review item PASS except
  inline `collect.py`, fixed in `c69e85a`. The L2 amendment-table "Anchor"
  cells still name `l2_amendment_*.md`, on purpose: they are table evidence
  anchors.

## Request
Re-audit on `67f29a6` / `c69e85a`, then go or no-go for the PI upload
before 10/22 11:00 PDT.
