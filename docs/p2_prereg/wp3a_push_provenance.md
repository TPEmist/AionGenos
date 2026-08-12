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

## Frame gate (standing rule, 2026-08-12) — pose targets from command system ONLY

**Rule 5 (mechanised, from the 2×-same frame trap: #2 first attempt + the
hold-smoke).** Any pose target fed to an OSC `pose_abs` action MUST be
produced by the env command system (`command_manager.get_term(...)` /
`get_command(...)`) OR an explicit IsaacLab frame-transform util
(`isaaclab.utils.math.subtract_frame_transforms` etc.). **Hand-writing a
world-position straight into a pose_abs slot is FORBIDDEN** — it silently
uses the wrong frame (the EE stalls / grasps skew, no error raised). Both
prior stalls were this. Enforcement: `wp1_target_gate.py` provides the only
sanctioned target builder + an assert that the target's provenance is a
command term; smoke scripts import it and cannot bypass it.

## Approach-behind ownership (pinned) — primitive-level, not teacher output

**Ruling (LIBERO hover-descend precedent):** the "approach from behind the
cube" geometry is mechanical common-sense of a push, so it belongs at the
PRIMITIVE level, not the teacher's reasoning. Encapsulate
`push_toward(cube, goal)`: the primitive itself computes the behind-cube
approach point (offset along the reversed cube→goal vector), approaches, and
pushes along the line. **The teacher's canonical output = WHICH cube to
push + toward WHICH goal** — it does NOT emit an approach-point coordinate.
This split is pinned here; the scaffolding prompt is written to it. Error
signal has two legs (EE→cube, cube→goal), oracle sources disclosed per the
L0a convention.

### 2026-08-12 — frame gate + push_toward built; design clarification surfaced

