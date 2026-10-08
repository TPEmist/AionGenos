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
object) [CORRECTED 2026-10-05: not the L0a condition — see the two-leg-reveal correction below] → 10-ep teacher smoke. Gate: any protocol ≥ 20–25% SR → GO.
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
lineage) [CORRECTED 2026-10-05: see the two-leg-reveal correction], then hold gate + 10-ep teacher smoke on it. The push env is built
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

### 2026-08-17 P5 δ-clamp setpoint probe — BRANCH-3: not a span artifact; domain shrink stands (gravity-honest)

PI-mandated P5 (jumped the queue before any domain shrink). Hypothesis: the
band sweep + side-push commanded the ABSOLUTE far target in ONE step
(action[:,0:3]=far), so OSC saw an instantaneous position error = the whole
30-45cm span → K·(huge error) saturated. Maybe a SETPOINT-SPAN ARTIFACT, not
the arm's real envelope. Fix: clamp each commanded setpoint to ≤δ=3cm ahead
of the CURRENT EE (carrot); walk the far target in as a chain of δ-steps;
per-step max(τ/limit) throughout; hold ≥30.

**Result (δ=3cm, push env, Pin-7 init):**
- a far-horizontal (0.50,0,0.30): reached=False, min_err 23.8cm (walked in
  from ~42 then stalled), walk_peak=1.00 hold_peak=1.00 — SATURATED.
- b far+low/cube (0.45,0,0.024): reached=False, min_err 53.3cm (DIVERGED —
  ended farther than start), peaks 1.00 — SATURATED.
→ a_ok=False b_ok=False → **BRANCH-3: clamp does NOT save it.**

**Config read BEFORE recording (killed my first mis-reading):** I first
guessed "arm extends → gravity lever on 7N·m distal saturates." FALSE —
osc_testbed_cfg.py:55 sets robot `disable_gravity=True` (H1-inherited OSC
prerequisite; push_s3a inherits it). Gravity is OFF. So the saturation is NOT
gravity torque. With the setpoint error BOUNDED to 3cm AND gravity OFF, the
arm STILL saturates walking into the far/low region. The residual driver is
the OSC control law itself at the workspace boundary: with
inertial_dynamics_decoupling=True the task-space inertia M_task blows up near
the reach boundary, and nullspace_control="center" adds a pull-back torque as
the arm extends off its centred posture. That is the arm's REAL controllable
workspace under THIS (validated, not invented) OSC tuning + 7N·m distal — not
a setpoint-span artifact.

**Gravity-honesty note (Pin-TODO below):** the whole diagnosis ran with
robot gravity OFF — an OPTIMISTIC torque budget. With gravity ON (gen-0
reality), the far-point torque only gets WORSE and the comfort zone only
SHRINKS. So BRANCH-3's "shrink the domain" conclusion is if anything
UNDER-stated; it will not reverse under honest gravity. This makes the
decision safe to act on.

**DECISION for PI (data complete, three-branch pre-committed → BRANCH-3):**
the contact workspace must move IN to the arm's controllable/torque-
comfortable zone (~x 0.14-0.26, the posed NEAR pass region: 12cm reach,
τ 0.81). Pin-4's x 0.40-0.60 was inherited from the REACH task's command
ranges, never calibrated to this arm's contact envelope.
**P2 scientific cost (on the table, per PI spec):** r-tracking's "context"
is supplied by per-episode cube+goal geometry variation; a shrunk domain =
poorer context space = weaker P2 signal source. The shrink must preserve, in
the new (smaller) region: cube sampling area + goal area + behind-cube
approach clearance + ≥8cm push-distance 2D direction variation. Whether
x~0.14-0.26 (a ~12cm-deep band) can hold all four is the design question to
settle WITH the PI — not a unilateral shrink.

**Pin-TODO (gravity re-enable, note-2):** disable_gravity=True is an
H1-inherited OSC prerequisite. AFTER the task geometry is settled and BEFORE
gen-0 collect: re-enable robot gravity + turn ON OSC gravity_compensation,
re-verify one round (the no-gravity torque budget is optimistic;
sim-to-real honesty requires the gravity-on number).

**Process win:** reading the config before recording caught my own
gravity-lever misread — the finding is "control-law workspace boundary, not
span, not gravity," which is stronger and correctly-attributed. Rule-2 family
(don't record a mechanism you didn't read the runtime/config state for).

### 2026-08-20 P6 pre-clip + ablation — BRANCH-3 OVERTURNED: controller over-command, not hardware. Pin-9 hybrid control.

PI rejected the BRANCH-3 domain-shrink: "12cm comfort zone" contradicts
DiffIK's 3-month full-table record on the SAME arm/table — an unresolved
contradiction bars the verdict. P6 three-piece, read the number nine rounds
never read: OSC's COMMANDED torque BEFORE the actuator clips it.

Path (task_space_actions.py): `_osc.compute()` → `term._joint_efforts`
(PRE-clip commanded) → `set_joint_effort_target` → actuator clips →
`robot.data.applied_torque` (POST-clip, =limit when saturated — the only
thing nine rounds read).

**(a) PRE-CLIP read, baseline OSC (decoupling=True, nullspace=position):**
- a far-horizontal (0.50,0,0.30): min_err 14.8cm, **PRE-clip |τ_cmd|/limit
  = 5.17**, post-clip 1.00.
- b far+low/cube (0.45,0,0.024): min_err 30.5cm, **PRE-clip = 6.19**,
  post 1.00.
→ OSC COMMANDS 5-6× the motor limit; the actuator clips it to 1.00. The arm
was never physically unable to reach — the CONTROLLER asked for torque the
motors cannot deliver. This resolves the DiffIK contradiction: DiffIK reaches
x=0.6 (it solves joint *position*); OSC asks 5-6× torque at the same point.
**"12cm hardware comfort zone" is VOID; Pin-4 geometry vindicated.**

**(b) ABLATION (decoupling=False, nullspace='none') — PREDICTION OVERTURNED:**
- a: min_err 29.2cm (WORSE), PRE-clip = 21,512,042 — diverged.
- b: min_err 42.8cm (WORSE), PRE-clip = 41,801,836 — diverged.
→ Turning decoupling OFF did NOT heal it — it blew up to millions and the EE
diverged. So our "decoupling = the Λ-inverse singular blow-up source, turn it
off → healthy" hypothesis is FALSE. Decoupling is here a STABILISING term;
without it the naked spring-damper on a large-span setpoint (high stiffness
300 × 30-45cm error, integrated over 150 steps) goes numerically unstable.

