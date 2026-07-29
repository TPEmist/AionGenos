# Diagnostic 4c — paired rescue analysis: RESULT

**Filed:** 2026-07-28, AFTER the pre-registered prediction
(`DIAGNOSTIC_4c_PREDICTION.md`, commit `28f7c9c`). Raw output:
`DIAGNOSTIC_4c_output.txt`.

## Cells (the entire +6pp)

rescue (C✓A✗) = 9 | regression (A✓C✗) = 3 | both-fail = 77 | both-succ = 11.
net = 9 − 3 = +6, matches the SR delta.

## Verdict against the pre-registered branches

**Branch 1 fired — and it is a genuine surprise (I had recorded branch 2
as more likely).** The rescue episodes share a sharp init-pose signature:

| group | init dist_red (cm) | | 
|---|---|---|
| **rescue** (n=9) | mean 13.9, median 14.2, range [8.0, 20.4] | |
| **both-fail** (n=77) | mean 21.6, median 21.8, range [11.4, 32.5] | |
| Mann-Whitney | **z=−3.88, p=1.0e-4** | rescues start much closer |

Retrieval rescues almost exclusively episodes that **start close to the
target** (init dist_red < ~20cm). Far-start failures (>20cm) are not
rescued — the entire rescue set sits in the near-start slice.

**Branch 3 turned out NEGATIVE (and informative):** rescue episodes'
retrieval similarity is *not* higher — it is slightly LOWER than the
failure set (top-1 rescue 0.847 vs both-fail 0.868, MW z=−2.16 p=0.03).
So rescue is **not** explained by better-matched memory. The decisive
variable is start distance, not retrieval match quality.

## How this resolves 4b's puzzle

4b: retrieval restores the round-1 bias magnitude on ~all episodes
(−4.8 → −17.2 ≈ teacher −17.1). 4c: yet only the near-start episodes
convert. The synthesis:

**The retrieved conditional correction is a single-step R1 bias fix. It
converts to success only where the start is already within reach of the
0.05m gate after that one corrected step. Far-start episodes need
multi-step navigation competence that a one-shot R1 lesson does not
supply — so the correction fires (4b) but does not cross the goal gate
(4c).** This is the L2 face of the memory-success-floor / minimum-viable-
competence law: memory conditions the correction, but cannot manufacture
the task competence to execute it from far away.

## Cross-diagnostic synthesis (4a + 4b + 4c — the pack is now closed)

- **4a:** L2 retrieval quality degraded but functional (top-1 0.90→0.87);
  the 5.5× thinner buffer retrieves farther neighbours.
- **4b:** despite that, retrieval still restores the teacher's R1 bias
  magnitude on ~all episodes (mechanism channel intact).
- **4c:** the correction converts to success only in the near-start slice
  (9 rescues, dist_red p=1e-4), independent of per-episode retrieval
  similarity.

Combined, licensed mechanism sentence (now permitted, red-line lifted):
**the identical-weights retrieval effect DOES replicate on L2 in
mechanism (R1 correction) and in direction (+6pp), but its conversion to
end-task success is gated by task competence — it rescues only episodes
already near the goal, so the effect is small (+6pp, n.s.) rather than
absent.** Retrieval supplies the conditional correction; it does not
supply the multi-step competence to cash it in from far configurations.

## Red-line status

LIFTED for the combined narrative only. n=9 rescues is tiny; the
init-distance separation (p=1e-4) is strong for that n but every
downstream sentence keeps the exploratory label and the n=9 caveat. The
confirmatory verdict (n.s., +6pp, CI [−4.5,+16.4]) is unchanged — 4c
explains the smallness, it does not upgrade the significance.

## Note on the honest-expectation record

The 4c prediction stated branch 2 (diffuse noise) as more likely than
branch 1 (state clustering). Branch 1 fired instead — a real surprise,
foregrounded as such per the pre-registration's own instruction. The
value of recording the expectation: this clustering cannot now be
dismissed as a result I was fishing for.
