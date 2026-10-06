# WP1-③a — real bimanual push (cube = DYNAMIC pushable RigidObject).
#
# Builds on the VERIFIED-GREEN OSC test-bed (WP1ContactTestbedEnvCfg: boots +
# servos to 2.14cm + seed-paired) and adds the one thing that makes it a
# CONTACT task: a dynamic DexCube the arms push. Provenance (success
# predicate, physics, controller) pinned in docs/p2_prereg/wp3a_push_provenance.md
# BEFORE this file. Closes the 2026-06-02 first-commit push ticket.
#
# NOT a new primitive: the push is OSC impedance move_to (WP1-①). Wrench axes
# stay OFF (that's ③b press). Stiffness raised toward the ≥30-step HOLD gate
# (Pin 1); the exact tuned value is re-pinned in provenance before first data.

import isaaclab.sim as sim_utils
import isaaclab.envs.mdp as mdp
from isaaclab.assets import RigidObjectCfg, AssetBaseCfg
from isaaclab.managers import EventTermCfg as EventTerm
from isaaclab.managers import SceneEntityCfg
from isaaclab.markers import VisualizationMarkersCfg
from isaaclab.sim.spawners.from_files.from_files_cfg import UsdFileCfg
from isaaclab.sim.schemas.schemas_cfg import RigidBodyPropertiesCfg

from .cube_relative_goal import CubeRelativePoseCommandCfg
from isaaclab.utils import configclass
from isaaclab.utils.assets import ISAAC_NUCLEUS_DIR

# Visible GOAL marker (2026-10-02, PI ruling a-1/a-2): the goal must be a REAL
# visible target the teacher can SEE in the sensor RGB — not a coordinate-frame
# triad (there is no such thing in the real world, and the three identical
# triads were visually indistinguishable). A flat green disc lying on the work
# surface = the "green zone" the prompt instructs the teacher to push the cube
# onto. Renders into the tiled sensor camera (verified: command markers DO
# render into the RGB).
_GREEN_GOAL_MARKER_CFG = VisualizationMarkersCfg(
    markers={
        "goal_zone": sim_utils.CylinderCfg(
            radius=0.05,
            height=0.004,            # a flat disc / decal, not a post
            visual_material=sim_utils.PreviewSurfaceCfg(diffuse_color=(0.0, 0.9, 0.1)),
        ),
    }
)

from aiongenos.tasks.WP1_contact_testbed.osc_testbed_cfg import WP1ContactTestbedEnvCfg

# ── Scene-rebuild geometry (2026-08-24, PI visual-inspection layout) ─────────
# Root cause of the 9-round reachability saga: NO table existed; the cube sat
# on the floor (z=0.02) while the arm base was also on the floor, so contact
# meant folding the arm to its own feet. Fix: a real work surface at the arm's
# natural EE height + the arm base raised onto a stand. All geometry here is
# base-relative-safe (interface/eval/bounds/camera all subtract root — recon
# 2026-08-24); only these absolute-z literals change.
_TABLE_USD = "/home/control/AionGenos/localProps/Table_sor_1.usd"
_TABLE_POS = (0.55, 0.0, 0.0)          # PI-defined table placement
_TABLE_TOP_Z = 0.9941                  # sim-measured bbox top (PI ruling: use sim value)
_ROBOT_BASE_Z = 0.55                   # PI-defined 2026-08-25: 0.65 too high to reach; 0.55 makes all Pin-4a corners human-verified reachable
_CUBE_HALF_H = 0.0240                  # DexCube half-height at scale 0.8, MEASURED via bbox (assembly-verify 2026-08-24)
_CUBE_REST_Z = _TABLE_TOP_Z + _CUBE_HALF_H          # ≈1.0181 WORLD (cube centre at rest, matches settle)
# Spawn 1mm ABOVE rest (NOT the old table_top+0.02: half-height is 0.024 > 0.02,
# so that spawned the cube 4mm INTO the table → solver popped it out laterally,
# sliding it ~4.5cm off its configured (x,y) and making the start non-reproducible
# — caught by the leftbox gate 2026-10-05). At rest+1mm it drops 1mm and stays.
_CUBE_SPAWN_Z = _CUBE_REST_Z + 0.001                # WORLD; no penetration, deterministic
# BASE-FRAME contact height = world rest − base z. The command term's ranges
# are in the ROBOT BASE FRAME (IsaacLab UniformPoseCommand generates in base
# frame), so the goal pos_z MUST be this base value, NOT the world _CUBE_REST_Z
# (the frame bug that sent the push target 0.55m too high → arm missed cube).
_CUBE_REST_Z_B = _CUBE_REST_Z - _ROBOT_BASE_Z       # base-frame contact height ≈0.468
# Contact-surface friction (Pin-10, PI ruling): EXPLICIT, not sim-inherited.
_FRICTION_STATIC = 0.6
_FRICTION_DYNAMIC = 0.5

