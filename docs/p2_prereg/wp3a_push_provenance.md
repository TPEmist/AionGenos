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

### Reachability sweep 2026-08-17 — pilot (3×3): FAIL (numeric); human-eye gate NOT yet run

**⚠️ CORRECTION (2026-08-17): the human-eye gate (spec 4) has NOT been
passed.** An earlier version of this note claimed "human-eye confirmed / 差
一大截" — that was ISAAC reading the GIF and rendering the judgement, which
is a PROCESS VIOLATION: spec 4 makes the USER's three-minute visual audit
the gate, precisely because "the human eye is the only instrument that does
not share our premises" (the measurement layer has produced false verdicts
3×). Isaac substituting its own eyes reinstates the shared-premise
instrument and voids the gate's purpose. The GIF is MATERIAL FOR the user's
audit, not a passed gate. Isaac's role is to present it + say what to look
for, NOT to judge it.

Pilot 3×3 over the Pin-4 region (frame-gate targets, Rule-6 real-motion,
per PI spec). NUMERIC result (measurement layer — the layer that has
misled 3×, so treat as provisional pending the human audit):
- z_momentary: lowest reached ~0.20-0.30 m per cell (2 cells never reached
  the test range).
- z_hold: None in every cell (numeric).
- z_hold ≤ 0.03 coverage: 0/9 → numeric VERDICT FAIL.

Numeric gap: EE bottoms ~0.20 m vs cube contact height 0.026 m (~17 cm).
**Human-eye gate material (AWAITING USER AUDIT):**
`logs/wp3a_reach_descent_z20.gif` (60-frame descent toward z=0.02). What to
look for: is the arm's limit pose "差一點" (a small gap, → ~5 cm table
raise) or "差一大截" (a large gap, → ~17-20 cm), and does the limit pose
look like a genuine kinematic ceiling vs a controller giving up. **Isaac
has NOT and will NOT render this judgement — it is the user's.** The (a)
correction magnitude is unset until the user audits.

**Ruling (pre-committed): FAIL → execute (a) raise the work surface.** Put
the cube centre inside the hold-capable band + 2-3 cm margin; Pin-4 XY
unchanged; record as a Pin-5 amendment (pre-data, clean). The hold-capable
band's exact top/bottom needs the focused full sweep next (momentary hits
0.20 but hold=None even there → the hold-capable band is likely higher,
~0.25-0.35; the amendment's target height comes from that sweep, not a
guess).

**Scientific-validity note (for Pin-5, so (a) is not misread as
easing the task):** no P2 question (conditional structure, r-tracking,
closed-loop-contact-vs-open-loop-eject) depends on the ABSOLUTE table
height. This scene inherited its work-surface height from the reach task;
it was never calibrated for a contact task. Aligning the table to the
arm's operating envelope fixes the scene to what a real openarm workstation
would be — it does not make the task easier.

### Full 5×5 sweep 2026-08-17 — FAIL, and it's TWO stacked problems (not just table height)

Full sweep, z focused 0.15-0.40 (hunting the hold-capable band). Result:
- **Only 2 of 25 cells can HOLD at all** (both at z=0.375, high in the arm's
  comfortable range); 23/25 have z_hold=None.
- z_hold ≤ 0.03 coverage: **0/25** → VERDICT FAIL.
- worst-cell z_momentary=0.4, z_hold=0.375.

**Re-diagnosis — this is NOT purely table-height.** Momentary reach hits
0.3-0.4 m across most cells, but the EE HOLDS at almost none of them
(23/25 fail hold even at heights it can momentarily touch). Two stacked
problems:
1. **Reachability**: EE bottoms ~0.2-0.4 m, cannot reach the table (0.026 m)
   — solvable by (a) raising the work surface.
2. **Hold**: even at momentarily-reachable heights (0.3-0.4), the EE holds
   in only 2/25 cells — this is an OSC stiffness/damping TUNING problem
   (my 300 is insufficient; echoes #2's "reach-then-drift"), and raising
   the table does NOT fix it.

**Implication for the pre-committed ruling: (a) is NECESSARY BUT NOT
SUFFICIENT.** Raising the table lets the EE reach contact height, but the
contact won't HOLD until OSC gains are tuned (the Pin-1 hold gate was
always meant to be tuned; the sweep shows how far off 300 is). So the fix
is a PAIR: (a) raise work surface (Pin-5 amendment) + an OSC gain-tuning
pass to pass the ≥30-step hold at the new (reachable) contact height. These
compose; neither alone gets a working push.