**Built (spec 1+2 mechanised):**
- **Frame gate (Rule 5)**: `wp1_target_gate.py` — the ONLY sanctioned OSC
  pose_abs target builder. `base_frame_target_from_world` now uses IsaacLab's
  `subtract_frame_transforms` (root as frame-0, full rotation), NOT the naive
  world−root subtraction (that dropped root orientation — the residual frame
  error in the first hold-smoke). `assert_command_frame` boot-asserts the
  command term still exposes base-frame `.command` (= pose_command_b, the
  frame WP1-① #2 verified). Confirmed at runtime: the reach command's
  `.command` IS pose_command_b (base), while `pose_command_w` (world) is
  computed lazily and read 0 before update — reading _w was my error.
- **push_toward primitive (spec 2)**: computes the behind-cube approach point
  (offset along reversed cube→goal), returns a base-frame target. Teacher
  will only choose cube+goal; geometry lives here.

**Design clarification (the real next-step, not a bug):** the push task needs
a CUBE goal, but the current env only has an EE-pose command (`left/right_ee_
pose`) — a target for the ARM, not for the cube. The hold-smoke wrongly fed
the EE command as the cube goal (and read the un-updated world field → 0).
**Push requires its own cube-goal**: a fixed on-table goal region (provenance
Pin 2's green marker) or a dedicated object-goal command. That is a
scaffolding-level addition (a cube-goal command term + the two-leg error
signal EE→cube / cube→goal), NOT something a smoke can improvise. 

**Status:** frame-gate + push_toward mechanisms GREEN and unit-safe; the
scaffolding's first real task is to add the cube-goal command term, then
push_toward has a real goal, then hold-gate + 10-ep smoke. Scene+physics +
frame machinery are in place; the cube-goal command is the next concrete
build.

## Pin 4 — cube-goal command: sampling distribution (pinned BEFORE first data)

The push goal is a CUBE goal (where the cube must end up), realised as a
seed-deterministic `cube_goal` UniformPoseCommand term (base-frame `.command`,
same sanctioned frame path as the EE commands; frame-gate compliant). Seed
determines the goal → same seed same goal (P2 paired design) and the goal is
the r-tracking "situation" variable. Goal position written into the replay
(`goal_pose`, alongside the existing seed-determined init fields).

**Sampling distribution (Pin 2 table region, planar push):**
- `pos_x = (0.40, 0.60)` m — on-table, within push reach, in front of arms.
- `pos_y = (-0.15, 0.15)` m — lateral span (margin inside the EE reach used
  by ee_pose's (-0.2,0.2) so the push line stays reachable).
- `pos_z = (0.02, 0.02)` m — fixed at cube resting height (planar push;
  cube stays on the table). Degenerate range = deterministic z.
- orientation ranges all (0,0) — goal is a POSITION region (GOAL_RADIUS
  0.05 m, XY), orientation irrelevant to the cube-in-goal predicate.
- **Margin note:** cube inits at (0.45, 0.0); goal pos_x/pos_y ranges keep a
  non-trivial cube→goal vector (push has somewhere to go) while staying in
  the reachable/pushable workspace. `resampling_time_range=(inf,inf)` — the
  goal is FIXED for the whole episode (F35 lineage; no mid-episode jump).

### 2026-08-12 (cont.) — cube-goal built + frame CORRECT; new blocker: bimanual OSC EE inert

**Built (spec 1-3):** cube-goal command term (re-purposed left_ee_pose,
seed-deterministic, base-frame `.command`, Pin-4 distribution, recorded in
replay path). Frame is now DEMONSTRABLY correct — the smoke prints sane
base-frame values: cube_b=[0.45,0,0.024], goal_b=[0.419,0.13,0.02] (in the
Pin-4 sampling range), approach_b=[0.464,-0.058,0.026] (behind the cube),
cube→goal 13.3cm. push_toward_base geometry verified. Rule-5 frame gate held
(assert passed; `.command` base not `pose_command_w`).

**New blocker (needs its own diagnosis): bimanual OSC EE is INERT.** With a
correct base-frame pose_abs target, the left EE does not move at all
(31.96cm, unchanged across 200 steps — not even gravity drift), cube not
contacted. This CONTRADICTS WP1-① #2, where the SINGLE-arm s0 env servoed to
2.14cm with the same method. Difference = single (s0, OPENARM_UNI) vs
bimanual (push, OPENARM_BI_HIGH_PD). Leading hypothesis: with the arm
actuator gains zeroed (OSC effort prereq) AND OSC somehow not taking over
the effort on the bimanual articulation, the arm has NO driving force
(neither PD nor OSC). Candidate causes to diagnose next: (a) the two OSC
action terms on one articulation — does each term's joint_names regex
(openarm_left_joint.* / openarm_right_joint.*) correctly claim its half, or
does the shared `openarm_arm` actuator group interfere; (b) action layout
into the two terms (verified [L13][R13] in principle, but the inert EE
suggests the left term's pose_abs is not reaching the controller); (c) OSC
stiffness command scaling (my action[:,7:13]=300 vs the term's
stiffness_scale=100 → effective stiffness / units).

NOTE: s1 bisection (dual-arm OSC, two terms) PASSED boot+reset+step earlier
— but that fed ZERO actions (just stepped), so it never exercised whether a
NON-zero pose_abs target actually drives each arm. s1's green covers
construction, not servo. This inert-EE is the first test of bimanual OSC
SERVO under a real target.

**Status:** cube-goal + frame machinery GREEN; bimanual-OSC-servo is the
blocker before hold-gate/smoke. Next: diagnose the inert EE (single-arm
works, bimanual doesn't) — likely the two-terms-on-one-articulation
interaction. Hold gate + 10-ep smoke + the mandatory human-eye GIF gate
(spec 5) all wait behind a moving arm.

## Rule 6 (standing, from the s1 lesson, 2026-08-12)

**A gate's green covers ONLY the path it actually exercised.** Any controller
config's acceptance MUST include a per-limb NON-ZERO-target real-motion check;
a zero-action boot+step green may NOT be claimed as servo capability. (s1
passed boot+reset+step feeding ZERO actions → it never tested whether a real
pose target drives each arm; that gap hid the reachability issue below for a
whole cycle.) The hardened-runner stage template gains this check: every
controller stage drives one limb to a known-reachable non-zero target and
asserts measurable EE motion before reporting green.

### inert-EE diagnosis result (Steps 0/1/2) — NOT inert; it's REACHABILITY

Diagnosis flipped the premise. Readings:
- **STEP0 torque NONZERO** (max|τ|=40, sum=108) and **EE MOVED 10.08cm / 20
  steps**. So OSC IS applying force and the EE IS moving — "inert" was wrong.
- STEP1 joint IDs correct + disjoint: left=[0,2,4,6,8,10,12],
  right=[1,3,5,7,9,11,13] (interleaved but each 7, non-overlapping). Made a
  boot-assert per Rule 1.
- STEP2 action layout correct: left term gets action[0:13] = pose(0.46,-0.06,
  0.03) + quat + stiffness 300×6; right term action[13:26] all zero. No
  layout/impedance bug (my leading suspect was WRONG).
- disable_gravity=True → no-drift is EXPECTED (not a clue).

**Root cause: target reachability, not control.** The smoke's "31.96cm flat"
was the EE reaching its WORKSPACE LIMIT ~31cm short of the target, then
stopping — not failing to move. The push approach target has **z=0.026 m
(table height)**; WP1-① #2 succeeded with targets at z=0.15–0.5 (the arm's
comfortable range). The openarm EEs, at their mounting height, may not reach
down to table-contact height.

**This is a go/no-go-level finding for ③a:** push REQUIRES the EE to reach
table height to contact the cube (cube at z=0.024). If the openarm mount
cannot reach the table, push is geometrically infeasible in this robot
configuration — NOT a tuning matter. Next: a reachability sweep (drive EE
down, find the lowest reachable z) to decide feasibility. If the arm can't
reach the table, options are (a) raise the cube/table to the arm's reachable
band, (b) re-mount the arms lower, (c) re-scope ③a — a PI decision, not an
execution tweak. Hold gate / smoke / GIF gate all wait on push being
geometrically possible.