# Pin-4a (2026-08-25): the PI eyeballed the standby tuner — the farthest Pin-4
# goal corners are reachable but only at FULL arm extension. Shift the whole
# goal region (and the cube start) IN toward the robot by 60mm so contact
# happens inside the comfortable envelope, not at full stretch.
_PIN4_INSHIFT = 0.06        # move goal region + cube −60mm in x (toward base)
_CUBE_START_X = 0.45 - _PIN4_INSHIFT   # = 0.39
# Pin-4a goal region — SINGLE SOURCE OF TRUTH. Any probe/diagnostic that needs
# the goal range MUST import these (not read a different env's inherited range,
# which was the drift that made the reach-confirm sweep test the wrong region).
_PIN4_X = (0.40 - _PIN4_INSHIFT, 0.60 - _PIN4_INSHIFT)   # (0.34, 0.54)

# ── LEFT-ARM clean baseline region (2026-10-05, PI ruling: Option-1) ─────────
# The old Pin-4a goal region (_PIN4_X/_PIN4_Y) is UNSAFE for a left-only push:
# the reachability sweep (reach_table_both.py, provenance 2026-10-05) proved the
# LEFT arm cannot reach ANY negative y on the table, and nothing beyond x≈0.46 at
# the center — yet _PIN4_Y was (−0.15,+0.15) and _PIN4_X went to 0.54. So ~half
# the old goals were LEFT-unreachable → guaranteed-unwinnable episodes (the other
# half of why the void 0/10 looked so bad, alongside the cube-reset bug).
# PI ruling: for the left baseline, cube AND goal AND the behind-cube approach
# point must ALL lie in LEFT reach ∩ table. Measured solidly-reachable left zone
# (servo 0.0cm): y≥+0.10, x≤0.46. These constants encode a margin-safe box inside
# it; a config-effect gate (reach_leftbox_confirm) verifies every sampled
# (approach,cube,goal) triple is left-reachable before data. The embodied
# cube-randomize + agent-picks-arm version (iii) supersedes this when built.
#
# ── FORWARD-dominant left baseline (2026-10-05, PI steer) ────────────────────
# The (0.38,0.06)+goal(0.40-0.46, 0.12-0.22) geometry made 9/10 episodes a
# SIDEWAYS/reach-around push (mean cube→goal angle 71° from forward): cube at
# low y, goal at high y, with the arm base at center forced the LEFT hand to
# wrap AROUND the cube to its body-side face and sweep it leftward — the most
# awkward contact for the left arm, and the cube squirts off the side (18cm
# moved, min cube→goal never < 9cm → SR 0/10, run 3ca3b769). PI: that is a
# KINEMATICALLY PATHOLOGICAL hard, which crushes SR WITHOUT adding the
# conditional richness r-tracking needs — the wrong kind of hard.
# New design: cube NEAR the robot + left, goal AHEAD (higher x), y spanning
# AROUND the cube's y → every push is FORWARD-dominant (contact stable), while
# per-episode direction+distance still VARIES (the conditional signal r wants).
# Reach-around is deferred to a harder rung/task once the mechanism (memory →
# SR/r climb) is shown on a BOOTSTRAPPABLE task (prereg §3a cold-start floor).
# All points verified LEFT-reachable + hand-clear by reach_table_both +
# final_gate (re-gated on this geometry before any gen-0 collect).
#
# Positions chosen from MEASURED data (hand_map 2026-10-05), not guessed:
#  - standby LEFT hand/fingers cluster at x≈0.21–0.27 → cube settle map shows
#    the cube is shoved for x≤0.34 at mid-y, but STAYS for ALL y at x≥0.38.
#    So cube x MUST be ≥0.38 (hand keep-out). → _CUBE_START_X=0.38.
#  - left reachable-on-table (reach_table_both): y≥0, x≤0.46@y≈0, x≤0.52@y≥0.1.
#  - cube y=0.10, goal y spans (0.05,0.15) AROUND it → forward-dominant pushes
#    (max angle ~40°, dist 8–13cm), per-episode direction+distance variation
#    (the conditional signal r wants), all left-reachable, cube+approach
#    hand-clear. Re-gated by fwd_gate before any gen-0 collect.
#
# Pin-4b (2026-10-05, PI ruling): the cube spawns in a REGION, not a point — a
# single cube pose leaves only the goal's 2D as situation space, too thin for r.
# The goal is sampled RELATIVE to the cube (CubeRelativePoseCommand), so every
# push stays forward-dominant while direction + distance vary per episode.
# Bounds from MEASURED data: hand_map (x≥0.38 stays for all y) and the fine
# left reach sweep logs/reach_table_left_fine.log (y≥0.07 reachable to x=0.50;
# y=0.05 only to x=0.46). Goal clip keeps the push END (≈goal−3cm) reachable.
_CUBE_REGION_X = (0.38, 0.42)    # hand keep-out floor 0.38
_CUBE_REGION_Y = (0.05, 0.15)
_CUBE_START_X = sum(_CUBE_REGION_X) / 2   # region centre = init_state; reset event samples ± half-width
_CUBE_START_Y = sum(_CUBE_REGION_Y) / 2
_GOAL_OFFSET_X = (0.07, 0.10)    # goal − cube: AHEAD; min 7cm > 5cm success radius (no pre-solved ep)
_GOAL_OFFSET_Y = (-0.04, 0.04)   # ≤30° off forward
_GOAL_CLIP_X = (0.44, 0.50)      # left-reachable box for the goal
_GOAL_CLIP_Y = (0.07, 0.19)
_PIN4_Y = (-0.15, 0.15)

