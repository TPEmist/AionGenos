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

**Rung ladder (mechanical, thresholds fixed now):**
- pilot (50 ep, memory ON) successes **< 5** → **rung-2** (text-hint
  scaffold, D6b disclosure convention); re-run (c) at rung-2.
- rung-2 pilot successes **< 5** → **rung-3** (PUSH_TO primitive);
  re-run (c) at rung-3.
- rung-3 pilot successes **< 5** → stop; escalate to PI (task change, not
  a further rung — no rung-4 is defined).
- successes **≥ 5** at the current rung → proceed to (d) at that rung.
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
GPU nights → A15 batch (D11 Amendment 15); GPU days → this pilot. (c)'s
r-variance analysis is CPU.
