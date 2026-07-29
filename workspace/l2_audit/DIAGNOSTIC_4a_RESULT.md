# Diagnostic 4a — retrieval-quality audit: RESULT

**Filed:** 2026-07-28, AFTER the pre-registered prediction
(`DIAGNOSTIC_4a_PREDICTION.md`, commit `7c06923`). Raw output:
`DIAGNOSTIC_4a_output.txt`.

## Numbers

Retrieval similarity (retriever α-weighted score, img_w=0.4; identical
config both runs), n=100 episodes each:

| metric | L0a (buffer 547) | L2 (buffer 100 / ~28 usable) | L0a − L2 |
|---|---|---|---|
| top-1 median | 0.900 | 0.870 | **+0.030** |
| top-1 mean   | 0.902 | 0.865 | +0.037 |
| top-3-mean median | 0.883 | 0.827 | **+0.057** |
| top-1 IQR | [0.890, 0.920] | [0.850, 0.880] | shifted down |
| top-1 min | 0.830 | 0.730 | L2 has a low tail |

Location tests (Mann-Whitney U, two-sided):
- top-1: z=8.39, **p=4.7e-17**
- top-3-mean: z=10.7, **p=1.3e-26**

Histogram: L0a top-1 concentrates at 0.85–0.90 (48/48 split); L2 shifts
down to 0.80–0.85 (29/61) with a low tail (0.70–0.75) that L0a has none of.

## Verdict against the pre-registered branches

**Branch 1 fired: L2 retrieval similarity is systematically LOWER than
L0a** (both metrics, clearly separated distributions, overwhelming
location significance). Per the locked interpretation, the **"attenuation
∝ buffer coverage" hypothesis gains quantitative support**: the ~5.5×
smaller L2 buffer retrieves systematically more-distant neighbours.

Extra structure (not pre-registered, flagged exploratory): the top-3 gap
(+0.057) exceeds the top-1 gap (+0.030) — L2's 2nd/3rd neighbours fall off
faster than L0a's, consistent with a thin buffer having only a few
close matches and padding the rest from farther away. This *strengthens*
the coverage reading but is a post-hoc observation.

## Red-line held (PRE_ANALYSIS_LOCK.md §c)

This does NOT close the attribution. 4a establishes that L2 retrieves
worse-matched neighbours — a necessary-but-not-sufficient account. Two
things it does NOT show, deferred to 4b/4c:
1. Whether a *closer* neighbour would even help — a high-cosine match to a
   near-failing recap is still a poor lesson (memory-success-floor). The
   similarity metric is visual, not task-relevance.
2. Whether the +6pp that DID materialise came from the better-matched
   episodes (4c rescue analysis) or is noise.

So 4a's contribution to the final writeup: **"retrieval quality degraded
measurably on L2 (top-1 0.90→0.87, top-3 0.88→0.83, both p≪1e-10),
consistent with the 5.5× thinner buffer"** — a diagnostic fact, not yet
the sole-cause sentence.