# Pin-7a (2026-08-25): standby pose TUNED BY THE PI in the free-drive tuner,
# on the rebuilt scene (base 0.65, table). SINGLE SOURCE OF TRUTH — used by
# BOTH init_state AND the reset event so they cannot drift (the drift was the
# recurring standby bug). NOT symmetric: the arms mirror physically (the
# shoulder j2 opens the opposite way, the elbow bends the opposite way), so
# left/right values legitimately differ — symmetry is NOT a correctness test.
_STANDBY_POSE = {
    "openarm_left_joint1": 0.090,  "openarm_right_joint1": 0.090,
    "openarm_left_joint2": -0.640, "openarm_right_joint2": 0.430,
    "openarm_left_joint3": 0.130,  "openarm_right_joint3": -0.030,
    "openarm_left_joint4": 1.830,  "openarm_right_joint4": 1.830,
    "openarm_left_joint5": -0.480, "openarm_right_joint5": 0.330,
    "openarm_left_joint6": -0.120, "openarm_right_joint6": -0.210,
    "openarm_left_joint7": -0.220, "openarm_right_joint7": 0.080,
}


@configclass
class WP1PushS3aEnvCfg(WP1ContactTestbedEnvCfg):
    """Real push: OSC bimanual test-bed + a dynamic pushable cube on a table."""

    def __post_init__(self):
        super().__post_init__()

        # SILENT MID-EPISODE RESET (found 2026-10-05, eye-gate run e81261c8):
        # the inherited reach env times out at episode_length_s=24 s = 720 env
        # steps (dt 1/60, decimation 2) and IsaacLab AUTO-RESETS inside
        # env.step — robot, cube (now a seeded region) and goal all jump. The
        # orchestrator never checks `truncated`. With 90-step segments that is
        # round 8 of 12: all 3 eye-gate episodes showed a 9–15cm cube "push" at
        # R8 and one cube was launched 11.5m (respawned into the hand). Push
        # rounds are bounded by PUSH_ROUND_CAP × segment steps, so lift the
        # time-out well past that; push_collect asserts the margin at start.
        self.episode_length_s = 300.0

        # Raise the robot base onto its stand (PI layout). Base-relative coord
        # pipeline auto-adapts (recon-verified); only this literal changes.
        self.scene.robot.init_state.pos = (0.0, 0.0, _ROBOT_BASE_Z)

        # Q1 (2026-08-25, Pin-TODO trigger): gen-0 requires REAL gravity, not
        # the OSC-effort optimistic no-gravity of osc_testbed. Re-enable arm
        # gravity AND turn ON OSC gravity_compensation so the controller
        # actively holds against it. Overridden HERE (not osc_testbed) so the
        # old bisection diagnostics stay on their no-gravity config — isolation.
        self.scene.robot.spawn.rigid_props.disable_gravity = False

        # Work surface (Pin-10): the table asset the cube rests on and is pushed
        # across. AssetBaseCfg (static). collider verified present (step 1).
        self.scene.table = AssetBaseCfg(
            prim_path="{ENV_REGEX_NS}/Table",
            init_state=AssetBaseCfg.InitialStateCfg(pos=list(_TABLE_POS), rot=[1.0, 0.0, 0.0, 0.0]),
            spawn=UsdFileCfg(usd_path=_TABLE_USD),
        )

        # Pin-7a standby (PI-tuned 2026-08-25) — set on BOTH init_state and the
        # reset event from the SAME _STANDBY_POSE constant (no drift).
        self.scene.robot.init_state.joint_pos = {
            **_STANDBY_POSE,
            "openarm_left_finger_joint.*": 0.0, "openarm_right_finger_joint.*": 0.0,
        }

        # CRITICAL (2026-08-24): the inherited reach-base reset event
        # `reset_robot_joints` OVERRODE the standby at every reset — it forced
        # only j2/j4 + added ±0.2 rad jitter to ALL joints, so the pose never
        # took effect and was non-deterministic (the flop/jitter the PI saw).
        # Setting it to None was ALSO wrong: with no reset event, reset falls
        # back to the USD default (all-0), NOT init_state. Correct fix: REWRITE
        # the event to apply the FULL Pin-7a pose with ZERO jitter — the
        # deterministic standby (r-tracking needs a constant body, freeze clause).
        # Verified by scripts/diagnostics/check_config_effect.py.
        self.events.reset_robot_joints.params["target_joint_pos"] = dict(_STANDBY_POSE)
        self.events.reset_robot_joints.params["position_range"] = (0.0, 0.0)  # ZERO jitter
        self.events.reset_robot_joints.params["velocity_range"] = (0.0, 0.0)

        # Dynamic pushable cube — DexCube physics, now RESTING ON THE TABLE.
        # Spawn just above the table top so it settles deterministically onto
        # the surface (gravity ON). Explicit physics material (Pin-10): push
        # physics IS friction, so friction is a CONTROLLED KNOWN, not the
        # silently-inherited sim default.
        self.scene.object = RigidObjectCfg(
            prim_path="{ENV_REGEX_NS}/PushCube",
            init_state=RigidObjectCfg.InitialStateCfg(pos=[_CUBE_START_X, _CUBE_START_Y, _CUBE_SPAWN_Z], rot=[1.0, 0.0, 0.0, 0.0]),
            spawn=UsdFileCfg(
                usd_path=f"{ISAAC_NUCLEUS_DIR}/Props/Blocks/DexCube/dex_cube_instanceable.usd",
                scale=(0.8, 0.8, 0.8),
                rigid_props=RigidBodyPropertiesCfg(
                    solver_position_iteration_count=16,
                    solver_velocity_iteration_count=1,
                    max_angular_velocity=1000.0,
                    max_linear_velocity=1000.0,
                    max_depenetration_velocity=5.0,
                    disable_gravity=False,
                ),
                visual_material=sim_utils.PreviewSurfaceCfg(diffuse_color=(1.0, 1.0, 0.0)),
            ),
        )
        # Explicit contact friction (Pin-10): FileCfg.physics_material is a
        # configclass field, set by assignment (not an __init__ kwarg). Push
        # physics IS friction → controlled known, not sim-inherited default.
        self.scene.object.spawn.physics_material = sim_utils.RigidBodyMaterialCfg(
            static_friction=_FRICTION_STATIC,
            dynamic_friction=_FRICTION_DYNAMIC,
        )

        # CRITICAL (2026-10-02): the cube is a RigidObject, and IsaacLab's base
        # _reset_idx does NOT restore a rigid body's spawn pose — only an
        # EventTerm(mode="reset") that calls reset_root_state_uniform writes
        # init_state back to sim. The inherited reach chain has exactly ONE
        # reset event (reset_robot_joints, robot-only), because the reach base
        # had no dynamic object. Result (opus root-cause, provenance): the cube
        # was left wherever physics last shoved it and drifted cumulatively
        # across episodes (ep0 cube→goal 14cm → ep5 61cm) — which POLLUTED the
        # 10-ep rung-1 smoke (later episodes unwinnable, cube off-table). Add a
        # dedicated cube-reset event, ORTHOGONAL to reset_robot_joints (do NOT
        # use reset_scene_to_default — it would re-apply robot state and fight
        # the Pin-7a standby event). ZERO jitter (empty pose/velocity ranges →
        # every axis defaults to (0,0)) = deterministic restart at exactly
        # init_state (_CUBE_START_X, 0, _CUBE_SPAWN_Z), zero velocity — the
        # freeze clause (r-tracking needs a constant body). Pin-4b (10-05)
        # superseded the zero x/y jitter with a seeded REGION (below).
        self.events.reset_object = EventTerm(
            func=mdp.reset_root_state_uniform,
            mode="reset",
            params={
                # Pin-4b: x/y uniform over _CUBE_REGION_* (world offset from the
                # region-centre init_state; base has identity yaw, so world xy
                # offsets = base xy offsets). Seeded per episode → paired.
                "pose_range": {
                    "x": (_CUBE_REGION_X[0] - _CUBE_START_X, _CUBE_REGION_X[1] - _CUBE_START_X),
                    "y": (_CUBE_REGION_Y[0] - _CUBE_START_Y, _CUBE_REGION_Y[1] - _CUBE_START_Y),
                },
                "velocity_range": {},    # empty → zero velocity (cube at rest)
                "asset_cfg": SceneEntityCfg("object"),
            },
        )

        # Pin-1 HOLD gate: raise motion stiffness so the EE holds at the
        # contact target rather than reaching-then-drifting (#2's lesson).
        # 100 reached-but-drifted; bump the ceiling of the variable_kp range
        # and the nominal, tuned further in the hold smoke.
        for act in (self.actions.left_arm_action, self.actions.right_arm_action):
            act.controller_cfg.motion_stiffness_task = 300.0
            act.controller_cfg.motion_stiffness_limits_task = (100.0, 500.0)
            # Q1: OSC actively compensates gravity (arm gravity now ON) so the
            # standby/servo hold against real weight — the sim-to-real-honest
            # controller. Requires the gravity vector, which the OSC action
            # term feeds from get_gravity_compensation_forces.
            act.controller_cfg.gravity_compensation = True

        # ── cube-goal (Pin 4): re-purpose the left_ee_pose command as the
        # CUBE's goal region (where the cube must be pushed), NOT the EE's
        # target. Rationale: this reuses an existing seed-deterministic,
        # base-frame `.command` term (frame-gate compliant, already in the
        # replay-recording path) rather than adding a new CommandsCfg field
        # (which would need a dataclass change). Sampling distribution =
        # Pin 4 (on-table, planar, position-only). The push_toward primitive
        # reads this goal + the cube pose and computes the behind-cube
        # approach; the teacher only picks push-this-cube-to-this-goal.
        # Pin-4b: swap to the cube-relative term (same fields as the parent
        # UniformPoseCommandCfg; x/y = cube + offset, clipped to the reachable box).
        # pos_x/pos_y ranges are overwritten by the cube-relative sample; set to
        # the clip box so the parent draw is in-range even before the override.
        self.commands.left_ee_pose = CubeRelativePoseCommandCfg(
            **{f: getattr(self.commands.left_ee_pose, f)
               for f in self.commands.left_ee_pose.__dataclass_fields__ if f != "class_type"},
            offset_x=_GOAL_OFFSET_X, offset_y=_GOAL_OFFSET_Y,
            clip_x=_GOAL_CLIP_X, clip_y=_GOAL_CLIP_Y,
        )
        g = self.commands.left_ee_pose
        g.ranges.pos_x = _GOAL_CLIP_X
        g.ranges.pos_y = _GOAL_CLIP_Y
        g.ranges.pos_z = (_CUBE_REST_Z_B, _CUBE_REST_Z_B)   # BASE-frame contact height (was world → frame bug)
        g.ranges.roll = (0.0, 0.0)
        g.ranges.pitch = (0.0, 0.0)
        g.ranges.yaw = (0.0, 0.0)          # position-region goal; orient N/A

        # ── Visible goal + NO triads (2026-10-02, PI ruling a-1/a-2) ─────────
        # The teacher must SEE the goal, and the real world has no RGB coordinate
        # triads. So:
        #   • left_ee_pose GOAL visualizer → a flat GREEN DISC (the "green zone"
        #     the prompt names). This is the ONLY command marker that stays
        #     visible; it marks where the cube must end up.
        #   • left_ee_pose CURRENT visualizer → OFF (no triad trailing the EE).
        #   • right_ee_pose BOTH visualizers → OFF (the right arm is a passive
        #     holder in the push task; its goal/current triads were pure noise
        #     in the image and two of the three ambiguous triads the PI flagged).
        # debug_vis stays True on left so the green disc renders into the sensor
        # RGB (verified command markers DO render to the tiled camera).
        g.goal_pose_visualizer_cfg = _GREEN_GOAL_MARKER_CFG.replace(
            prim_path="/Visuals/Command/goal_zone"
        )
        # kill the left CURRENT-pose triad (make its markers invisible)
        for _m in self.commands.left_ee_pose.current_pose_visualizer_cfg.markers.values():
            _m.visible = False
        # kill BOTH right-arm triads entirely
        self.commands.right_ee_pose.debug_vis = False


