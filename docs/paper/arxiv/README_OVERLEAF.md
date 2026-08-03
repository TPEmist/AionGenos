# Overleaf build + submission handoff (v1.1 → TMLR/arXiv)

This `arxiv/` dir is the LaTeX assembly of the v1.1 manuscript. No LaTeX
toolchain on the build box, so **compile on Overleaf**. This README is the
division of labour: what the paper session did, and the human steps left.

## Structure
```
arxiv/
  main.tex                 # preamble + author block + \input list + bib
  refs.bib                 # STUB — bib pass needed (see below)
  README_OVERLEAF.md       # this file
  sections/
    abstract.tex           # done (headline, verbatim + L2 sentence)
    intro.tex              # done (headline, verbatim)
    methods_d11.tex        # md→tex (agent)
    methods_l2.tex         # md→tex (agent) — holds L2 §4 Methods + §5 Results + §6 Discussion
    results_d11.tex        # md→tex (agent)
    results_l2.tex         # (see note: L2 results are inside methods_l2.tex; main.tex \input may need adjusting)
    discussion.tex         # md→tex (agent)
    related_work.tex       # done (verbatim; [cite] markers → bib TODO)
    appendix_amendments.tex# pointer stub
    appendix_teacher_provenance.tex # md→tex (agent)
```

## What I (paper session) can / cannot do
**Can (done or doable here):** assemble all `.tex` sources, convert every
markdown section verbatim, author block, section scaffolding, cover
letter, git tag, push branch+tag to origin (submission decision landed →
remote unblocked).

**Cannot (human steps — need Overleaf login / OpenReview / arXiv account):**
1. **Compile + visual proof** on Overleaf (catch overfull boxes, table
   overflow, missing glyphs).
2. **TMLR style swap:** replace the fallback preamble with official
   `tmlr.sty` (`\usepackage[preprint]{tmlr}` for arXiv; plain for
   camera-ready). See main.tex header.
3. **Author affiliation confirm** — main.tex flags it UNCONFIRMED
   (nikon.com domain → "Nikon Corporation" guessed; confirm + check corp
   sign-off).
4. **Bib pass** — refs.bib is a stub; convert every `\tmlrnote{[cite]}` in
   related_work.tex (and the ASPIRE/Titans/J-Space names in discussion) to
   real entries + `\citep{}`.
5. **Section renumber (T-INT)** — the drafts keep explicit draft numbers
   via starred sections; at integration decide the merged scheme (L2 →
   Experiment 2 own section; see ../v1.1_notes.md INTEGRATION ITEMS).
6. **arXiv upload** (needs arXiv account) and **TMLR OpenReview submission**
   (needs OpenReview login; both author emails registered — pick submitting
   identity).

## Pre-submission checklist (before arXiv upload)
- [ ] Author affiliation confirmed (main.tex)
- [ ] tmlr.sty swapped in (main.tex header)
- [ ] refs.bib filled; zero `[cite]` / `\tmlrnote` markers remain in body
- [ ] section numbering resolved (T-INT); cross-refs (§x.y) verified
- [ ] intro contribution-list vs L2 abstract sentence reconciled (intro.tex flag)
- [ ] compiles clean on Overleaf, no overfull-hbox on tables
- [ ] cover letter finalised (TMLR version, see ../cover_letter_skeletons.md)
