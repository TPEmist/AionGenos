# WP1-③a rung-1 smoke — pre-committed criterion (written BEFORE the run)

> Pre-registered 2026-10-02, before the 10-ep rung-1 smoke. SR bands + failure
> routing are fixed here so the result is read mechanically, not rationalized
> post-hoc.

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