# ── rung-1b: second-viewpoint (top-down) RGB camera — a SENSOR, not an oracle ──
# PI ruling 2026-10-06 (wp3a_pilot_plan.md ladder 1 → 1b → 2 → 3): rung-1 showed
# 0/50 contact from a single oblique RGB; a top-down RGB view gives x/y directly
# in the VLM's native modality. Depth is NOT added (its encoding is an untested
# hypothesis — rung-1c). EXTRINSICS = Pin-11 (recorded in wp3a_push_provenance):
# fixed world mount (not on the robot), straight down over the push region.
# The prompt gains ONE sentence naming the view; no coordinate semantics.
_TOPCAM_POS_B = (0.40, 0.06, 1.25)       # base frame (m): over the push region + left hand, ~0.8 m above the table top
_TOPCAM_ROT_WORLD = (0.70711, 0.0, 0.70711, 0.0)   # (w,x,y,z) "world" convention: +90° about y → optical axis +X → −Z (down); image top = robot forward (+x)
_TOPCAM_RES = 256                         # = main camera resolution
_TOPCAM_FOCAL_MM = 45.0


@configclass
class WP1PushS3aTopCamEnvCfg(WP1PushS3aEnvCfg):
    """WP1PushS3aEnvCfg + a fixed top-down RGB camera (rung-1b and above)."""

    def __post_init__(self):
        super().__post_init__()
        from isaaclab.sensors import CameraCfg

        self.scene.camera_top = CameraCfg(
            prim_path="{ENV_REGEX_NS}/TopCamera",
            update_period=0.0,
            height=_TOPCAM_RES,
            width=_TOPCAM_RES,
            data_types=["rgb"],
            spawn=sim_utils.PinholeCameraCfg(
                # FOV ≈ 2·atan(45/(2·45)) ≈ 53° → ≈0.8 m footprint at the table
                # (covers base x ≈ 0.0–0.8: hand standby, cube region, goal clip box)
                focal_length=_TOPCAM_FOCAL_MM, focus_distance=400.0,
                horizontal_aperture=45.0, clipping_range=(0.1, 1.0e5),
            ),
            offset=CameraCfg.OffsetCfg(
                pos=(_TOPCAM_POS_B[0], _TOPCAM_POS_B[1], _TOPCAM_POS_B[2] + _ROBOT_BASE_Z),
                rot=_TOPCAM_ROT_WORLD,
                convention="world",
            ),
        )
