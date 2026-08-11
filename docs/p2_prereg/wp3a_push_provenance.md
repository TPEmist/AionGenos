# WP1-③a —真 push 任務 provenance (pinned BEFORE scene build / first data)

**Rule (Q1 companion + 爐子 lesson):** success predicate, physics params,
and controller choice are pinned HERE before the scene is built and before
any datum is collected. No "build it and see."
**Date**: 2026-08-11 (isaac session, master).
**Governs**: the WP1-③a push task only. WP1-① (OSC controller) delivered
GREEN; ③a is the first CONTACT task using it. L0–L3 untouched.

## Task identity
- **Task**: real bimanual push — the cube is a DYNAMIC RigidObject (pushable),
  NOT a pose visualizer. Closes the 2026-06-02 first-commit push ticket that
  was later diagnosed as a mis-named pose-reach.
- **Why push first (not press/twist):** zero new primitives — push = OSC
  impedance `move_to` (WP1-① deliverable); press/twist need new primitives
  (③b/③c). Conditional structure is naturally rich (push direction +
  contact point vary per-episode with cube→goal geometry) → what r-tracking
  needs to have signal to climb.
- **Baseline contrast:** LIBERO's two NO-GO walls (0/30 eject-on-contact
  with open-loop position servo). If ③a's teacher smoke clears with
  closed-loop impedance, "WP1-① unlocked the contact ceiling" gets a
  before/after datum straight into P2 motivation.

## Pin 1 — hold-in-tolerance acceptance criterion (from #2's lesson)
WP1-① #2 showed OSC reaches min 2.14cm then DRIFTS. In reach that was a
tuning footnote; in a CONTACT task it is a BLOCKER (push needs sustained
force against the cube). So ③a acceptance ADDS:
- **hold criterion**: after the EE reaches the contact target, ‖EE−target‖
  must stay within tolerance (≤ 5 cm) for **≥ 30 consecutive sim steps**
  (N=30, ~0.5 s at 60 Hz). Tune stiffness/damping NOW to pass this — do NOT
  roll the known drift into ③b.
- rationale: a controller that reaches-but-drifts cannot maintain the
  push contact; hold is the contact-readiness gate.

## Pin 2 — success predicate + physics params (爐子 lesson: read+write first)
- **Success predicate**: the CUBE (not the EE) enters the goal region.
  `success = ‖cube_pos_xy − goal_pos_xy‖ < GOAL_RADIUS` with
  **GOAL_RADIUS = 0.05 m** (matches the 5 cm gate used throughout P1/L2).
  Measured on the cube's world position, XY plane (push is planar on the
  table). Z ignored (cube stays on table).
- **Physics params (pinned, reuse L3's validated DexCube):**
  - cube: `DexCube` USD (`.../Props/Blocks/DexCube/dex_cube_instanceable.usd`),
    scale (0.8,0.8,0.8), `disable_gravity=False` (it must be pushable),
    solver_position_iteration_count=16, solver_velocity_iteration_count=1,
    max_lin/ang_velocity=1000, max_depenetration_velocity=5.0.
  - **mass / friction**: DexCube USD defaults inherited from L3 (the
    validated pick-place object). If a physics_material override is added
    for push friction, it is re-pinned here BEFORE that run's first datum.
    Initial run uses the DexCube USD defaults as-is (no override) so the
    baseline is the same object L3 already handles.
  - goal region: a fixed on-table target zone (green marker), pos pinned
    per-episode by the command generator; GOAL_RADIUS 0.05 m as above.

## Pin 3 — controller choice (Q1 companion rule)
③a uses the WP1-① OSC action term, motion-only at contact (no wrench axis
yet — pure impedance push, the cube moves by the EE's impedance-controlled
contact, not by a commanded wrench). Pinned OSC params BEFORE first data:
- `target_types=["pose_abs"]`, `impedance_mode="variable_kp"`,
  `inertial_dynamics_decoupling=True`, `nullspace_control="position"`
  (the WP1-① verified-working params).
- `motion_stiffness_task`: **to be tuned for Pin-1 hold**, starting at 100
  (the #2 value that reached but drifted); the tuned value that passes the
  ≥30-step hold is re-pinned here before the teacher smoke's first datum.
- arm actuator gains zeroed + disable_gravity (OSC effort prerequisite,
  from WP1-①); gripper gains left as-is (OSC does not control gripper; push
  uses a closed/rigid gripper as the push tool).
- wrench axes OFF (contact_wrench_control_axes all 0) — enabling commanded
  force is ③b (press), re-pins provenance then.

## Completion chain (order fixed)
scene + physics acceptance → teacher scaffolding port (error signal = two
legs: EE→cube + cube→goal, the L0a Fix-3 lineage extended to a moved
object) → 10-ep teacher smoke. Gate: any protocol ≥ 20–25% SR → GO.
Failure classification routed per the LIBERO template (info-gap / control /
physics, each with a pre-written fix budget). GO → dual-track: gen-0
collect (feeds [PWR-SIM] step 2 Δr prior) + ③b press.

### 2026-08-11 — scene+physics acceptance PASS; hold test deferred to scaffolding (layer fix)

Ran `wp3a_push_smoke.py`. **Scene + physics acceptance PASSES:**
- env boots (Isaac-AionGenos-WP1-Push-v0), OSC bimanual + dynamic cube.
- cube is a REAL dynamic RigidObject: mass=0.216 kg, gravity on, init pos
  (0.45, 0, 0.024) — pushable as designed.
- reset OK, seed-controlled.

**Hold test in this smoke FAILED — but for a LAYER reason, not a controller
one.** The smoke hand-set the cube's WORLD position as the OSC pose_abs
target; the EE stalled at ~38 cm (never approached). Diagnosis: OSC
pose_abs targets are NOT in world frame, so a hand-set world target is the
wrong frame (same frame trap as #2's first attempt). #2 succeeded precisely
because it used the env's OWN `ee_pose` command (frame guaranteed correct).

**Layer correction (not a failure):** the hold gate (Pin 1) must be tested
with a CORRECT-FRAME target, and the correct-frame target comes from the
command system — which is exactly what the TEACHER SCAFFOLDING uses. So the
order is: scene+physics acceptance (✓ done) → teacher scaffolding (uses
left/right_ee_pose commands, correct frame) → THEN the ≥30-step hold gate on
a real scaffolded push. Forcing hold into the scene smoke conflated layers.

**Status:** ③a scene+physics GREEN. Next in the completion chain: teacher
scaffolding port (error signal = EE→cube + cube→goal two legs, L0a Fix-3
lineage), then hold gate + 10-ep teacher smoke on it. The push env is built
and dynamic-verified; the frame-correct driving is the scaffolding's job.