**Honest mechanism (corrects the probe's auto-verdict wording):**
- The CONVICTION stands: baseline pre-clip 5-6× >> 1 → the ceiling is the
  controller's command, not arm physics (DiffIK full-table record confirms).
  PI's rejection of BRANCH-3 was correct.
- The mechanism is NOT "decoupling singular blow-up" — ablation proved
  removing it is worse. The over-command comes from the COMBINATION of a
  single-step large-span setpoint × high task stiffness under THIS OSC
  tuning; AND no single OSC knob covers both full-table transport and contact
  (baseline over-commands, ablation diverges — both roads break).
- Therefore the fix is ARCHITECTURAL, not a flag tweak → hybrid control.

**Pin-9 (architecture, DECIDED — per PI spec (c), independent of a/b):**
HYBRID CONTROL. This is the design answer, not a workaround — free-space
position control + contact-phase impedance control is standard real-robot
practice, sim-to-real honest.
- TRANSPORT phase: DiffIK (existing, validated) drives the EE to the
  pre-contact point behind the cube.
- CONTACT phase: OSC takes over the push (working range ≤±12cm, entirely
  inside the NEAR-verified envelope τ 0.81).
- SWITCH point = a phase boundary INSIDE the push_toward primitive,
  transparent to the teacher (canonical output unchanged).
- Consequence: Pin-4 geometry KEPT; domain-shrink / table-raise / task-
  semantic-change ALL unnecessary. Supersedes Pin-8 and the BRANCH-3 shrink.

**Rule 9 (institutionalised):** controller config knobs (decoupling,
nullspace, stiffness, impedance mode) are DESIGN degrees of freedom, not
physical ground truth. Before declaring ANY "hardware limit", ablate the
controller variants first — read the PRE-clip commanded quantity, not just
the post-clip applied one. Nine rounds read only post-clip (always =limit
when saturated) and nearly mislabelled a controller-tuning ceiling as a
hardware envelope. (Related: Rule 2 read-runtime-state family.)

**Pin-TODO carry-over:** the gravity-on re-verify (P5 note-2) still stands —
do it on the HYBRID controller before gen-0.

### 2026-08-20 Reachability envelope (L2 instrument) — instrument fixed after 3 harness bugs; z-wall signal REAL but CONFOUNDED by y=0 + orientation

Per PI spec (instrument rule): drove the reachability sweep with the VALIDATED
L2 DiffIK instrument (ArenaEnvBuilder level=2 + IsaacLabEnvInterface.
execute_command), NOT a hand-written IK probe. Baseline-first, (x,z)-face
sweep, error vector + joint-limit proximity + orientation contrast + GIFs.

**Three harness bugs found & fixed via baseline-first (all MINE, not the
instrument):**
1. Invented baseline point (0.45,0,0.30) — real L2 left-arm cmds span
   x[-0.17,0.51] z[0,0.70]; there is NO canonical single point, and
   final_dist (median 15.6cm, 2% <5cm) is an OBJECT-GOAL metric, not EE servo
   error. Fixed: self-referential baseline (EE_start + 5cm x).
2. Readback frame: interface uses world−root (translation only); DiffIK
   consumes subtract_frame_transforms (with rotation). Fixed readback to match
   the controller frame. (Moot here: root_quat = identity, but the bug was
   real and would bite a rotated base.)
3. Forced identity quat → the servo wasted motion slewing orientation, z
   drifted (6.2cm baseline FAIL). Fixed: HOLD the EE's current orientation →
   baseline min_err = 0.0cm PASS. Instrument+frame validated.

**Sweep result (baseline PASS → readings trustworthy for what they measure):**
- EVERY (x,z) cell STUCK (none <3cm). Low z: z-wall(hover), dz 17-24cm,
  joint2/joint4 pinned at limit (1.00) — the fingerprint of a KINEMATIC wall,
  not servo budget (budget-limited joints sit mid-range, still moving).
- At z=0.30 (reset height), x=0.25: 3.8cm (nearly reached, y-limited);
  extending x to 0.45 → 12.4cm, joint2 at limit — an x-extent boundary too.

**TWO CONFOUNDS I baked in without isolating — so I do NOT declare Pin-10:**
- **y=0 centerline demand:** every cell targets y=0, but the LEFT arm's
  natural workspace is the +y side. dy≈+9.2cm persists EVERYWHERE (EE can't
  reach centerline). The cube sits at y=0, so this is TASK-RELEVANT — but it
  means "low-z unreachable" is really "low-z AT CENTERLINE with the LEFT arm
  unreachable," which is a different (and arguably righter) statement: maybe
  the RIGHT arm should own y≤0, or the cube should sit on the left arm's side,
  or it's a bimanual reach. This is a task-geometry question, not a pure wall.
- **orientation not truly relaxed:** DiffIK command_type="pose" ALWAYS
  constrains orientation. My "relax" contrast used palm-down (worse), but that
  is still a constraint — I could NOT test true orientation-free reach. A
  genuine test needs command_type="position" DiffIK. So "orientation not the
  blocker" is UNPROVEN, only "palm-down is worse than held-current."

**Verdict (honest): strong z-wall + x-extent kinematic signal (joints at
limit, hover pattern), but the y=0 centerline confound + un-relaxed
orientation mean the sweep does NOT cleanly prove "pure z-wall → raise table
(Pin-10)."** The decision-tree's Pin-10 branch is PLAUSIBLE but not earned
until the two confounds are killed. Reported to PI with GIFs (human-eye gate)
+ this data, NOT unilaterally decided.

**GIFs for the human-eye gate:** logs/reach_frames/stuck_x{35,40,45}_z24.gif
(left arm servoing toward y=0, z=0.024 at x=0.35/0.40/0.45).

**Recommended confound-killers before any Pin-10 (for PI approval):**
1. Re-sweep at the LEFT arm's natural y (e.g. y=+0.10..+0.20), not y=0, to
   separate "can't reach low z" from "can't reach centerline."
2. Add a command_type="position" (orientation-free) DiffIK pass to truly test
   whether orientation constraint blocks low-z.
3. If BOTH confounds killed and low-z STILL walls → Pin-10 (raise table) is
   earned, clean kinematic version.

### 2026-08-20 (addendum) Human-eye gate caught a GIF-material bug: RED cube ≠ servo target

PI viewing the stuck-cell GIFs asked: "the red block looks CLOSER to the body,
but the arm is fully extended FORWARD — which do I trust?" That question
exposed a real defect in MY material, not arm behaviour:

- The reachability sweep uses the L2 env as a KINEMATIC INSTRUMENT: it feeds
  the left arm a bare coordinate (x,y,z) via execute_command → the DiffIK
  ACTION term. There is NO goal block at that coordinate.
- The RED cube in the GIF is L2's left goal VISUALIZER, bound to the
  `left_ee_pose` COMMAND term (pose_command_w). execute_command drives the
  ACTION path only; it never touched the command term. So the red cube sat at
  the reset-time RANDOM command (near the body) while the arm servoed to my
  invisible forward target. Two unrelated things in one frame → misleading.
- ⇒ the first GIF batch was UNAUDITABLE (wrong reference object). The PI's eye
  caught it in one second — exactly the human-eye gate working as designed.

Fix: `mark_left_goal()` writes the servo target into the command term's
pose_command_b each burst; CommandTerm.compute() → _update_metrics()
recomputes pose_command_w every step, so the RED cube now marks the arm's TRUE
target. L2 resampling_time_range is LOCKed, so the mark persists. Verified the
sweep numbers are byte-identical with/without the mark (baseline 0.0cm;
x0.25z0.024=22.8cm) — the mark is purely visual, does not perturb the servo.

Regenerated GIFs (RED cube now = true target): logs/reach_frames/stuck_x{35,
40,45}_z24.gif. Human-eye gate re-opened with correct material.

### 2026-08-20 HUMAN-EYE GATE VERDICT (PI) — the wall is LATERAL, not vertical; Pin-10 (raise-table) REFUTED

PI audited the corrected GIFs (RED cube = true target). Verdict:
1. "橫向勾不到,再往右一點應該就可以了" — the arm reaches SHORT LATERALLY;
   a bit further right (−y, toward centerline) would reach.
2. "自然極限,但往右是沒問題的" — looks like a natural extent, but the
   rightward direction is NOT hard-blocked (i.e. close/achievable, not a wall).
3. "手指 ee 需要往右" — the finger EE needs to go right (−y).

**This OVERTURNS my numeric classifier.** My code labelled every low-z cell
"z-wall(hover)" because |dz| (≈20cm) was the largest error component. The
human eye identified the CAUSAL wall as LATERAL: the arm can't get its finger
across to the y=0 centerline (dy≈+9.2cm everywhere), and the large dz is a
DOWNSTREAM consequence — once the arm is laterally maxed and a joint pins, it
also can't descend. Magnitude-ranking misread cause; the eye read cause.

**Consequences:**
- **Pin-10 (raise the table / z-wall → raise work surface) is REFUTED by the
  human eye.** We did NOT wrongly raise the table. Height is not the wall. The
  old option (a) does NOT return this time — the clean kinematic evidence
  (human-eye) points AWAY from it.
- The real constraint is the y=0 CENTERLINE demand with the LEFT arm (confound
  #1 I flagged — now CONFIRMED), likely COMPOUNDED by the held-orientation
  constraint pinning the wrist in a poor IK config (confound #2 — the PI's
  "往右沒問題" suggests a better config/orientation would reach).

**Both confounds I flagged are now the live hypotheses, human-validated.** The
decisive next test (confound-killer) is well-motivated: re-sweep with
orientation FREED (command_type="position" DiffIK) AND across the left arm's
natural lateral zone (+y), to map the true (x,y,z) envelope and check whether
low-z becomes reachable once lateral+orientation are unconstrained. Then place
the contact workspace INSIDE that envelope (lateral/side placement or bimanual
arm-assignment), NOT by raising the table.

### 2026-08-20 CONFOUND-KILLER + frame fact — the "z-wall" is BASE-AT-FLOOR geometry; there is NO TABLE

Confound-killer sweep (PosFree env: DiffIK command_type="position", wrist
FREE; both arms; full y∈[-0.20,+0.20]; per PI "先純診斷,不預設歸屬"). Baseline
self-referential PASS both arms (L 0.0cm, R 0.4cm) → instrument valid.

**Envelope (orientation-free):**
- z=0.30: LEFT reachable y∈[0,+0.20] (its +y side), RIGHT y∈[-0.20,0] (its
  −y side) — arms naturally own opposite lateral halves (assignment EMERGED,
  not preset).
- z=0.10: NONE reachable, either arm, any y.
- z=0.024: NONE reachable, either arm, any y (dz≈22-26cm, joint2/4 pinned).
- LOW-Z reachable cells (orientation-free, full y): **0**.

Orientation-free did NOT rescue low z → the held-orientation confound was
NOT the (main) blocker; something more basic gates low z.

**Frame-fact probe (wp3a_frame_fact.py) — the decisive read I should have
done rounds ago:**
- root_pos_w = [0,0,0] → ROOT frame == WORLD frame; z=0.024 root IS z=0.024
  world. The frame-confound I suspected is RULED OUT (no offset).
- Both EEs rest at world z≈0.20-0.25. The robot BASE is mounted at world z=0.
- **The env has NO TABLE.** scene entities = terrain, robot, camera, ground,
  light. The code comments say "looking down at the table" but there is no
  table prim — only a ground plane at z=0. The cube (push env only) sits at
  world z=0.02 = basically ON THE FLOOR, and the arm base is AT THE FLOOR too.

**Reframing (this overturns the question, not just the answer):** "z=0.024
unreachable" is not a torque wall, not an orientation wall, not a lateral
wall — it is that we asked an arm BASED AT FLOOR LEVEL to fold down to its own
feet (z≈0.02, 20cm below its natural EE rest). That is geometrically extreme
for ANY 7-DoF arm. And it is consistent with the DiffIK 3-month record: real
L2 commands ranged z→0 but ACHIEVED median 15cm off — L2 never actually
touched the floor; its goal cubes float. **The premise "cube on the floor at
z=0.02" was inherited by push_s3a from elsewhere and NEVER validated against
this floor-mounted arm.**

**Pin-10 (raise the table) is now MOOT in its old form — there is no table to
raise.** The real design question for the PI:
- the WORKSPACE needs a WORK SURFACE at the arm's natural EE height (~z 0.20-
  0.30), i.e. ADD a table/pedestal at ~0.20-0.25 and put the cube ON IT — so
  contact happens where the arm actually works (the z=0.30 reachable band),
  not on the floor;
- OR mount the arm base ABOVE the work surface (real robots sit above their
  table), equivalent geometry;
- either way the cube contact height should sit in the z≈0.20-0.30 reachable
  band, which the envelope shows IS reachable (and laterally, each arm owns
  its side — natural bimanual assignment).
This is the clean, correctly-attributed version of "raise the work surface",
now backed by: orientation-free envelope + frame fact + no-table discovery +
DiffIK-record consistency. Reported to PI; NOT unilaterally decided.

GIFs: logs/reach_posfree/posfree_L_x{25,35,45}_y-20.gif (low-z stuck, wrist
free — shows the arm folding toward the floor).

### 2026-08-20 ROOT CAUSE (screenshot-confirmed): the scene has NO usable table — L3 swapped the table/robot z-offset from the official convention

PI: "確認範例場景的設定應該是正確的,不然截圖給我確認." Did exactly that —
rendered the L3 scene (our only same-robot table scene) + read prim bboxes.

**Screenshot (logs/l3_scene/l3_scene.png): floor grid, robot, two GREEN goal
markers, one tiny YELLOW cube floating in mid-air. NO TABLE visible.**

**Facts (L3, settled):**
- robot base world z = 0.0
- EE rest world z ≈ 0.26 (both hands)
- cube rest world z = 0.024 — floating, NOT on any surface
- TABLE world bbox z = [-2.09, -0.33] → its TOP SURFACE is at z ≈ −0.33,
  i.e. BELOW THE FLOOR. The code comment "top surface ends up at z=0" is
  WRONG.

**Root cause — L3 swapped the official table/robot z convention:**
- Official IsaacLab lift (ObjectTableSceneCfg): TABLE init pos=[0.5,0,**0**]
  (table origin at floor, its top ~1.05m up), ROBOT init pos=[0,0,**−1.05**]
  (robot dropped so its base sits at the table-top height). Net: table top ≈
  robot base + 1.05 = the arm's natural work height.
- Our L3 (pick_place_cfg.py:47): TABLE pos=[0.5,0,**−1.05**] (table shoved
  underground), ROBOT left at z=0. The −1.05 was applied to the WRONG asset.
  Result: table top at −0.33 (underground), cube floating at 0.024, arm based
  on the floor. push_s3a inherited this broken premise.

**This resolves EVERYTHING cleanly:**
- The 9-round "can't reach z=0.024" saga was never torque, orientation,
  lateral, or a real kinematic floor — it was that the workpiece sits ~24cm
  BELOW the arm's natural EE height because the table (which should lift the
  work to EE height) is underground. The reachability envelope was correct;
  the SCENE was mis-assembled.
