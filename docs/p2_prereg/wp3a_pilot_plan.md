# WP1-③a push — pre-freeze pilot plan (pre-registered BEFORE any pilot episode)

**Filed**: 2026-10-05, before step (a) runs. PI ruling (chat, 2026-10-05).
**Supersedes**: the rung trigger in `rung1_smoke_criterion.md`. The rung
ladder is NOT retired — only its trigger moves. The no-memory 10-ep smoke
is pipeline feasibility; SR there carries no rung-language signal (see its
CORRECTION). Per §3a P-MVC-teacher, the ladder's correct trigger is the
**memory-ON pilot**: if the teacher cannot get successes even with memory,
gen-0 cannot start.

## Order (no step skipped, no reordering)

**(a) Human-eye gate — PI's, not mine.** 3 episodes on the current
geometry; fine-frame GIFs (forward push, approach, cube slide, handover
moment) delivered to the PI with what to look at. I do not judge them.
Pass = PI says pass.

**(b) Cube spawn is a REGION, not a point — Pin-4b.** A single cube pose
leaves only the goal's 2D as situation space — too thin for r. Cube is
sampled in a small region outside the standby-hand keep-out
(x 0.38–0.42, y 0.05–0.15, base frame); the goal is sampled RELATIVE to
the cube so push direction and distance vary per episode while staying
forward-dominant. Pin-4b is recorded in `wp3a_push_provenance.md` with
evidence: hand_map measured clearance over the whole region, fwd_gate
10/10, reset drift / nondeterminism, push-angle and cube→goal distance
distributions. If (b) changes the geometry, (a) is re-shown on the new
geometry.

**(c) Pilot collect — memory ON, 50 episodes, all tagged `pilot`.**
recap → buffer → retrieval active. Pilot data are NOT gen-0 and NOT
confirmatory; stored separately for exploratory use. Three outputs:
1. Teacher-with-memory SR and success count (the MVC floor reading).
2. Q7 check: recap on push actually produces lessons (count, non-empty,
   push-specific content — sampled verbatim into the report).
3. r-estimator variance on this task: `p2_r_tracker` on the pilot's
   round-1 correction vs situation (r, permutation band, bootstrap σ).

**Rung ladder (mechanical, thresholds fixed now) — REVISED 2026-10-05 (PI
ruling; supersedes the text-hint / PUSH_TO ladder above, before any pilot
episode).** Rungs are OBSERVATION scaffolds, each a disclosed oracle with a
measurement cost (D6b convention); the action language (TCP target + optional
base-axis ORI) is the same at every rung:
- **rung-1 (default)** = image + proprioception only (TCP / right EE /
  gripper). No object coordinates, no distances. Retrieval key = image
  embedding + proprioception.
- **rung-1b** = rung-1 + a depth image and/or a second-viewpoint camera
  (the original design spec names RGB/Depth). These are SENSORS a real robot
  has, not oracles. Re-ordered in 2026-10-05 (PI, before any pilot episode):
  widening disclosure exhausts what the BODY can sense before adding what the
  body should not know.
- **rung-2** = rung-1b + scalar distances TCP→cube, cube→goal (the P1 L0a
  condition, `prompts.py _S1_POS_HEAD`).
- **rung-3** = rung-2 + cube/goal grid coordinates and vectors.
- Ladder order (mechanical): 1 → 1b → 2 → 3.
- pilot (50 ep, memory ON) successes **< 5** at a rung → the next rung in the order above; re-run
  (c) at the new rung. rung-3 successes **< 5** → stop; escalate to PI (task
  change; no rung-4).
- **Amended by the PI on 2026-10-07: rung-3 is NOT mechanical.** If rung-2 has
  < 5 successes, STOP and report to the PI for re-deliberation.
  - rung-3 (coordinate disclosure) is a last resort under the A-spec founding
    intent.
  - Activating it needs explicit PI consent, recorded in the Ledger
    (`dual_collect_equivalence_ledger.md`) before the run.
  - The 1 → 1b → 2 steps stay mechanical.
