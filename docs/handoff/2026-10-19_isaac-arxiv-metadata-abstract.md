# Handoff → isaac: arXiv metadata abstract (≤1920 characters)

**From:** paper session, 2026-10-19.

**File:** `workspace/release/arxiv_abstract_metadata.txt`
- 1895 characters, excluding the trailing newline;
- pure ASCII;
- sha256 `3c125ac1…7946`.

It is a cut of `arxiv_abstract_fullplain.txt` (2334 characters). The PDF
abstract is unchanged.

## Checks (scripted against the full plain text)
- Every number in the metadata text appears in the full abstract, and none
  was dropped. All of these are kept: +1 pp, +34 pp (z=5.15), 49.3%, +23 pp
  (z=3.36), +36 / +29 pp, 48% (sens 48%), 19–26% → 53–55% (sens 17–21% →
  50–55%), +6 pp, CI [−4.5, +16.4].
- No new words, except the inflection "transfers" → "transferring".
- C5 is kept: "we withdraw - rather than refute - the memory-in-weights claim".
- Sensitivity stays beside every SR (+36/+29; 48%; 17–21% → 50–55%).
- Labels are kept: "pre-registered", "registered before they ran", "An
  exploratory behavioural probe with pre-registered per-arm predictions",
  "exploratory diagnostics".

## Edits (deletions and rewordings only)
1. Removed "accumulated", "We test this directly.", "single-arm", "only"
   (in "by only +1 pp") and "By contrast,".
2. Removed "— a clean parametric-vs-contextual-memory contrast on identical
   weights" and "Because the headline result is a null,".
3. Removed "(a static prior every arm adopts)".
4. Reworded "is consistent with a mechanism: behavioural distillation transfers"
   → "is consistent with behavioural distillation transferring".
5. Reworded "prompt-retrieved memory supplies" → "retrieval supplies".
6. Removed "each of", "so the retrieval effect does not depend on the
   adapter," and "in the same family".
7. Removed the closing "and a distance-gated conversion threshold,
   suggesting the effect scales with the amount of retrievable success
   experience".
8. Unicode dashes became ASCII ("-" for — / – / −).
