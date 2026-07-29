# Diagnostic 4c — paired rescue analysis: PREDICTION (pre-registered)

**Timestamp intent: written and committed BEFORE the 4c script runs.**

**Filed:** 2026-07-28 (isaac session, master), under the locked
"not-significant → DIAGNOSE" branch. Third and last diagnostic.

## What 4c measures

The discordant episodes that constitute the entire +6pp:
- **rescue** (C_retrieval ✓, A_ctrl_rat ✗): **9 episodes** — where the
  retrieval preamble flipped a failure to a success.
- **regression** (A_ctrl_rat ✓, C_retrieval ✗): **3 episodes** — where it
  flipped a success to a failure.
- net = 9 − 3 = +6 (matches the SR delta exactly).
- (both-success = 11; both-fail = 77.)

For each rescue (and regression) episode: the **init-pose profile** —
init left-EE pose, init distance-to-red-cube (dist_red), the round-1 ΔX_L
before/after, and the retrieved neighbours' similarity for that episode.
Ep_idx / seeds already identified (rescue: 13,24,30,42,57,60,78,92,93;
regression: 9,50,74).

## The puzzle 4c must address (handed up from 4b)

4b showed retrieval restores the round-1 bias magnitude on ~all episodes
(mean −4.8 → −17.2 ≈ teacher −17.1), yet only **9 net** episodes convert
to success. So R1 correction is nearly universal but success conversion is
sparse. 4c asks: **what distinguishes the 9 that converted?**

## Pre-registered predictions (both directions interpretable)

1. **If the rescue episodes share an init-pose signature** (e.g. cluster
   in init dist_red, or in init left-EE region — a "retrieval helps most
   when starting from configuration X" pattern):
   → retrieval's value is **conditional on start state** — it rescues a
   specific, identifiable slice of the state space. This is a positive,
   reportable structure (and would echo the conditional-correction story).

2. **If the rescue episodes look like a random draw** from the failure set
   (no init-pose clustering, similarity indistinguishable from
   non-rescued failures):
   → the +6pp is better read as **diffuse / near-threshold noise**: R1
   correction nudges many episodes, and 9 happened to cross the 0.05m gate
   while 3 fell back. Consistent with the n.s. confirmatory result and the
   [−4.5,+16.4]pp CI. This would be the honest "small, diffuse, sub-MDE
   effect" reading — NOT a clean conditional-rescue story.

3. **Retrieved-similarity check on rescues:** do the 9 rescue episodes
   have *higher* retrieval similarity than the failure set at large?
   - Higher → rescues came from better-matched memory (ties 4c to 4a).
   - Not higher → rescue is not explained by retrieval match quality
     (points back to noise / threshold effects).

## Expectation stated honestly (so a null can't be reframed)

Given the confirmatory n.s. and 4b's near-universal R1 correction, I
expect **branch 2 is more likely than branch 1** — the +6pp probably reads
as a small diffuse effect rather than a crisp state-conditioned rescue.
Recording this expectation so that IF branch 1 fires (clear clustering) it
is a genuine surprise worth foregrounding, and if branch 2 fires it is the
predicted, unspun outcome. n=9 rescues is tiny; any clustering claim needs
to survive that the sample is 9 points.

## Red-line (PRE_ANALYSIS_LOCK.md §c)

4c closes the diagnostic pack. Only after 4a+4b+4c together may the report
write its mechanism sentence. 4c with n=9 cannot carry an attribution
alone; its job is to say whether the +6pp is state-structured or diffuse,
feeding the combined narrative. Exploratory throughout.
