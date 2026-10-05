# WP1-③a rung-1 smoke — pre-committed criterion (written BEFORE the run)

> Pre-registered 2026-10-02, before the 10-ep rung-1 smoke. SR bands + failure
> routing are fixed here so the result is read mechanically, not rationalized
> post-hoc.

> **CORRECTION 2026-10-05 (PI steer — read this first).** The SR-band /
> rung-SR framing BELOW was a MISREAD of this pilot's purpose and is RETIRED.
> Why: (1) this smoke runs a FROZEN teacher with NO cross-episode inheritance
> (`recap_buffer=None`, verified) — there is no learning mechanism, so SR=0 is
> EXPECTED and carries no signal about "rung-1 language quality"; applying the
> "10-ep SR=0 → rung-2" rule to a no-learning feasibility pilot is a category
> error. (2) Per the P2 prereg (§2), SR is SECONDARY and competence-floor-
> confounded; r (situation-conditional correction) is the confirmatory measure.
> (3) This task's ONLY role (prereg §8b, step 2) is to be the contact task that
> UNBLOCKS a gen-0 collect so gen-0 r can be estimated — it is a pre-flight
> unblocker, not r-tracking itself.
>
> **Correct criterion for THIS pilot** = the minimum-viable-competence
> cold-start test (prereg §3a, P-MVC-teacher): can the frozen data-generator
> get ANY success (>0) on this task? If yes → the task can bootstrap gen-0
> (buffer can accumulate successes to retrieve/distil). If 0 → the task is
> below the cold-start floor and CANNOT seed expert-iteration as-is (not a
> language failure — a task-difficulty/kinematics failure). The "difficulty"
> r-tracking needs is CONDITIONAL RICHNESS (push direction varies with contact
> geometry per episode), NOT a kinematically pathological reach (reach-around-
> and-side-push), which crushes SR to 0 WITHOUT adding conditional signal — the
> wrong kind of hard. See wp3a_push_provenance.md 2026-10-05 entries.

## Run

10 episodes, EEF rung-1 language (A-spec v2), teacher gemma-4-31B on 148,
seeds 4700..4709 (env_seed_base + ep_idx), label=pilot (NOT confirmatory —
these are feasibility episodes, do not enter gen-0). push_s3a env (table, base
0.55, Pin-7a, gravity-on, Pin-11 success = cube within 0.05m of goal, round
cap 12, plateau 3×<1cm).

## Pre-committed SR bands

- **SR ≥ 45%**: rung-1 is strong — proceed to B (gen-0 collection) on rung-1.
- **SR 20–45%**: feasibility GO — rung-1 is a viable baseline; proceed to B.
- **SR 5–20%**: weak but non-zero — rung-1 carries signal; PI decides B vs
  rung-2 scaffold.
- **SR = 0% (0/10)**: rung-1 insufficient → escalate to **rung-2** (textual-hint
  scaffold) per the A-spec rung ladder (mechanical: 10-ep SR=0 → next rung).

Expectation (not a criterion — honesty note): n=2 pilot showed 1 success /
1 plateau, so a low SR (possibly <20%) is plausible; the frozen prompted
teacher is unstable at rung-1. That is the EXPECTED gen-0 starting point, not a
failure of the harness — r-tracking's job is to show SR climbing across
generations.

## Failure routing (pre-committed — classify every non-success)

Each failed episode is routed by its per-round record (the τ monitor + cube
displacement + servo_err are the raw material):

- **INFORMATION gap** — the teacher's EEF targets wander / don't track the cube
  (e.g. z climbs off the cube, large cube→goal with small cube motion despite
  low τ). The teacher cannot infer the right action from the image/state.
  → prompt/scaffold (rung-2) territory.
- **CONTROL** — teacher targets are sane but the arm doesn't execute (servo_err
  large with τ saturated, or the arm can't reach). → executor/primitive.
- **PHYSICS** — contact happens but the cube doesn't move as expected (cube
  slides wrong, tips, friction) despite good contact. → scene/physics (Pin-10
  friction, cube props).

Routing is tallied across the 10 episodes; the dominant class names the next
work item. No silent reinterpretation of a failure into a different class.

## Human-eye gate (precedes trusting the SR number)

Per standing rule (3492b96): the SR number is NOT trusted until the PI has
viewed a representative GIF (the overlay GIF with cube→goal distance). The PI's
visual audit — contact posture, cube motion, whether failures look like the
routed class — gates acceptance of the smoke result. I present + say what to
look for; I do NOT judge the gate.