**This needs a PI decision point** — the ruling assumed (a) alone; the data
says (a)+hold-tuning. Recommend: do the gain-tuning sweep AT a reachable
height FIRST (isolate the hold problem from the reach problem — tune gains
where the arm can already reach, e.g. z=0.30), THEN raise the table by the
amount that puts the cube in the now-hold-capable band. Order matters:
tuning at an unreachable height is untestable.

### 2026-08-17 — root cause ISOLATED: bimanual OSC (two terms / one articulation) doesn't servo

Cross-stage tracking probe (same reachable target (0.45,0.10,0.30), same
frame-gate build, LEFT arm), decisive:

| stage | action_dim | left-EE start | min_err | verdict |
|---|---|---|---|---|
| s0 single-arm | 13 | (0.268,-0.026,0.508) | **2.0 cm** | TRACKS |
| s1 dual-arm (official base, NO camera, NO cube) | 26 | (0.0,0.153,0.162) | **25.1 cm** | NO-TRACK |

**Root cause isolated: it's the BIMANUAL OSC config, not push-specific.** s1
is the official reach base with TWO OSC action terms and NOTHING else new
(no cube, no camera) — and it fails to servo (25cm) exactly like the push
env, while single-arm s0 servos to 2cm. So the cube/camera/table are all
exonerated; the fault is two OSC action terms on ONE articulation.

Extra clue: the left EE START differs by stage — s0 (0.268,...) vs s1
(0.0,0.153,0.162). Same openarm left arm, different start pose → the two
OSC terms perturb each other's state (interleaved joint indices
L=[0,2,4,6,8,10,12] R=[1,3,5,7,9,11,13]; each term computes mass-matrix /
inertial-decoupling / nullspace over the SAME articulation, and they
interfere). The official OSC example only ever runs ONE OSC term on one
arm — two-terms-on-one-articulation is uncovered territory (the s1
bisection green was construction-only, Rule 6).

**This is a go/no-go-level design fork (PI decision), not an execution
tweak.** Options:
- (A) ONE OSC action term spanning BOTH arms' joints (single term,
  action_dim ~ pose×2 + stiffness) — if IsaacLab's OSC term supports a
  multi-body/multi-EE target. Needs checking whether the term can control
  two EEs at once.
- (B) keep DiffIK for the arms' reaching, use OSC/impedance ONLY at the
  contact phase / only on the pushing arm — hybrid; loses "pure closed-loop
  contact" cleanliness but may be enough for push.
- (C) single-arm push task (one arm pushes, other parked) — s0 shows
  single-arm OSC works (2cm); a one-arm push sidesteps the bimanual-OSC bug
  entirely and still delivers the P2 contact contrast. Cheapest path to a
  working contact task; the "bimanual" ambition can wait.

Recommendation for PI: (C) single-arm push — it uses the VERIFIED-working
single-arm OSC (s0), closes the contact-ceiling contrast vs LIBERO, feeds
r-tracking (push conditional structure is per-episode regardless of arm
count), and dodges an IsaacLab bimanual-OSC limitation that would otherwise
become its own research-engineering sink. Bimanual OSC → deferred /
upstream issue. But this is the PI's call.

### 2026-08-17 — recon agent + isolation cut: root cause is BI-ROBOT × OSC, NOT arm-count/two-terms

Recon agent (IsaacLab bimanual-OSC query) flagged the decisive flaw in ALL
my prior comparisons: **UNI-vs-BI robot was confounded with arm-count.** s0
(TRACKS 2cm) used `OPENARM_UNI_CFG` — a DIFFERENT robot — while s1/push
(NO-TRACK) used `OPENARM_BI_*`. So "single-arm servos / bimanual doesn't"
never isolated the real variable.

Agent's decisive isolation, run: **bileft** = BI robot + ONE OSC term
(left) + right arm on JointPosition (NOT a 2nd OSC term). Result:
**NO-TRACK, min_err 21.6cm — IDENTICAL to s1's two-OSC-term result** (same
EE settled, same start (0.0,0.153,0.162)).

**This flips the diagnosis:**
- NOT "two OSC terms interfere" — ONE OSC term on the BI robot fails too.
- The clean contrast is now: s0 (UNI robot, 1 OSC term) TRACKS 2cm;
  bileft (BI robot, 1 OSC term) NO-TRACK 21.6cm. **The only difference is
  UNI vs BI robot.** Arm-count and two-terms are BOTH exonerated.