- **Amendment (PI, 2026-10-15): per-round feedback, rung-2′.** This is an
  interface bug fix, not a new rung.
  - Push rounds had been stateless. The teacher never saw its previous target
    or the result of its last move. P1's L0 collect gave both.
  - Fix: round r ≥ 2 carries the previous round's report in P1 format:
    `DIAGNOSTIC REPORT FOR PREVIOUS ROUND` with the predicted target and the
    TCP "from → to".
    - At rung ≥ 2 it also carries the two distances, before → after.
    - Below rung 2 those distances are not observations, so the report is
      proprioception only.
  - Flag: `run_push_collect.py --round_feedback`. When it is off, prompts are
    byte-identical.
  - **The three 0/50 results (rung-1 e4aebf36, rung-1b 30f15f0c, rung-2
    3e8c52d4) are all labelled "obtained without inter-round feedback".**
    - Their reading on whether a viewpoint helps (1 → 1b) is **void**.
  - The corrected condition is **rung-2′**: the same seeds 5000–5049, run
    episode by episode against 3e8c52d4.
  - **If rung-2′ has any success**, rung-1′ (image + feedback) is re-run
    before any ladder comparison. The ladder rungs are comparable only under
    the same interface.
  - rung-2′ with < 5 successes → STOP and report (the 10-07 rule; no
    automatic rung-3).
  - Open (Rule 10 finding, raised to the PI): P1's L0 collect also kept a
    multi-turn conversation history (first turn + the last 6 user/assistant
    pairs, `client.EpisodeConversation.DEFAULT_RECENT_WINDOW`).
    - "Previous round only" therefore matches P1's *feedback* but not its
      *history*.
    - Implemented as ruled: previous-round feedback, no history.
- successes **≥ 5** at the current rung → proceed to (d) at that rung.
- Every rung activation is recorded here + in the provenance log; every
  replay / recap carries `obs_rung`; the P2 paper states which rung the data
  came from. The rung-1 SR is expected to be lower than an oracle prompt —
  that is the honest x=0, not a failure.
No discretion: the count selects the rung.

**(d) [PWR-SIM] steps 2–4** (`p2_preregistration_skeleton.md` §8): fill
the Δr prior from (c)'s variance, power-simulate the G×n grid (G ≥ 5 hard
floor, §8b), lock the stopping rule. n per generation comes from the sim.

**(e) FREEZE.** §2c takes effect here and only here. gen-0 collect starts
from an EMPTY buffer — the pilot buffer is not carried in (clean
provenance); pilot data archived for exploratory use.

**Loop-back:** if (c) shows the geometry still needs to change (successes
below threshold after the ladder, or situation variance too thin for r),
change it before (e) and re-run (c). Freezing is the (e) action, not now.

## Scheduling
GPU nights → A15 batch (D11 Amendment 15); GPU days → this pilot. The
rung-1 50-ep memory-ON pilot runs 2026-10-06 daytime.

## Body constraints in force for the pilot (not knowledge; ledger: safety / body)
- Static-scene collision interlock (SAFETY only; PI 2026-10-05): a commanded
  TCP point (target and every carrot setpoint) inside a STATIC collider is
  moved out — table: lifted to top + 1 cm over the footprint; robot body link
  (fixed torso/column): projected to the nearest face of its +1 cm box;
  ground: z ≥ ground + 1 cm. All boxes measured from the live USD stage.
  Awkward-but-free poses (below table-top height outside the footprint) are
  NOT blocked — observable, the model's to learn. Every clamp logged per round
  (`table_guard`). `wp3a_table_guard_check.py` PASS (table / body / free case).
  Scene note: there is no stand prim — the base is fixed at z_w 0.55 with
  nothing beneath it (only the ground plane at base z −0.55).
- Known body limit: yaw Y > ≈+15…30° from rest is not trackable (probe Y+30:
  22.6° error). Recorded, not root-caused, not blocking: proprioception
  reports the unachieved pose to the model. (c)'s
r-variance analysis is CPU.