- L3 was never run to success (no collect dumps) → the bug was never exposed
  until this contact work forced a real reach to the workpiece.

**Fix (matches PI's synthetic-data intent): assemble the work surface at the
arm's natural height, the OFFICIAL way, as a configurable asset:**
- Follow the official convention — either robot pos z=−1.05 (arm base at
  table-top) OR table raised so its TOP is at ~z=0 relative to a floor-based
  arm; net effect identical: cube contact height ≈ arm EE natural band
  (z≈0.20-0.30, which the envelope PROVED reachable, each arm owning its
  lateral side).
- Make table height / presence a cfg parameter (table_height, spawn on/off)
  so the background is swappable for synthetic-data domain randomization
  (PI's stated goal).
- Then the cube sits ON the table at the reachable band → contact geometry is
  valid → Pin-9 hybrid control (DiffIK transport + OSC contact) can proceed.

Screenshot evidence: logs/l3_scene/l3_scene.png (cube floating, no table).
Reported to PI for the assembly decision; NOT unilaterally rebuilt.

### 2026-08-24 Scene rebuild — Step 1 new-table USD health check (Pin-10 material) + PI-defined layout

New geometry (PI-defined, from visual inspection): table asset
localProps/Table_sor_1.usd at (0.55,0,0); robot base at (0,0,0.65); cube
centre (table-top + half-height) at base-frame z_b≈0.39 — lands near the
NEAR-verified servo band, the answer to "where should the work surface be."

**Step 1 USD health check (wp3a_table_usd_check.py, headless):**
- root valid, Xform, 17 subtree prims.
- **COLLIDER: PRESENT** (1) — /World/Table/packing_table/…/SM_HeavyDutyPacking
  Table_C02_01. Push has a real contact surface; no missing-collider trap.
- **Physics material: NONE on the asset** → friction inherits the sim default.
  IsaacLab RigidBodyMaterialCfg default = static 0.5 / dynamic 0.5,
  combine_mode="average". (L3 cube also sets no explicit friction — same
  inheritance.)
- **Table-top world z (bbox) = 0.9941** (measured, at table pos z=0). PI-stated
  ≈1.0197 differs by ~2.6cm — pending PI ruling on which datum to use; sim
  measures 0.9941 as the physical top.
- bbox x=[0.169,0.951] (Pin-4 x 0.40-0.60 is ON the table ✓);
  y=[-1.237,1.237] (both arms covered ✓).

**Pin-10 (contact-surface material — PENDING PI ruling, two points):**
1. Table-top datum: sim-measured 0.9941 vs PI 1.0197 (~2.6cm). Recommend
   sim-measured (what PhysX sees). Cube rests on top + half-height.
2. Friction: currently INHERITS sim default 0.5/0.5. Push physics IS friction,
   so recommend setting an EXPLICIT physics material on the contact pair
   (cube+table) so friction is a CONTROLLED KNOWN, not silently inherited —
   proposed static 0.6 / dynamic 0.5 (typical cube-on-table), to be PINNED
   here once the PI confirms. This value directly sets the push force budget
   that the 7 N·m distal must supply.

Both are contact-physics parameters that must be pinned BEFORE gen-0 data (a
changed friction mid-collection would confound r-tracking, per the freeze
clause). Awaiting PI ruling before Step 2 (cube physics) + Step 3 (coord z
updates).

### 2026-08-24 Scene rebuild — assembly verified (steps 2/3/5 PASS; step 4 needs a correct intersection test)

Rebuilt push_s3a (table Table_sor_1.usd @ (0.55,0,0), robot base z=0.65,
cube-on-table, explicit friction 0.6/0.5). Assembly-verify results:

- **robot base world z = 0.6500** ✓ (PI layout applied)
- **table top z = 0.9941** ✓ (sim-measured, PI ruling); x=[0.17,0.95]
  y=[-1.24,1.24] — Pin-4 region on the table, both arms covered.
- **cube half-height MEASURED = 0.0240** (constant assumed 0.0206 — DexCube
  edge is ~0.06 not 0.0515 at scale 0.8; corrected below).
- **cube settle DETERMINISTIC**: seed4700 == seed4700(rpt) to 0.00mm; rests
  2.40cm above table top = ON the table ✓ (step 2 PASS).
- **cube centre BASE frame z_b = 0.368** (PI expected ≈0.39; close — the
  0.0206→0.0240 half-height + exact table top account for it). Lands in the
  NEAR-verified servo band ✓ — the whole point of the rebuild.
- **camera framing**: screenshot logs/assembly/assembly.png shows table +
  cube-on-table + goal markers IN FRAME ✓ (step 5 PASS). Contrast the pre-fix
  shot (floating cube, no table).

**Step 4 (Pin-7 vs table intersection): my probe MIS-JUDGED — retracted.** It
compared "lowest robot body z vs table top" and flagged INTERSECT because
openarm_body_link (the torso/base) sits at z=0.65, below the table top 0.9941.
But a torso 34cm BELOW the table top is not a collision — it is the arm base
on its stand under/beside the work surface, exactly as intended. The screenshot
shows the arms clear above the table, no penetration. A correct test must check
horizontal bbox OVERLAP with the table AND vertical penetration, not a bare
min-z compare. Step 4 re-do pending with the right geometric predicate; visual
(screenshot) shows no intersection.

**Two corrections to fold in:**
1. cube half-height is 0.0240 (measured), not 0.0206 → _CUBE_REST_Z and the
   goal pos_z should use the measured value so the goal marker sits exactly on
   the cube rest height. (z_b 0.368 is fine either way — in band.)
2. the Pin-7 intersection probe predicate is wrong (min-z vs top); rewrite to
   bbox-overlap + penetration before claiming step 4.

### 2026-08-24 Scene rebuild — steps 2/3/4/5 ALL PASS (Pin-7 CLEAR with correct predicate)

Re-ran assembly-verify after two fixes (cube half-height 0.0206→0.0240
measured; Pin-7 predicate min-z→bbox-overlap+penetration):
- robot base z=0.6500 ✓; table top 0.9941 ✓; cube settle DETERMINISTIC (0.00mm
  same-seed), rests 2.40cm on table ✓; cube z_b=0.368 in NEAR band ✓;
  camera framing ✓ (table+cube+goal in frame).
- **Pin-7 standby: CLEAR** — no robot body penetrates the table AABB
  (x[0.17,0.95] y[-1.24,1.24] z[0.00,0.99]). The earlier INTERSECT was a
  probe-predicate bug (min-z vs top), now retracted; correct test PASSES. No
  Pin-7a needed — the working standby pose is collision-free with the new
  table.

Scene rebuild checklist status: 1 (USD health) ✓, 2 (cube physics) ✓, 3
(coord z updates in push_s3a) ✓, 4 (Pin-7 clear) ✓, 5 (camera framing) ✓.
Remaining: 6 (kinematic reachability sweep on NEW geometry — CONFIRM the
contact height z_b≈0.37 is in the reachable band; old sweeps void) → 7
(Pin-9a contact-gain on new pre-contact posture → hybrid primitive →
acceptance chain).

Pin-10 SEALED (contact-physics params, PI-ruled): table-top datum = sim
0.9941; cube rest z_b≈0.368; friction EXPLICIT static 0.6 / dynamic 0.5 on the
cube (set by assignment, spawn.physics_material). These are frozen for gen-0
(freeze clause).

### 2026-08-24 Step 6 reachability CONFIRM — UNEXPECTED: Pin-4 unreachable at contact height on new geom (baseline PASS)

Ran the L2 DiffIK instrument (orientation-free) on the rebuilt geometry
(table + base z=0.65). Baseline PASS both arms (L 0.2cm, R 3.2cm — instrument
valid; several harness bugs fixed en route: reset-jitter staleness in
self-ref baseline → read rest in-episode with do_reset=False; baseline vs
sweep tolerance split 4/3cm).

**Result: 0/15 Pin-4 cells reachable, either arm, at contact z_b=0.368.**
NOT the expected confirmation. Error-vector pattern (the diagnostic signal):
- dominant component is dx NEGATIVE (x undershoot): L reaches x≈0.29 rest but
  Pin-4 wants 0.40-0.60; at x≥0.55 dx≈-25..-31cm. R similar, dx≈-25..-44cm.
- near cells (L x0.40-0.50/y+0.15 → 4.6-8.7cm; R x0.45-0.50/y-0.15 →
  4.9-6.7cm) are CLOSEST but still >3cm.
- arm rest x is only 0.29 (L) / 0.17 (R); Pin-4 x 0.40-0.60 is 11-43cm beyond
  rest in x AND 28cm below base in z simultaneously.

**Honest read: raising the base to z=0.65 SHORTENED the horizontal reach to
the Pin-4 table region.** The "far + low" combination (reach out to x=0.40-0.60
AND down to z_b=0.37) exceeds the raised arm's envelope. The scene is now
physically assembled correctly (table, cube-on-table, base on stand), but the
Pin-4 x-region and/or the base height are not matched to each other.

This is NOT a controller/instrument issue (baseline servos to 0.2cm) — it is
a workspace-geometry mismatch between base height, Pin-4 x-extent, and contact
z, on the NEW layout. Candidates to resolve WITH the PI (not unilateral):
1. base z=0.65 may be too high — a lower base (e.g. 0.3-0.4) keeps the arm's
   natural x-reach over the table while the table (top 0.99) still lifts the
   cube to the EE band;
2. OR the Pin-4 region should move IN (x≈0.25-0.40, the reachable band the
   near-cells suggest) — but that is the domain-shrink question again, now on
   correct geometry;
3. OR the table should be closer (table x-pos < 0.55) so its usable top sits
   at reachable x.
Reported to PI with the envelope data + error vectors. Step 7 (Pin-9a) BLOCKED
until the contact workspace is confirmed reachable.

### 2026-08-25 Pin-7a standby (PI-tuned) + Pin-4a goal region −60mm + config-effect gate

**Pin-7a standby pose** — PI tuned it in the free-drive tuner on the rebuilt
scene (base 0.65, table). NOT symmetric, and correctly so: the arms mirror
physically (shoulder j2 opens opposite ways, elbow bends opposite ways), so
L/R joint values legitimately differ. Symmetry is NOT a correctness test —
my earlier "same-sign symmetric" assumption was wrong. Values (rad):
  L: j1 0.09 j2 -0.64 j3 0.13 j4 1.83 j5 -0.48 j6 -0.12 j7 -0.22
  R: j1 0.09 j2 0.43 j3 -0.03 j4 1.83 j5 0.33 j6 -0.21 j7 0.08
Set as a SINGLE module constant `_STANDBY_POSE` used by BOTH init_state AND
the reset event (no drift — the drift was the recurring bug). reset event
rewritten to apply it with ZERO jitter (constant body for r-tracking).

**Pin-4a goal region** — PI eyeballed: the farthest Pin-4 corners are reachable
but only at FULL arm extension. Shifted the whole goal region + cube start IN
toward the base by 60mm: goal x (0.40,0.60)→(0.34,0.54); cube start x 0.45→0.39.
So contact happens inside the comfortable envelope, not at full stretch.

**config-effect gate (scripts/diagnostics/check_config_effect.py)** — new
PERMANENT gate for the bug family that recurred 4× on the standby pose (cfg
value silently overridden/not-applied at runtime). Builds env → reset →
mechanically asserts runtime joint pose == cfg intent + two-reset determinism
(no jitter). PASS on the current cfg (14 joints match, deterministic). Any
geometry/pose/reachability conclusion is invalid until this gate passes.
Mirrors the check_eval_format_contract.py precedent.

**Audit of the bug class across the repo** (agent, read-only): only one other
active HIGH — osc_bi_leftposed_cfg.py sets a deliberate init pose but inherits
the stock reset_joints_by_scale(0.5,1.5) which randomly scales it every reset
(diagnostic-only cfg, no current use). No AionGenos main-line task besides
push_s3a sets a custom init_state.joint_pos, so the bug is not silently
replicated. Latent trap documented: `events.* = None` reverts to USD default,
not init_state. Future rule: any task setting init_state.joint_pos MUST also
rewrite reset_robot_joints, and run the config-effect gate.

**Next (step 6 re-run):** the reachability confirm must be re-run on this
corrected cfg (Pin-7a + Pin-4a −60mm) — the earlier step-6 fail used base 0.65
with Pin-4 at full x 0.40-0.60. With Pin-4a shifted in, re-confirm contact
height reachable before Pin-9a.

### 2026-08-25 WP1-③a INVENTORY + re-scoping — the mechanical layer is DONE; "command quality" is the model's job, not mine

Turning point (PI, watching the push GUI): "EEF fully reachable, posture
distorted, feels like the command is just given badly." That judgement
re-scopes everything and corrects my error of the last many rounds.

**What I was doing wrong:** manually playing teacher — hand-writing waypoints
(one-step absolute far targets, forced identity orientation). When I wrote bad
commands, OSC contorted the arm to force the bad target → distorted posture +
τ saturation → I then debugged the saturation as if the TASK/sim were broken.
It never was. I was debugging my own bad commands. Generating good commands is
the ENTIRE POINT of AionGenos (the teacher/model learns situation→action);
me hand-writing them either bypasses the research or manufactures fake bugs.

**Marginal vs conditional, corrected (founding-intent):** the APPROACH
trajectory shape (move_to / hover / descend primitives) is marginal (given
mechanical form); WHICH primitives to chain and with what waypoints/params is
CONDITIONAL — the teacher must learn it. Hand-writing a full hover-descend
approach = injecting conditional knowledge. So the "saturation from one-step
direct-slam" is not a bug to fix by hand — it's exactly the kind of bad
command a competent teacher learns NOT to emit. r-tracking is meant to watch
the teacher improve this across generations.

**WP1-③a mechanical layer — DONE (verified):**
- scene: real table (Table_sor_1.usd) at arm work height, cube-on-table,
  base z=0.55, deterministic settle (0.00mm), camera framing ✓
- standby: Pin-7a PI-tuned, applied via rewritten reset event (symmetric-not-
  required, zero jitter), config-effect gate PASS ✓
- standby holds under the FIRST servo command (HELD, τ 0.75) — the "collapse"
  was a zero-action artifact, not a real-rollout state ✓
- reachability: EEF reaches Pin-4a cells (PI human-verified in the tuner;
  full envelope) ✓
- OSC executes commands (impedance servo works when the target is sane) ✓
- Pin-10 contact material sealed (friction 0.6/0.5), Pin-4a goal −60mm ✓
- goal frame bug fixed (base-frame contact z 0.468, not world 1.018) ✓

**What is NOT mine to solve (the model's job, defer to teacher/rollout):**
- approach/command QUALITY (waypoint choice, chaining, when to hover-descend
  vs direct) — CONDITIONAL, the teacher learns it; my hand-written one-step
  slam is a deliberately-dumb stand-in that (correctly) fails.
- these are r-tracking's SUBJECT, not preconditions.

**Re-scoping decision:** stop hand-debugging approach waypoints. The
mechanical testbed is sufficient to carry the P2 experiment. Next step is to
connect the REAL teacher (model emits push-this-cube-to-here → push_toward
primitive → OSC), NOT to keep hand-writing better waypoints. The distorted-
posture/saturation the PI saw is the teacher's problem to learn away, which is
precisely what P2 measures.

**Process note (the recurring signature):** the PI's interventions — headless,
gripper, scene geometry, standby, "just bad commands" — are all cross-layer
abstraction judgements I could not make from the numbers. The last one caught
that I was solving the wrong layer entirely (hand-writing what must be learned).
That is the harness_grant_ledger's gap map in action: where a human still
supplies the abstraction the system can't yet reach.

### 2026-08-25 Q1 gravity-on re-verify — PASS (Pin-TODO closed; gen-0 gravity honest)

push_s3a now: arm disable_gravity=False + OSC gravity_compensation=True
(overridden in push_s3a, NOT osc_testbed, so the old no-gravity diagnostics
are untouched — isolation). cube physics unchanged. Pre-committed criteria:

- **STANDBY HOLD**: command the standby EE pose, sustained. peak τ/limit=0.61
  (mean 0.57), drift 2.7cm, EE_z 1.127 → PASS (≤0.85). Pin-7a holds under
  real gravity + compensation; no Pin-7b needed.
- **NEAR servo** (rest+12cm): min_err 2.9cm, peak τ/limit=0.53 → PASS.

**τ delta (sim-to-real material):** no-gravity/no-comp first-servo τ≈0.75 →
gravity-on/comp-on τ 0.61 (hold), 0.53 (near). Counter-intuitive but correct:
turning gravity ON while turning gravity_compensation ON *lowered* τ, because
the controller now feed-forwards the gravity load (knows the weight to hold)
instead of running blind. gen-0 gravity budget is comfortable, not tighter.

Pin-TODO (gravity re-verify) CLOSED. Proceed to Q3 (teacher scaffolding).

### 2026-08-25 Q3 canonical design SEALED + Pin-11 + gen-0 pre-reqs (PI ruling)

**PUSH_TO format (canonical, teacher-only ControlMode.PUSH_WAYPOINT):**
- `PUSH_TO: x,y` — 2D ONLY. z is not a decision variable (cube slides on the
  table; z owned by primitive/physics). Cuts a whole dimension of error
  surface, physically honest.
- integer, base-frame, SAME scale/units as LEFT_TARGET_POS (int_to_metric +
  WorkspaceBounds). "Student zero-change" = the tokenizer sees the same kind
  of number.
- one PUSH_TO per round; the primitive executes ONE bounded push segment
  (per-round cube displacement cap ~5-8cm, managed by the primitive's internal
  lead budget) then returns; teacher re-decides next round. The conditional
  decision surface ("where / how far / when to re-approach") lives in this
  loop — this is what r-tracking measures.
- Parser validation: PUSH_TO must fall inside the table workspace (Pin-4a
  region + margin); out-of-bounds = format violation → format-contract check
  (extend the gate, teacher-only branch).

**Two-leg error reveal (L0a Fix-3 convention):** two vectors (EE→cube,
cube→goal) revealed as base-frame integers, SAME scale as the output, oracle
source declared in-prompt. Symmetric with the reach prompt's reveal style →
one-sentence caveat covers both tasks in the P2 writeup.

> **CORRECTION 2026-10-05:** the "L0a Fix-3 convention" label is wrong. L0a's
> actual teacher condition is `prompts.py _S1_POS_HEAD`: EE positions + a
> scalar EE→target distance, NO object coordinates. The two-leg vector reveal
> is superseded by the PI ruling (image + proprioception only; disclosed
> scaffold = obs_rung ladder, rung 2 = the L0a scalar condition). See
> dual_collect_equivalence_ledger.md push-memory item 22.

**Pin-11 (success predicate + round budget, SEALED):**
- SUCCESS = cube centre within 0.05m of goal.
- round cap = 12 (distance budget: farthest ~36cm ÷ 5-8cm/round ≈ 6-8 rounds,
  ×1.5 margin).
- plateau termination: 3 consecutive rounds with cube displacement <1cm →
  end early, log 'plateau'.
- If these conflict with the Q5 containment probe, the probe wins; re-pin
  after.

**R1 probe — push analogue (DEFINED pre-data, prereg addendum):**
round-1 push-direction error = angle/deviation between the teacher's FIRST
PUSH_TO direction (from cube toward the emitted waypoint) and the OPTIMAL
cube→goal direction. Smoke is feasibility and does NOT use it; gen-0 does.
Written before any data seen (matched-tier discipline, like the reach R1).

**gen-0 pre-req flag (record now, execute before gen-0):** "student
zero-change" holds ONLY for smoke. Expert iteration REQUIRES the student to
eventually emit PUSH_TO itself → before gen-0 SFT, the student-side
constrained decoding + STAGE1 templates + format-contract gate MUST be
extended to include PUSH_WAYPOINT. This is a PLANNED controlled change (full
format-contract discipline, precisely because of that bug family's record) —
NOT a forbidden zone. Forbidden = "tweak it during smoke." Added to the gen-0
pre-req list.

**Q1 τ-reading flag (Rule 8, one-line verify, non-blocking):** the counter-
intuitive 0.75→0.61 (gravity ON lowering τ) must be checked: is the logged
applied_torque INCLUSIVE of the gravity-compensation feed-forward term? If yes
→ benign (pose near equilibrium), record one explanatory sentence. If no → the
τ budget accounting must be redone (real motor load = feed-forward + feedback).
To verify before trusting the budget.

### 2026-08-25 Q1 τ-flag RESOLVED (Rule 8) — applied_torque IS the real motor load

Verified (articulation_data.py:339): `applied_torque` = the torque the actuator
model actually applies to sim AFTER clipping. OSC's `_joint_efforts` (which
includes the gravity-comp feed-forward `joint_efforts += gravity`,
operational_space.py:479) → set_joint_effort_target → actuator → applied_torque.
So the logged τ INCLUDES the gravity-comp feed-forward = the real motor load
(feed-forward + feedback). → BENIGN branch: the 0.75→0.61 drop is physical —
without gravity/comp, OSC fights the pose on position-error feedback alone
(large error → high τ); with gravity ON + comp ON, the feed-forward cancels
the weight, the pose sits near equilibrium, feedback only trims → total τ
lower. τ budget accounting is CORRECT, no redo. gravity_compensation is
sim-to-real honest AND cheaper on τ.

### 2026-08-26 Pin-9 TRANSPORT phase ACTIVATED (contact phase stays pure OSC)

First end-to-end push episode ran (pipeline green) but execute_push_segment
slammed the absolute approach point in one step → OSC saw a ~40-60cm span →
pre-clip τ/limit 2.4-3.0 (numerical over-command), post-clip pinned 1.00,
servo_err 60cm, cube moved only 2.7cm then stuck (plateau). The live τ monitor
(Rule 9, now in collect) gave the decisive read: pre-clip 3.0 = a
transport-span pathology, NOT a hardware limit — exactly Pin-9's pre-committed
trigger. So this is mechanical execution of the pre-written fallback, not a
grey-area decision.

**Fix:** execute_push_segment's transport leg (standby → approach) now uses
CARROT-style segmented position servo (setpoint advances ≤δ toward approach
each burst, via the existing verified base_frame_target path — not new code);
OSC only takes over the CONTACT push from the approach point (its ±12cm
comfortable envelope). Pin-9 TRANSPORT phase = ACTIVATED; CONTACT phase stays
pure OSC.

**Two-layer accounting (PI, prevents a mislabel from this bug):** the earlier
philosophy ruling "the teacher must learn segmented approach" refers to the
PUSH_TO DECISION layer (where to push, how far). The standby→approach
TRANSPORT is primitive-internal mechanical common sense — Ledger entry (b)'s
existing scope, a harness obligation. The teacher's learning target is the
PUSH strategy, NOT "don't make the spring jump 40cm" — the latter is the
harness's job. This bug was a harness defect (my one-step slam), not a teacher
deficiency; do not conflate the two layers.

### 2026-08-26 Human-eye gate (PI 5th intervention) — identity-quat orientation pollution; contact orientation = f(push_dir), not a constant

PI watched the push servo GUI and diagnosed in one glance what the numbers hid:
"left wrist keeps hitting the table, won't rotate the wrist to bring the EEF to
the red target — instead the EEF gripper joint turns to FACE THE SKY." Root
cause: execute_push_segment commanded position + a HARD-CODED identity quat
[1,0,0,0], but identity = gripper-up for this arm. OSC fought to hold
"face-sky" against the position target → wrist hit table, gripper flipped up,
position stalled ~10cm short (the err_base 10-13cm plateau). NOT a reachability
limit, NOT OSC-transport awkwardness — a wrong orientation COMMAND. Same class
as the reach-sweep "identity quat pollutes position servo" bug; I repeated it.

This is the PI's 5TH cross-layer human-eye intervention (headless, gripper,
scene geometry, standby, now orientation) — all low-signal→structural leaps the
system couldn't make from numbers. The harness_grant_ledger gap map in action.

**Fix (PI ruling, revised after the PI overturned my constant-quat proposal):**
1. Contact orientation is a FUNCTION the primitive computes from the push
   direction (palm/contact-face toward the push dir; Pin-7a orientation as the
   null/reference basis, rotated about world-z to align with the push heading).
   NOT a constant, NOT teacher output. Gauge note: the choice among equivalent
   orientations = 0 bits; the direction-dependence = deterministic mechanical
   geometry, same family as approach-behind/IK — the primitive owns it.
2. Orientation stiffness softened to ~1/5 of position stiffness (position firm,
   orientation soft) so an imperfect orientation guides the wrist, not drags
   it. Value pinned in Pin-9a.

**Rule (executor no literal pose/quat constants):** executor code
(execute_push_segment) may NOT hard-code a pose/quat — orientation, like
position, comes from the primitive. Added to the format-contract dry-run as a
grep lint (executor files must not contain literal quaternion tuples).

**Two-frame servo_err bug also fixed:** push_collect's servo_err used
world-vs-base (the 66cm phantom); true base-vs-base error is ~13.5cm. Fixed in
execute_push_segment (ee_world − root vs tb).

### 2026-10-02 (correction) contact is PALM-push not finger-push; goal marker was hidden

**PI correction to the previous commit's wording.** The commit said the
orientation "aligns the gripper FINGERS" — WRONG. EE local +Z is the hand-link
forward direction; the actual FINGERTIPS are further out along +Z by an offset
(the gripper's triangular tip; openarm_left_ee_tcp sits +0.093 past the hand,
and the fingers extend beyond that). So the current behaviour is a PALM push
(contact at the hand/wrist-forward face), NOT a fingertip push.

Per the PI this is CORRECT for the current task: the prompt only says "push",
and a palm push is what a human would do. It would be WRONG only if the prompt
ever says "push with the fingertips" — in that case the target point must be
EXTENDED along +Z by the fingertip offset so the actual fingertips (not the
palm) make contact. Recording the offset's existence so a future "fingertip"
semantic does not silently become a palm push (a contact-point lie).

**Red line reaffirmed:** the finger-axis / tip-offset measurements are for EE-
local-frame calibration ONLY, never leaked into a prompt.

**GIF goal-marker bug:** to make the 4.8cm cube visible I disabled ALL command
visualizers (debug_vis=False) — but the GREEN GOAL marker is also a command
visualizer, so it got hidden too → the PI could not judge whether the cube
reached the goal. Fix: keep the goal cuboid visible, disable only the obstructing
pose AXES, so cube-vs-goal is visible in the GIF.

### 2026-10-02 rung-1 10-ep smoke — SR 0/10 → escalate to rung-2 (CONTROL-dominant failure)

Ran the pre-committed 10-ep rung-1 EEF smoke (seeds 4700-4709, label=pilot,
run bed0e663). Result: **SR = 0/10** → mechanical escalation to rung-2 per the
A-spec rung ladder (10-ep SR=0 → next rung).

Per-episode (min cube→goal / cube moved / saturated rounds):
- ep0 plateau 14.3cm / 3.3cm / 1-of-4 sat
- ep1 plateau 12.2cm / 0cm / 1-of-3
- ep2 plateau 19.7cm / 20.2cm / 9-of-9 sat
- ep3 plateau 31.9cm / 115.5cm(!) / 5-of-6 sat
- ep4-9 plateau 36-61cm / 0cm / 3-of-3 sat each

**Failure routing (pre-committed classes): CONTROL=8, INFORMATION=2, PHYSICS=0.**
Dominant class = CONTROL. Signature: the teacher emits EEF targets that are
too far / too high, so the arm maxes out (τ pre-clip ≥1.0 saturated nearly
every round) — the EEF target is often reachable-in-principle but the one-shot
EEF waypoint per round + the carrot transport can't deliver it in the step
budget, OR the teacher's targets wander far from the cube (ep3 moved the cube
115cm total yet never converged — flailing). ep0/ep1 are INFORMATION (teacher
targets miss contact, cube barely moves at low τ).

**Honesty on the n=2 pilot:** the earlier 1-success was genuine luck — the full
10-ep shows rung-1 the frozen teacher cannot reliably push. This is the
EXPECTED unstable gen-0 start; r-tracking's job is to show SR climb across
generations. The 0/10 is a baseline reading, not a harness failure (the one
clean success a26bd170 proves the pipeline CAN succeed when the teacher emits
good targets).

**Interpretation caveat (CONTROL-dominant):** before concluding "teacher
command quality", note 8/10 are τ-saturated — part of CONTROL here is that the
EEF-target → carrot-transport → OSC chain saturates when the teacher asks for a
far/high target in one round. This blurs "teacher asked badly" vs "executor
can't deliver a sane-but-far target". rung-2 (textual scaffold) addresses the
teacher side; if saturation persists under rung-2 with good targets, that's an
executor item (transport budget / multi-step). The τ monitor in collect is
what lets us keep these separable.

Human-eye gate: GIF logs/push_gif_bed0e663.gif (overlay cube→goal per round),
PI to view before the SR=0 reading is trusted / rung-2 is started.

### 2026-10-02 cube-reset bug — ROOT CAUSE + FIX (invalidates the SR=0/10 smoke)

**PI-caught** (watched GUI): the cube was NOT reset between episodes — it drifted
below/across the table cumulatively. PI ordered: dispatch an opus agent to find
the TRUE root cause BEFORE fixing. Done.

**Root cause (opus agent, file:line evidence):** IsaacLab's
`ManagerBasedRLEnv._reset_idx` (manager_based_rl_env.py:349-362) never restores a
RigidObject's spawn pose on its own — `scene.reset()` → `RigidObject.reset()`
(rigid_object.py:126-132) resets ONLY the external-wrench composers; it does NOT
write `default_root_state` back to sim. The ONLY thing that restores a rigid body
is an `EventTerm(mode="reset")` calling `reset_root_state_uniform`. The inherited
reach chain (ReachEnvCfg → AionGenosReachEnvBaseCfg → WP1ContactTestbed →
WP1PushS3a) had exactly ONE reset event — `reset_robot_joints` (robot-only) —
because the reach base never had a dynamic object. push_s3a added `scene.object`
(a RigidObjectCfg) WITHOUT a corresponding reset event → cube left wherever
physics shoved it. (The GOAL resampled every reset because command terms
self-resample in CommandManager.reset() independent of any object reset — hence
the asymmetry PI saw: goal moved, cube didn't.)

**This POLLUTES the SR=0/10 smoke (bed0e663):** per-episode first-round cube→goal
rose monotonically (ep0 14.3cm → ep5 61.4cm) = the cube accumulating drift, not
teacher behavior. Later episodes were unwinnable (cube off its spot / off table),
so the CONTROL=8 routing is partly a reset-bug artifact. **The 0/10 reading and
its failure routing are VOID.** rung-2 escalation is NOT yet justified — rung-1
must be re-run on the fixed env first.

**Fix (push_s3a_cfg.py):** added `self.events.reset_object = EventTerm(func=
mdp.reset_root_state_uniform, mode="reset", params={pose_range:{}, velocity_range:
{}, asset_cfg:SceneEntityCfg("object")})`. Empty ranges → every axis (0,0) →
deterministic restart at exact init_state (_CUBE_START_X, 0, _CUBE_SPAWN_Z), zero
velocity (freeze clause). Kept ORTHOGONAL to reset_robot_joints (did NOT use
reset_scene_to_default, which would re-apply robot state and fight the Pin-7a
standby event).

**Config-effect gate PASS** (verify_cube_reset.py): reset(4700) cube=(0.392,0.000,
1.018) → shoved to (0.671,0.310) → reset(4701) cube=(0.391,0.001,1.018), drift
0.15cm < 1cm → RESTORED ✓. Bug fixed.

**Latent twin:** L3 pick_place_cfg.py has the identical omission (scene.object at
line 52, no object-reset event). Flagged; fix when L3 push/pick is next touched.

### 2026-10-02 Q1 — does the teacher VISUALLY see the goal in its RGB? NO (design gap)

PI's challenge: "prompt 裡有寫座標 不代表 visual 看得到；要 visual 看得到才能正確
識別要怎麼推". My earlier answer (grep-based) guessed the command-visualizer
markers do NOT render into the sensor camera — **that guess was WRONG.** Probe
(goal_in_rgb.py, rendered the actual sensor RGB → logs/sensor_rgb_check.png):

- The command visualizers DO render into the tiled sensor camera (not GUI-only).
- BUT the "goal" is drawn as an **RGB coordinate-frame triad** (red-X/green-Y/
  blue-Z arrows), visually IDENTICAL to the two EE-pose triads also in frame.
  There are multiple triads; nothing marks WHICH one is the goal.
- There is **no distinct solid goal block** (the green/red pixels my heuristic
  counted were the axis ARROWS, not a goal cuboid).
- The yellow cube IS visible (small, center).

**Verdict:** the teacher CANNOT visually identify the goal — it can only know the
goal via the prompt's oracle TEXT coordinates. For a general-purpose zero-demo
visual-grounding VLA (π0 / Gemini-Robotics target), a text-only oracle goal is a
crutch that conflicts with the founding intent. **Design gap, not a quick fix:**
the scene needs a real VISIBLE goal marker (a distinct solid-colored flat
disc/decal on the table at the goal pose) that renders into the sensor RGB and is
unambiguous vs the EE triads — THEN the oracle text can be dropped (or kept only
as a scaffold rung). Deferred to a PI ruling: (a) add a visible goal decal now vs
(b) keep text-oracle for rung-1 baseline and add the visible marker as the
visual-grounding rung. Not starting either without the ruling.

### 2026-10-05 reachability math — table plane × BOTH arms (PI question)

PI asked, before any cube/goal randomization: is the green goal reachable, and
what is the pure-math intersection of the table plane with each arm's working
envelope? Ran the VALIDATED L2 DiffIK instrument (instrument rule) over the
table contact height z_B=0.468, sweeping x∈[0.28..0.58]×y∈[-0.30..0.30] for
LEFT and RIGHT (hold-orient pure-position servo, ≤4cm = reachable). Base-frame
kinematics is invariant to base world-height, so the L2 DiffIK envelope = the
push env's kinematic reach. (reach_table_both.py; log logs/reach_table_both.log.)

Base frame: +y = robot LEFT, −y = robot RIGHT. Result (min servo err cm; OK≤4):
```
LEFT arm (reaches +y side + center):           RIGHT arm (reaches −y side + center):
        x.28 .34 .40 .46 .52 .58                      x.28 .34 .40 .46 .52 .58
y-0.30   --  --  --  --  --  --              y-0.30   OK  OK  OK  OK  --  --
y-0.20   --  --  --  --  --  --              y-0.20   OK  OK  OK  OK  --  --
y-0.10   --  --  --  --  --  --              y-0.10   OK  OK  OK  OK  --  --
y+0.00   OK  OK  OK  --  --  --              y+0.00   OK  OK  --  --  --  --
y+0.10   OK  OK  OK  OK  OK  --              y+0.10   --  --  --  --  --  --
y+0.20   OK  OK  OK  OK  OK  --              y+0.20   --  --  --  --  --  --
y+0.30   OK  OK  OK  OK  --  --              y+0.30   --  --  --  --  --  --
```
Clean mirror symmetry: LEFT owns +y + center, RIGHT owns −y + center.

**Findings:**
1. **The CURRENT goal region is PARTLY UNREACHABLE.** Pin-4a goal x-range is
   (0.34, 0.54) — but x≥0.52 is marginal-to-unreachable (left-only, |y|≥0.1),
   and x=0.58 is unreachable by either arm. A sampled goal at e.g. (0.54, 0.0)
   is a ~14cm-unreachable dead cell. The goal region MUST be tightened to the
   measured envelope.
2. **Far-center dead zone:** (x≈0.46, y≈0.0) is unreachable by EITHER arm (left
   10.0cm, right 10.8cm) — the two envelopes don't overlap there.
3. **Fully-reachable-by-some-arm rectangle (no holes):** x ∈ [0.28, 0.40],
   y ∈ [-0.30, +0.30]. Beyond x=0.40 the center opens a gap and the sides
   shrink. Conservative sampling region with margin: **x ∈ [0.30, 0.40],
   y ∈ [-0.25, +0.25]** (reachable by ≥1 arm everywhere inside).
4. **Caveat:** this is KINEMATIC reach (DiffIK). OSC contact dynamics / torque
   under push load are a separate gate (the τ monitor); reach ≠ can-push-hard.

### 2026-10-05 LEFT baseline region locked + 3 bugs fixed before rerun (PI Option-1)

PI ruled: Option-1 (clean LEFT-arm baseline first, then build the embodied
cube-randomize + agent-picks-arm version "iii"). PI constraint: cube AND goal
must both lie in LEFT reach ∩ table. Getting there surfaced 3 real bugs (all
caught by the pre-rerun gates, none shipped):

1. **Old goal region was LEFT-unreachable.** _PIN4_Y=(−0.15,+0.15) and
   _PIN4_X→0.54, but the sweep proved the LEFT arm reaches NO negative y and
   nothing past x≈0.46 center. ~half the old goals were unwinnable — the other
   half of why the void 0/10 looked catastrophic (with the cube-reset bug).
   Fix: new LEFT box _LEFT_GOAL_X=(0.40,0.46), _LEFT_GOAL_Y=(0.12,0.22), all
   inside the measured LEFT envelope, forward-left of the cube (push away from
   body). New constants (NOT a mutation of the historical _PIN4_* which a
   diagnostic still imports).
2. **Cube spawned INTO the table.** _CUBE_SPAWN_Z = table_top+0.02 but
   half-height is 0.024 → 4mm penetration → solver popped it out laterally,
   sliding it ~4.5cm off config and non-reproducibly. Fix: spawn at rest+1mm
   (_CUBE_REST_Z+0.001), no penetration.
3. **Cube spawn collided with the standby LEFT hand.** First pick (0.32,0.14)
   was 6.4cm from the resting hand → hand shoved it 4.3cm with 0.94cm
   run-to-run non-determinism (freeze-clause violation). slide_diag showed all
   hand-clear spots (≥16cm) drift ~0 deterministically (table is level; slope
   hypothesis rejected). Fix: cube at (0.38, 0.06), 16cm clear of the hand.

**FINAL pre-rerun gate (final_gate.py) — ALL PASS:**
- cube start deterministic + stays put: t0=(0.380,0.060), settle=(0.380,0.060),
  drift 0.00cm, non-determinism 0.01cm → STABLE (freeze clause satisfied).
- all 10 seeds (4700-4709): cube≈(0.38,0.06), goal in the LEFT box, cube→goal
  8.5–14.8cm (all real pushes >5cm success radius), approach point reachable by
  the REAL push executor (5.4–6.6cm, within OSC reality) → OK.
- layout RGB logs/left_baseline_layout.png: cube + green zone both left, clean
  (triads gone), green zone forward-left of cube = natural left push.

Also fixed this session (recorded above): cube-reset EventTerm, visible green
goal disc, all command triads removed, prompt wording ("green zone").

**The void 0/10 (bed0e663) is superseded.** Re-running the pre-committed 10-ep
rung-1 smoke on this fixed env. New run id recorded on completion. Rung-2
escalation remains gated on THIS clean reading, not the void one.

### 2026-10-05 CLEAN rung-1 10-ep smoke — SR 0/10 (run 3ca3b769), awaiting human-eye gate

Re-ran the pre-committed 10-ep rung-1 EEF smoke on the validated-clean env
(cube resets ✓, spawn deterministic+stable ✓, cube/goal/approach all LEFT-
reachable ✓, visible green zone ✓, triads gone ✓, teacher gemma-4-31B up).
Seeds 4700-4709, label=pilot, GIF logs/push_gif_3ca3b769.gif, records
logs/push_smoke_3ca3b769.json.

**Result: SR = 0/10. ALL 10 episodes = PUSH_PLATEAU** (not timeout, not
off-table). This is a REAL baseline (the void bed0e663 0/10 is superseded).

Per-episode (start_cg = round-1 cube→goal; min_cg = closest ever; totdisp =
total cube motion; sat = τ-saturated rounds):
```
ep        outcome       rnds start_cg min_cg totdisp  sat
826af205  push_plateau   11   11.8    11.8   32.4cm  8/11
78fc18d1  push_plateau   11   14.4    14.4   24.0cm  3/11
ad1684ba  push_plateau    6   14.0    14.0    7.4cm  2/6
9dd6fece  push_plateau    7   17.5    17.5   10.9cm  2/7
f73179ec  push_plateau    7   13.5    13.5    7.7cm  2/7
d3d78a6d  push_plateau   11   16.6    11.1   19.8cm  3/11
5255216f  push_plateau   11   13.2     9.9   31.5cm  5/11
f660443d  push_plateau    7    9.3     9.3   11.8cm  2/7
c1ea083b  push_plateau    6   12.8    12.2   12.5cm  6/6
200a6d46  push_plateau   11   15.6    13.2   25.0cm  4/11
```

**Key signatures (vs the void run):**
1. **All episodes WINNABLE and stayed winnable** — start_cg 9.3–17.5cm (the gate
   held: no off-table, no unreachable goal, no cumulative drift). Contrast the
   void run (start_cg climbed to 61cm from the cube-reset bug). The env is now
   honest.
2. **The cube MOVES but does NOT approach the goal.** Mean total displacement
   18.3cm/ep, yet min_cg never drops below 9.3cm (success needs ≤5.0) and in
   6/10 episodes min_cg == start_cg (round 1 was the closest it EVER got — every
   later push made zero net progress). 0/10 episodes even reached within 8cm.
3. **τ saturation 43% of rounds** — present but NOT dominant (down from ~80% in
   the void run); the arm is pushing, just not productively.

**Pre-committed reading:** SR=0/10 → mechanical escalation trigger to rung-2 per
the A-spec rung ladder. BUT per the standing human-eye rule (3492b96) the SR is
NOT trusted and rung-2 is NOT started until the PI views the GIF. The "cube
moves 18cm but min_cg flat" signature is consistent with EITHER (a) teacher
emitting EEF targets that don't drive the cube goalward (INFORMATION), or (b)
the cube squirting off the side of the EE on contact (PHYSICS/geometry) — these
look identical in the numbers; the PI's eyes on the GIF disambiguate. I do NOT
judge the GIF.

### 2026-10-05 FORWARD-dominant geometry locked (PI steer: fix the pathological hard, keep conditional richness)

PI corrected the whole framing (recorded in rung1_smoke_criterion.md CORRECTION):
this smoke is a FEASIBILITY pilot with a FROZEN, NO-MEMORY teacher
(recap_buffer=None) — SR=0 is expected and carries NO rung-language signal; the
"10-ep SR=0 → rung-2" rule was MISAPPLIED to a no-learning pilot. The task's real
role (prereg §8b step 2) is to UNBLOCK a gen-0 collect so gen-0 r can be
estimated. The correct pilot criterion is the MVC cold-start test (§3a): can the
frozen generator get ANY success (>0) → can the task bootstrap gen-0.

The void+clean 0/10 runs both had a KINEMATICALLY PATHOLOGICAL geometry: cube at
low y, goal at high y, arm base at center → the LEFT hand had to reach AROUND the
cube to its body-side face and SWEEP it leftward (mean push angle 71°, 9/10
sideways). The cube squirts off the side on a sideways push → 18cm moved, min
cube→goal never <9cm. That is the WRONG kind of hard: it crushes SR without
adding the conditional richness r needs.

**Fix (data-driven, not guessed):**
- hand_map measured the standby LEFT hand/fingers at x≈0.21–0.27, y≈0.06–0.13,
  and a cube settle map: cube is shoved for x≤0.34 at mid-y but STAYS for all y
  at x≥0.38 → hand keep-out floor x≥0.38.
- New geometry: cube (0.38, 0.10); goal x(0.44,0.50), y(0.05,0.15) spanning
  AROUND the cube's y → FORWARD-dominant pushes with per-episode direction+
  distance variation (conditional signal preserved), no reach-around.

**fwd_gate re-gate — ALL PASS:** cube stable (drift 0.20cm, nondeterm 0.10cm);
all 10 seeds push angle 2–29° (mean 17°, forward-dominant), cube→goal 6.5–11.3cm
(real pushes >5cm success radius), approach points left-reachable (4.2–7.6cm) and
hand-clear (appr_y 0.07–0.12). Layout logs/fwd_layout.png: green zone directly
AHEAD of the cube, both left-reachable. Geometry LOCKED pending the gen-0 /
memory decision (prereg §2c FREEZE clause: body+geometry must be constant from
gen-0 until P2 collection completes).

**NEXT (PI decision pending):** the pipeline is feasibility-clean. The real
forward step is prereg §8b step 2 — wire the recap/memory buffer and run a gen-0
collect to estimate gen-0 r (the Δr-prior unblocker). SR=0 under a FROZEN teacher
is NOT the question; whether the task can bootstrap (MVC cold-start) and what
gen-0 r is, are. Reach-around + agent-picks-arm (iii) is a HARDER rung/task for
AFTER the memory→climb mechanism is shown on this bootstrappable task.

## 2026-10-05 (16:10) — Pin-4b region + two push-path instrument bugs (pre-freeze)

- **Pin-4b** (PI ruling): cube region x(0.38,0.42) y(0.05,0.15); goal = cube +
  (0.07..0.10, ±0.04) clipped to x(0.44,0.50) y(0.07,0.19) (fine left reach
  sweep `logs/reach_table_left_fine.log`: y≥0.07 reachable to x=0.50, y=0.05
  only to 0.46). `wp3a_pin4b_gate.py` 12 seeds ALL PASS (region/clip/static
  goal/determinism/approach reach); angle mean 8° max 19°; cube→goal
  7.1–9.8cm (`logs/pin4b_gate.log`, `logs/pin4b_layout.png`). Scripted
  closed-loop oracle 1/12 — informational, oracle is naive.
- **Bug 1 — silent auto-reset at 24 s** (720 env steps = round 8 at 90-step
  segments): cube/goal/robot re-sampled inside env.step, `truncated` never
  checked; run e81261c8 void (one cube launched 11.5m). Fix: push
  `episode_length_s=300`. Same latent behaviour in the frozen L0a path — see
  D11 Amendment 15 pin 8 (not changed there; pairing).
- **Bug 2 — biased push deltas**: EE_TO_CUBE / CUBE_TO_GOAL were computed by
  passing a METRIC delta through the POSITION int map, whose x-axis has an
  offset (0 m ↦ −33). A goal 9cm ahead read dX=−13 ("behind"). Run 579329e1
  (post bug-1 fix): teacher never drove +x; cube pushed away (→17–19cm). Fix:
  delta = difference of grid positions (dX=+20 for the same layout). Also the
  output line said "integer cm" — it is the position grid (x 0.45cm/unit,
  y 0.4cm/unit); label corrected. Both runs e81261c8 + 579329e1 are VOID for
  the eye gate; gate (a) re-run on the fixed instrument.
- **Eye-gate (a) candidate run 098975dd** (both bugs fixed, no memory, seeds
  4700–4702): 0/3, all push_plateau after 3 rounds. Teacher now reads dX=+20
  correctly and aims behind the cube in x/y, but keeps the hand at the
  standby height (Z≈0.518 m base vs cube centre 0.468, top 0.492): the
  prompt reveals CUBE_POS as (X,Y) only, so contact height is never given —
  the horizontal fingers pass over the cube (cube moved ≤0.4cm). Open PI
  question (not changed): is contact height a marginal grant (reveal cube Z)
  or a lesson for memory to earn? GIF `logs/push_gif_098975dd.gif`.

## 2026-10-05 (17:05) — observation interface returned to design (PI ruling)

Photos + proprioception only; object positions are perception. Stage-1, recap
and retrieval carry no GT at rung-1 (GT only in the success predicate and
offline analysis). EEF reference = TCP (live-measured hand-local offset);
orientation = rest pose (Pin-7a) rotated by base-axis ORI —
`neutral_contact_orientation_b` retired from the push path. Rung ladder =
observation scaffolds (wp3a_pilot_plan.md). Eye-gate candidate 098975dd and
the Z question are superseded (that prompt was rung-3-like).

**6D pose-path probe** (`wp3a_ori_probe.py`, `logs/ori_probe*.log`; command
path = push_collect's): rest 0.3°; P+45 → 42.6° about base y (err 6.0°);
R+30 → 30.0° about base x (0.2°); Y+15 → 14.8° (0.8°); Y−30 → 30.2° (0.3°);
**Y+30 → FAIL: 22.6° tracking error, achieved rotation about a mixed axis
[−0.68,0.13,0.72]** — positive yaw beyond ~+15…30° is not trackable from the
rest pose (body limit, cause not yet isolated: joint limit vs OSC). τ pre-clip
saturates only at step 0 (reset transient, identical in the rest probe);
≤0.46 after step 20. Per-step orientation error is now logged by
execute_push_segment beside the position error.
- **Rung-1 3-ep run 3577d85e** (photos + proprioception, memory OFF, seeds
  4700–4702): 0/3 (plateau R3, R3, R7). Contact report: in 8 of 9 early rounds
  the cube never moved (TCP→cube min 7–24 cm). Teacher TCP targets sat far
  short of the table/cube (x 0.15–0.24 vs cube ≈0.41) and LOW (z 0.28–0.42;
  table contact height 0.468) — reached by the servo (TCP err ≤0.6 cm), i.e.
  the hand went below table-top level at the near edge. ep 537ef9ab R3:
  target x0.15 z0.28 unreachable (TCP err 35.6 cm, ori err 60°), a finger
  touched the cube (first motion, finger, 2.2 cm); R4 the cube was knocked
  45 cm by the wrist (link6) at step 0. Honest rung-1 x=0: no image↔grid map
  is given. GIF `logs/push_gif_3577d85e.gif` (tag strip below the scene).
- **Pre-pilot (PI 2026-10-05):** ladder re-ordered 1 → 1b (depth / second
  view = sensors) → 2 → 3; table-collision interlock added (measured table box
  base x 0.169–0.951, top z 0.444; guard check PASS: into-table target clamped,
  TCP final z 0.472; before-edge target untouched); Y+30 limit recorded as a
  known body limit, not blocking.
- **Interlock = full static scene** (PI): table top (base x 0.169–0.951, top
  z 0.444), robot body link box (x −0.155…0.095, y ±0.095, z 0…0.773), ground
  (z −0.55). Check PASS: into-table → lifted to z 0.454; into-body → projected
  to x 0.105; before-edge low target untouched. No stand prim in the scene.
- **A15 start (Rule 2):** the 18:00 waiter never fired — its
  `pgrep -f run_push_collect.py` matched its OWN bash command line, so it
  waited forever (seen 18:18: empty log, no process). Waiter killed (PID
  verified), driver launched manually 18:19; cost re-measure running first.

## 2026-10-06 — pilot step (c), rung-1, memory ON, 50 ep (run e4aebf36, seeds 5000–5049)

- **Successes 0/50** (all push_plateau, all exactly 3 rounds: the plateau rule
  ends an episode after 3 rounds of no cube motion). **Pre-registered rule:
  0 < 5 → rung-1b** (mechanical).
- **Contact report**: the cube moved in 0/150 rounds, 0/50 episodes; TCP→cube
  closest approach per episode median 5.0 cm, min 1.6 cm, 0 episodes within
  1 cm. Static-scene guard clamped 26 targets (all table).
- **Memory / Q7**: 50/50 recaps written (median 95 words, 0 empty); retrieval
  injected past recaps in 49/49 episodes after ep0. Lessons are generic and
  partly CONFABULATED: at rung-1 the recap sees only success/failure + TCP
  targets, and several lessons assert the cube was "pushed away from the goal"
  although GT shows it never moved. Q7 = lessons are produced, but at rung-1
  they are not grounded in what happened.
- **r-estimator variance** (exploratory 4×4 (c, s) grid, nothing pinned): no
  candidate above its permutation band; bootstrap σ(r) = 0.13–0.15 at n = 50
  (band half-width ≈ 0.27–0.30). Report: `logs/pilot_report_e4aebf36.json`.

## 2026-10-06 — PI rulings after the rung-1 pilot

- **Rung-1 fact (50-ep measured):** a frozen VLM cannot infer grid depth/x-y
  from a single oblique RGB — 0 contacts, 0 cube displacement, closest
  fingertip approach 1.6 cm over 50 episodes.
- **MVC law, 4th instance — recap confabulation (P2 Discussion candidate):**
  memory-WRITE quality is bounded by the perception floor. At rung-1 the recap
  cannot perceive the outcome, so it invents one ("the cube was pushed away
  from the goal" while GT shows the cube never moved). Recall the three prior
  instances (teacher / buffer / student floors); this is the write-side one.
  Re-measure the confabulation rate at rung-1b against the contact report.
- **rung-1b = second-viewpoint (top-down) RGB camera; NO depth** (depth
  encoding is an untested hypothesis → rung-1c). **Pin-11 (camera extrinsics):**
  fixed world mount, base-frame position (0.40, 0.06, 1.25) m (~0.8 m above
  the table top), optical axis straight down (world-convention quat
  (0.70711, 0, 0.70711, 0); image top = robot +x), pinhole focal 45 mm /
  aperture 45 mm (≈53° FOV), 256×256 RGB = main camera resolution
  (`push_s3a_cfg._TOPCAM_*`). Check `wp3a_topcam_check.py` PASS (cube and goal
  visible at 4 seeds; `logs/topcam_views.png`). Prompt adds one sentence
  naming the view; no coordinate semantics.
- **Pin-12 (plateau arming, rung ≥ 1b):** the plateau counter starts only after
  the first contact (cube moved); before that, rounds count only toward the
  12-round cap. Rung-1's rule (3 rounds) stays as run — with zero contact it
  acted as a 3-round cap for all 50 episodes.
- **[PWR-SIM]:** σ(r) ≈ 0.13–0.15 @ n = 50 noted; NOT filled until the PI pins
  one (c, s) pair from the 16-candidate exploration, after rung-1b contact data.

## 2026-10-07 — pilot step (c), rung-1b (top-down view), memory ON, 50 ep (run 30f15f0c, seeds 5000–5049)

- **Successes 0/50** (49 timeout at the 12-round cap, 1 plateau — Pin-12 arming
  worked: plateau counter only armed after contact). **Pre-registered rule:
  0 < 5 → rung-2** (mechanical, PI pre-authorized).
- **Contact report**: cube moved in 2/595 rounds, 2/50 episodes; both first
  contacts = WRIST (link7 / link6), incidental, not a fingertip push: in ep 15
  R5 and ep 44 R12 the TCP target was far below the table top at the near edge
  (z 0.28 / 0.245 vs top 0.444, x 0.15) and the arm swept into the cube. TCP→cube
  closest per episode median 5.5 cm, min 3.9 cm, 0 within 1 cm. Scene guard
  clamped 89 targets.
- **Target pattern (diagnostic):** the teacher's TCP targets cluster at
  x = 0.15 m = grid X 0 and z = 0.35 m = grid Z 0 (and lower) — i.e. it emits
  grid-centre/zero values; the top view did not give it an image→grid mapping.
- **Recaps / Q7**: 50/50 written (median 94 words, 0 empty). Confabulation on
  the 48 recaps whose episode had NO cube motion: assertive 20/48 = 42%
  (keyword 46/48) — vs rung-1 22/50 = 44%. The top view did not reduce it.
- **r-estimator**: bootstrap σ(r) 0.115–0.150 @ n = 50; 4 of 16 exploratory
  (c, s) candidates above their band (≈0.8 expected by chance at 5% × 16 —
  forking paths; no claim, nothing pinned).
- PI view: per-round GIFs (front | top + contact strip) of the only two contact
  episodes: `logs/rung1b_contact_15_fdc85b67-ca9.gif`,
  `logs/rung1b_contact_44_dc5061e5-e7c.gif` (pilot ran without fine-frame GIF;
  per-round dumps only — future pilots run with GIF on).
- **A15 ops:** B_main finished 01:46 (13c5c402, 53/100, readonly gate OK);
  D_gist did NOT start — the reload ssh to 10.80.9.148 failed
  ("kex_exchange_identification: Connection reset"), port 22 open but sshd
  resets every handshake (still at 12:30). llama-servers up over HTTP.

## 2026-10-07 (afternoon): GPU host reboot, rung-2 run voided, D_gist started, PI amendments

### GPU host reboot
- The PI rebooted host 10.80.9.148 at about 13:18.
- My earlier ssh failures were partly my own error: I connected as `control@`,
  but the host account is `exx@` (`REMOTE_HOST` in `run_a15_night.sh`).
- After the reboot no llama-server was running. I restarted both with the
  repo scripts and changed no config:
  - teacher: `server/llama_server_teacher.sh`, port 18888, layer split over
    3 GPUs;
  - student: `server_side/reload_student_dual.sh`, port 18889, GPU0.
- GPU placement is identical to `logs/cost_remeasure_run_*.log` from 10-05.

### Adapter integrity before D_gist
- A_ctrl_rat SFT/KTO sha256 are identical to the handoff 7229335 values
  (`4807767d…`, `7f7f7363…`). The disk is intact after the reboot.
- D_gist has no earlier recorded hash. Recorded now:

| Adapter | sha256 | Size | mtime |
|---|---|---|---|
| `data/lora_gguf/d11_D_gist_sft/adapter.gguf` | `dba178f3f974b8c90d63667bdc2c9d74a5e9eff512335ca3f14e977ba059ff85` | 489,774,208 B | 2026-07-11 01:59:23 (D11 export, unchanged) |
| `data/lora_gguf/d11_D_gist_kto/adapter.gguf` | `d5ebc32f1645a01e7ffc01e9cc1454161d5b947928955cc7f85b75b21801dfd6` | 489,774,208 B | 2026-07-11 01:59:23 (D11 export, unchanged) |

- `/lora-adapters` lists exactly these two files, at scale 1.0.

### A15 D_gist started manually
- Started at 13:37 by PI order:
  `run_a15_night.sh --ignore-window`. Pre-flight passed (lock, buffer tar
  and tree hash). The cost re-measure and arms a/action_only/B_main were
  skipped as already complete.
- Run `fdb2a9b0`, log `logs/a15_b_D_gist_ret_20261007_133730.log`.
- I stopped the 18:00 waiter (PID 4097775, cmdline verified) so that it
  cannot start a second driver while this one is running.

### rung-2 run 73210d6a VOIDED
- Teacher connection lost at 13:22 because of the host reboot.
- Episodes 0–12 ran (13 timeouts, 0 successes). ep13 was cut at R12.
  ep14–49 are `vlm_parse_fail` with 0 rounds.
- This is not a valid 50-episode pilot.
- The buffer `workspace/recaps_push_pilot_rung2` (13 recaps) is kept as
  data and not reused.
- Re-run started at about 13:41: same seeds 5000–5049, a fresh buffer
  `workspace/recaps_push_pilot_rung2_r2`, GIF on.
  - PID is in `logs/pilot_rung2r2.pid`.
  - It runs concurrently with D_gist on the local GPU (12.3/20 GB).
  - D_gist and the pilot use different servers, so they do not compete for
    the model.

### PI amendments (2026-10-07)
- **rung-2 → rung-3 is no longer mechanical.** If rung-2 has < 5 successes,
  stop and report to the PI. rung-3 needs PI consent and a Ledger entry.
  Recorded in `wp3a_pilot_plan.md` and `wp3a_pilot_report.py` `NEXT_RUNG`.
- **New rung-2 diagnostic:** the (x, z) distribution of teacher targets
  across rungs 1, 1b and 2. Tool: `scripts/analysis/wp3a_target_hist.py`.
- **Recap honesty guard** proposed as P2 prereg §2d, awaiting PI approval.
  The pilot buffers are not cleaned.

## 2026-10-08 — pilot step (c), rung-2 (scalar distances), memory ON, 50 ep (run 3e8c52d4, seeds 5000–5049), valid re-run

**Validity.** The run had 0 VLM connection failures, 50/50 episodes and 594
rounds. It replaces the voided 73210d6a.

**1. Successes: 0/50** (48 timeout, 2 plateau).
- **PI rule of 10-07 applies: STOP. No rung-3.** Reported to the PI for
  re-deliberation.

**2. Contact report**
- The cube moved in 2/50 episodes (2/594 rounds).
  - ep0 R5: wrist, incidental, 4.0 cm.
  - **ep18 R7: FINGER (TCP link)**, the first fingertip push in WP1-③a.
    - It is the 1st fingertip push in 50 + 50 + 50 pilot episodes.
    - The cube moved 3.2 cm, mostly sideways, and cube→goal changed
      9.8 → 9.0 cm.
    - The teacher's raw target was below the table top (z 0.385). The scene
      guard lifted it to 0.454.
- TCP→cube closest per episode: median 5.2 cm, min 0.67 cm. **3 episodes
  within 1 cm** (ep2 0.80, ep18 0.67, ep43 0.95). rung-1b had 0.
- Scene guard target clamps: 76.

**Fine-frame GIFs for the PI** (first human-eye gate). These are the first
3 episodes meeting the PI criterion (fingertip < 1 cm, or a fingertip push).
Front camera, every 9 servo steps, round + GT strip.
- Files:
  - `logs/rung2_fine_ep02_84fc24e9-867.gif`
  - `logs/rung2_fine_ep18_144fd969-e61.gif`
  - `logs/rung2_fine_ep43_952305a3-cf5.gif`
- Each GIF has a per-round contact report beside it (`*_contact.json`).
- How they were cut: from the run GIF, at exactly 10 frames per round. The
  90-step segment is captured at steps 0, 9, …, 81, and 5940 frames = 594
  rounds × 10. The split was checked on the ep18 R6/R7/R8 strip.

**3. Target distribution** (`wp3a_target_hist.py`; `logs/wp3a_target_hist.{json,png}`)

| Rung | X at 0 | Z at 0 | X0 & Z0 | Distinct X / Z | Median \|target−cube\| X / Y |
|---|---|---|---|---|---|
| 1 | 31% | 9% | 9% | 14 / 16 | 33 / 12 |
| 1b | 68% | 21% | 16% | 18 / 30 | 55 / 30 |
| 2 | 26% | 5% | 4% | 37 / 38 | 23.5 / 17.5 |

- rung-2 **leaves grid zero**: the Z-zero mass drops 21 → 5%, the number of
  distinct values doubles, and targets are about 2× closer to the cube than
  at rung-1b.
- The round-1 target does **not** track the cube position:
  - Spearman X −0.13, Y −0.14.
  - Expected: a scalar distance carries no direction before the first
    action.
- Within an episode the scalar is **not** used to close in:
  - TCP→cube (xy) after R1 has median 10.6 cm; at the last round it is
    23.8 cm.
  - Only 5/50 episodes end closer than after R1.
- Reading: the distance scalar moves the teacher off the grid-centre prior,
  but it does not act as a closed-loop anchor.

**4. Recaps and confabulation**
- 50/50 written, median 96 words.
- The heuristic flags 5/48 as assertive (keyword 39/48).
- **I hand-read all 5. All are false positives:** "Subsequent targets moved
  further away" refers to the TCP, and "LESSON: … push directly toward the
  goal" is an imperative that matched "toward".
- **True confabulation 0/48**, against 44% at rung-1 and 42% at rung-1b.
  - The recaps quote the distance scalars ("the cube remained stationary,
    7.6 cm from the goal").
  - Consistent with MVC: the recap is honest once the outcome is perceivable.
- The opposite error also exists. ep0's recap says the cube "remained
  stationary", but the wrist moved it 4.0 cm. This is under-reporting.
- Input for §2d (honesty guard):
  - the assertive detector needs an imperative/LESSON exclusion;
  - the guard should also catch "cube did not move" when it did.

**5. r-estimator:** bootstrap σ(r) 0.126–0.153 @ n = 50. 4/16 candidates are
above band, at chance level; c/s are still not pinned.