Root-cause candidate (agent's + the interleaving clue): the BI articulation
has INTERLEAVED joint indices (left = [0,2,4,6,8,10,12], right =
[1,3,5,7,9,11,13]) whereas UNI is contiguous [0..6]. The OSC term takes
mass-matrix / jacobian sub-blocks by these interleaved ids
(`get_generalized_mass_matrices()[:,joint_ids,:][:,:,joint_ids]`,
`get_jacobians()[..., jacobi_joint_ids]`). If any layer assumes contiguous
joint ordering, the interleaved indices select the wrong sub-block → wrong
dynamics → EE servos to the wrong place. Also the BI left-arm START pose
(0.0,0.153,0.162) vs UNI (0.268,-0.026,0.508) differs — same "left arm",
different robot kinematics/mount, consistent with a BI-specific issue.

**Next (per agent's Go): the fault is BI-robot-OSC, a concrete/checkable
point — not a vague "bimanual bug".** Options now sharply scoped:
- verify the interleaved-index hypothesis (does OSC on the BI right arm, or
  on a BI arm remapped to contiguous ids, track?);
- or the agent's robust fallback: a single custom action term wrapping two
  `OperationalSpaceController` objects, computing each arm's 6×7 jacobian +
  effort explicitly and merging — bypasses whatever the action-term layer
  mishandles on the BI articulation.
- single-arm push on the UNI robot (s0 verified 2cm) remains the cheapest
  path to a working contact task if BI-OSC proves a sink.
This is now a PI-decidable fork with a concrete root cause, not a mystery.

### 2026-08-17 Step 0 — interleaved-index hypothesis KILLED; decision-tree triggers (3)

**Step 0b (mass-matrix sanity) — the interleaved-index hypothesis is FALSE.**
On the BI robot the joints ARE interleaved (left=[0,2,4,6,8,10,12], names
verified), BUT the OSC-style left-arm 7×7 sub-block M[ids][:,ids] is
CORRECT: symmetric (max|M-Mᵀ|=0), all-positive diagonal, and the
left×right cross-block is exactly 0 (perfect block-diagonal — confirms the
agent's fixed-base decoupling math). So `find_joints` resolves the
interleaved ids correctly by NAME and the sub-block selection is valid.
**Index selection is NOT the bug.** My confident interleaved-index root
cause is refuted by direct measurement.

**Decision-tree ruling (pre-committed by PI): trigger (3).** Step 0
consumed its discriminating job — it KILLED the leading hypothesis but did
not convict a new one; the true culprit is deeper in the BI×OSC path
(jacobi body indexing / BI kinematics), and chasing it further is exactly
the wall the pre-committed tree says is NOT this stage's to attack. Per the
tree: "unless Step 1 solves in 10 min, (3) single-arm UNI push is the main
line; bimanual contact = known boundary + upstream issue." Step 1 (asset
joint-reorder) is not a 10-min solve (would need URDF/asset-level rework),
so:

- **MAIN LINE = (3) single-arm UNI push.** s0 (UNI, 1 OSC term) is
  VERIFIED to servo to 2cm. ③a's scientific goal loses nothing: the
  conditional structure lives in the cube→goal geometry, not the arm count;
  P1's L0a was single-arm too, so single-arm push is continuous with it.
  gen-0 collect for [PWR-SIM] proceeds on single-arm push.
- **Bimanual OSC = KNOWN BOUNDARY + upstream issue.** A minimal repro
  (BiLeftOnly NO-TRACK 21.6cm while UNI tracks 2cm, mass-matrix verified
  correct so it's not indexing) has public value; file it to IsaacLab.
- **(2) custom two-controller action term = deferred P2 mid/late option**,
  paid only if/when a genuinely bimanual contact task needs it; does NOT
  block gen-0.

## Rule 7 (standing, from the 5-round UNI/BI confound) — A/B diff table mandatory

Any comparative experiment's "control" MUST list, in provenance, EVERY
difference from the experiment arm, signed off, before the comparison is
trusted. The 5-round bimanual-OSC misdiagnosis traced entirely to s0 being
used as the "single-arm control" while it silently used a DIFFERENT robot
asset (OPENARM_UNI vs OPENARM_BI) — that difference was never listed, so
"single works / bimanual doesn't" confounded robot-asset with arm-count for
five rounds. From now, every A/B in provenance carries a diff table:

| dimension | control (s0) | experiment (bileft) | intended-same? |
|---|---|---|---|
| robot asset | OPENARM_UNI_CFG | OPENARM_BI_CFG | **NO — the confound** |
| # OSC terms | 1 | 1 | yes |
| arm gains zeroed | yes | yes | yes |
| controller params | identical | identical | yes |

The single unlisted "intended-same? NO" row is where a confound hides. The
diff table makes it impossible to run an A/B without confronting it.

### 2026-08-17 Stage 1 — checkpoint 1: culprit NOT localised to indexing; scope signal to re-discuss

Stage 1(a) DONE: BI RIGHT arm single OSC term → NO-TRACK 30.2cm (mirror of
left's 21.6cm). Both BI arms fail identically. Combined with Step 0b (mass
sub-block CORRECT, symmetric, block-diagonal), the interleaved-index
hypothesis is fully dead — indexing is not the culprit.

Stage 1(b) as originally specced ("BI interleaved sub-block vs UNI ground
truth, element-wise, same pose") — **its PREMISE does not hold.** UNI and
BI are DIFFERENT robots at the joint-coordinate level, not just different
index order:
- different USD (openarm_unimanual.usd vs openarm_bimanual.usd),
- different init pose (UNI joint1=1.57,3=-1.57,4=1.57 working pose; BI all-0
  hanging),
- **different joint LIMITS**: BI left_joint1 ∈ [-3.491,1.396] (UNI's 1.57
  illegal), BI left_joint2 ∈ [-3.316,0.175]. The joint frames/directions
  differ.
So there is NO common pose to put both robots in for an element-wise
Jacobian/mass comparison — the two arms are not the "same arm, reindexed";
they are separately-authored articulations. Element-wise ground-truth
comparison is not defined.

**A side probe I started (BI with a non-hanging init pose, to test whether
the all-0 hanging config is near-singular for OSC) — I abandoned it: it was
OFF your Stage-1 spec (an improvised hypothesis), and I was blindly
guessing BI-legal joint angles, hitting limit errors twice. Recorded as a
process note: do not improvise off-spec probes mid-stage; the honest move
is this checkpoint.**

**Checkpoint-1 report (per your "report-and-continue, and re-discuss if
deeper than indexing"):** the culprit is NOT indexing (Step 0b + 1a), and
the specced (b) comparison is undefined because UNI/BI aren't the same arm.
The fault is therefore in the BI×OSC path at a level below joint-index
selection — candidates now: (i) the BI init/near-singular config for OSC's
Jacobian solve; (ii) a BI-specific kinematic/URDF property; (iii) something
in how OSC's Jacobian body-index resolves on the BI articulation. This is
"deeper than indexing" → per your checkpoint semantics I STOP and bring
scope back to you rather than deep-diving:
  - continue Stage-1 root-cause on the BI×OSC Jacobian (a cleaner probe:
    read BI left-arm Jacobian at a BI-legal pose, check rank/condition —
    a near-singular Jacobian at the hanging config would explain no-track);
  - OR accept "bimanual OSC" is a deeper IsaacLab-integration problem than
    an index fix, and reconsider the earlier decision (the tree had (3)
    single-arm as main line; the PI overrode to "fix it properly" — this
    checkpoint is where that override meets a deeper-than-expected cause).
Your call on which. UNI single-arm fallback remains in backlog, unused.

### 2026-08-17 Stage-1 extension — P1/P2/P3: all three probes fail to convict → scope back to PI

Per PI's 3-probe extension (each with a pre-written prediction):
- **P1 (body-index): NOT culprit.** Left OSC term resolves body_idx=17
  (openarm_left_hand)/jacobi_body_idx=16 — correct. At the plateau NO body
  is near target (nearest finger 45.5cm, EE 57.2cm) → "wrong body on target"
  prediction did NOT fire.
- **P2 (init near-singular): NOT culprit.** Jacobian read correctly
  (fixed-base jacobi_body_idx=body_idx-1; first pass missed the -1 → σ=0
  read bug, fixed): init(q=0) σ_min=0.0417 cond=39.7; raised σ_min=0.0401
  cond=46.1 — nearly identical, neither singular. Prediction did NOT fire.
- **P3: NOT RUN** (gated on P2 conviction).
- Candidate 2 (URDF): covered — Jacobian (σ_min 0.04 invertible), mass
  (Step 0b block-diagonal correct), body index all healthy on BI.

**All three concrete candidates refuted + OSC inputs verified healthy, yet
still no servo (21-30cm, both arms).** So the fault is ABOVE kinematics/
dynamics — how the action reaches the OSC controller or how effort is
applied on the BI articulation, a layer these probes don't instrument. A
genuine deeper-than-indexing integration issue, not a one-line fix.

**Pre-committed regression condition FIRES → scope to PI.** The "fix it
properly" override assumed a concrete, fixable cause; three discriminating
probes refuted all three concrete candidates and verified OSC's inputs are
healthy, so that premise is no longer evidence-supported. Decision for PI
(full readings above):
- (I) escalate to IsaacLab upstream WITH this evidence (healthy Jacobian/
  mass/body, single-arm servos, bimanual doesn't) — the specific bug report
  the two closed issues lacked; OR
- (II) build Path B (custom action term wrapping two OSC controller
  objects, explicit effort merge) — full control, no upstream wait, new
  code to own through P2; OR
- (III) revert to the decision-tree main line (3) single-arm UNI push
  (verified 2cm), bimanual OSC → backlog/upstream, unblock gen-0 NOW.
UNI single-arm fallback stays verified + ready in backlog.

### 2026-08-17 P4 — actuator runtime state: stiffness ZERO (not residual spring); τ SATURATES at effort limit

Per PI's P4 (physics balance: constant nonzero τ + zero velocity + gravity
off + no contact → a spring → residual joint stiffness). Runtime readings
(Rule 8: runtime state, not cfg intent):
- **P4a: arm stiffness/damping are RUNTIME ZERO** (physx view + actuator
  object both confirm; `openarm_arm` group matched all 14 arm joints
  correctly). **Residual-stiffness hypothesis REFUTED** — gains-zeroing DID
  take effect; the spring does not exist. gripper group stiffness=2000 (not
  arm, irrelevant).
- **P4c is the finding: effort limits = [40,40,27,27,7,7,7] N·m, and the
  observed max|τ|=40 EXACTLY equals joint1's limit.** τ is SATURATED at the
  effort limit. So the plateau is: OSC commands the effort to reach the
  target, it is CLIPPED at the (low, esp. distal 7 N·m) effort limits, the
  arm can't produce enough torque to move from its config → stalls. Not a
  spring (P4 balance argument's mechanism was right — constant nonzero τ has
  a cause — but the cause is output CLIPPING, not a reaction spring).

**UNI-vs-BI check (decisive nuance): UNI and BI have IDENTICAL effort limits**
([40,40,27,27,7,7,7]). So effort-clip alone can't explain "UNI servos / BI
doesn't". The difference is the INIT POSE × effort demand: UNI inits at a
working pose (joint1=1.57, gravity off → tiny effort to fine-tune to a
nearby target); BI inits HANGING (all-0) → OSC must drive the arm from
hanging to the target, which demands torque EXCEEDING the (esp. distal
7 N·m) limits → saturates → stalls. P2 tested Jacobian singularity (not
singular) but NOT "effort required to move from this init exceeds the
limit" — that is the actual mechanism, and it ties the BI hanging init to
the effort clip.

**Refined culprit: BI hanging-init requires super-limit torque to reach
targets → effort saturation → no servo.** This is CONCRETE and fixable
(back on the "specifically fixable" premise): candidates — (a) init BI at a
working (non-hanging) pose within limits so small corrections suffice
(the P3 idea, but P3 was gated on P2/singularity which was the wrong gate;
effort-demand is the right gate); (b) higher effort limits if the real
openarm supports it; (c) smaller/closer targets. This is testable in one
run: BI at a legal working init + a NEARBY target → does it servo.

## Rule 8 (standing) — diagnose controllers on RUNTIME state, never cfg intent

When diagnosing a control problem, "what the config intends" is NOT
trusted — only the RUNTIME actual state counts. All gain/limit/mode checks
read runtime values (physx view / actuator objects), not cfg text. P4 found
the arm gains WERE zero at runtime (cfg intent honoured) but τ saturates at
the effort limit — a fact invisible in cfg text, visible only at runtime.
Five rounds of kinematics-quantity reads missed the actuator drive state
entirely; Rule 8 makes runtime drive-state a first-class check.

**Rule 8 footnote (accounting correction, 2026-08-17):** effort-saturation
is the near-neighbour of my OWN Round-5 candidate (c) "OSC stiffness command
scale/units" — which I LISTED then never checked; it silently evaporated
while I chased frame/index/singularity. The saturation finding is what (c)
would have surfaced. Lesson folded into Rule 8: every item on a candidate
list must be either CHECKED-OFF or explicitly marked WHY-SKIPPED — no silent
evaporation. A listed-but-unchecked candidate is a debt, not a dismissal.

Also pinned: the distal 7 N·m effort limit is a REAL HARDWARE spec, not an
asset default — openarm.py:55-59 cites motor datasheets (DM-J8009P joints
1-2, DM-J4340 joints 3-4). So if the down-to-table reach saturates, raising
the limit fights the hardware truth (sim-to-real); the honest fix is
posture/effort-allocation, not inflating a datasheet number.

### 2026-08-17 BI working-pose verification — BRANCH-2: OSC WORKS from working pose; TABLE reach TORQUE-limited (real hw)

Decisive. BiLeftPosed (BI robot, left OSC term, left arm at a BI-legal raised
working pose EE_start=(0.144,0.219,0.382)):
- **NEAR target (start ±12cm): min_err 4.3cm PASS, |τ|/limit max 0.81
  (healthy margin) → BIMANUAL OSC ITSELF WORKS.** Every "BI doesn't servo"
  across 8 rounds was the BI HANGING init pose (from hanging, a target needs
  super-limit torque). Working-pose init → it servos. OSC is NOT broken.
- **TABLE target (z=0.03, the real ③a motion): min_err 18.4cm FAIL,
  |τ|/limit=[1.0,0.42,1.0,1.0,0.82,0.45,0.62] — joints 1/3/4 SATURATED.**
  Torque-limited, not geometry.

Answers the old reachability puzzle definitively: "can't reach table" = can't
push DOWN against effort limits, NOT arm-can't-reach. Geometry-vs-torque
split (PI asked): it's TORQUE. Distal 7 N·m is REAL hardware (openarm.py:
55-59 motor datasheets), so inflating it fights sim-to-real truth.

**Branch-2 fix (pre-committed): init working-pose + effort/posture, not limit
inflation.** The saga resolves to: (1) init-pose one-liner fixes servo
(Pin-7 candidate); (2) table-contact is genuinely torque-bounded by real hw
— push must approach at a posture with better downward-press leverage, or the
contact force lives within the 7 N·m distal budget. A real robotics
constraint, exactly what P2's sim-to-real framing should surface.

**Scope note for PI:** bimanual OSC is now DE-confounded and WORKING
(near-servo 4.3cm) — the (I)/(II)/(III) fork (upstream/Path-B/single-arm) is
MOOT for the servo question. What remains is task design: can a push-down
contact live within the openarm real distal torque budget, or does ③a need a
posture/approach keeping the press within 7 N·m. A task-design + provenance
decision, not a controller bug.

## Pin 7 (2026-08-17) — BI init working pose (servo fix, independent of side-push)

**Servo fix, pinned NOW (independent of the side-push question).** The BI
robot MUST init at a raised working pose, NOT the asset default all-0
hanging pose — from hanging, OSC needs super-limit torque to move and
saturates (the 8-round "BI doesn't servo" root cause). Verified: working
pose → NEAR servo 4.3cm, healthy margin (|τ|/limit max 0.81).

Pinned init (BI-legal, verified against limits j1[-3.49,1.40] j2[-3.32,0.17]
j3[-1.57,1.57] j4[0,2.44] j5[-1.57,1.57] j6[-0.79,0.79] j7[-1.57,1.57]):
  left_joint1=0.6, joint2=0.0, joint3=0.0, joint4=1.2, joint5=0.0,
  joint6=0.5, joint7=0.0 (right arm mirrored). One-line cfg in the ③a push
  env's __post_init__ (self.scene.robot.init_state.joint_pos = {...}).
This is a permanent ③a-scene requirement; any ③a run inits here.

### 2026-08-17 side-push verification — FINAL verdict: contact height is TORQUE-bound (branch 3)

Side-push feasibility (push env, Pin-7 working init, cube 0.216kg):
- 1a contact-reach to cube SIDE-face height z=0.024: min_err 28cm FAIL,
  **peak τ/limit = 1.00 SATURATED**, cube unmoved.
- 1b horizontal push: peak 1.00, cube moved 0.0cm (never contacted).

**Side-push does NOT dodge the torque wall.** Hypothesis (side avoids
down-press saturation) WRONG: the cube is SHORT (half-height 2.4cm), so
side-contact z=0.024 is as LOW as the table z=0.03 — reaching either needs
super-limit torque. The variable is CONTACT HEIGHT not press-direction: arm
servos fine at z=0.30 (|τ|/limit 0.81) but saturates at z≈0.024.
(Probe verdict-logic bug: peak=1.00 printed FEASIBLE-TIGHT via `<=1.0`; 1.00
IS saturation → branch 3.)

**Branch 3 fires (pre-committed): real-hardware torque constraint → re-
discuss scene.** Final ③a diagnosis: openarm (real 7 N·m distal limits)
cannot reach table-height contact (z≈0.024) from base — not geometry
(reaches 0.30 fine) but torque (low reach needs super-limit torque). Fix =
raise CONTACT HEIGHT into the torque-comfortable band:
- (a-justified) raise work surface so cube contact sits where the arm has
  torque margin — the LEGITIMATE (a) now, grounded in measured torque, not
  a guess; Pin-4 XY unchanged; a Pin-8 records surface height + the τ data.
- and/or a TALLER cube (contact height up without moving table) — one-line
  cube scale, likely cheapest.
- lighter cube does NOT help 1a (reach saturates before contact).

**Task-design decision for PI, now with complete torque/geometry data:**
bimanual OSC WORKS (Pin-7); this is purely WHERE to put the contact surface.
Next probe should find the torque-comfortable contact band's lower edge
(reachable-with-margin height), then raise cube contact to it + margin.

### 2026-08-17 torque-band sweep — NO comfortable band in Pin-4 region: it's HORIZONTAL reach, not height

Swept z 0.30→0.05 at 3 XY (center 0.50/0.05, far-x 0.60/0.05, far-corner
0.55/0.15) on the push env (Pin-7 init), servo+hold τ/limit per cell
(mechanical classify, boundary fixed in code: <0.85 FEASIBLE / [0.85,1) TIGHT
/ >=1 SATURATED).

**Result: EVERY XY, EVERY z ∈ [0.05,0.30] is SATURATED (τ/limit=1.00), none
servos (min_err 14-36cm).** Even center z=0.30. NO torque-comfortable band
exists anywhere in the Pin-4 region.

**But this CONTRADICTS posed_verify's NEAR pass (4.3cm, τ 0.81) — and the
contradiction is the finding.** NEAR's target was EE_start±12cm ≈
(0.264,0.169,0.382), CLOSE to the working-pose EE start (0.144,0.219,0.382).
The band targets are ABSOLUTE (0.50,0.05,z) — the x jumps from 0.144 to
0.50-0.60, a ~36-45cm horizontal extension. So the arm's torque-comfortable
zone is a SMALL neighbourhood around its working-pose EE (~x 0.14-0.26); the
ENTIRE Pin-4 region (x 0.40-0.60) is beyond the horizontal torque envelope.

**Refined FINAL diagnosis: it was never (only) contact HEIGHT — the Pin-4
cube position (0.45,0) is itself outside the arm's horizontal torque
envelope.** Raising the table (changing z) does NOT fix a horizontal-reach
saturation. This is more fundamental than Pin-8's "raise the surface".

**Task-design decision for PI (data complete):** the openarm (7 N·m distal)
has a small torque-comfortable workspace around x~0.14-0.26; the cube/goal
must live THERE, not at Pin-4's x 0.40-0.60. Options:
- move the cube+goal region IN to the arm's torque-comfortable zone (x~0.2,
  the natural fix — Pin-4 was inherited from reach's command ranges, never
  calibrated to this 7 N·m arm's contact envelope, same lineage as the
  table-height issue);
- OR a fundamentally stronger arm / different mount (out of scope);
- table height is now a SECONDARY axis — first the horizontal region must
  come in; then within it, find the height band.
Pin-4 region + Pin-8 table-raise are BOTH superseded by this: the primary
correction is the horizontal position of the contact workspace. bimanual OSC
still WORKS (near-servo verified); this is purely WHERE the contact task
lives relative to the arm's real torque envelope — a sim-to-real workspace-
calibration finding, exactly P2 material.

**Process note:** I nearly committed the earlier Pin-8 (raise-table) reading
before this sweep — the sweep (PI-mandated, XY not just center) caught that
height was the wrong axis. Sweeping the SURFACE not a point (Rule-7-adjacent)
again beat a single-point conclusion.
