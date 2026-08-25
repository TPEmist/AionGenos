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
from isaaclab.assets import RigidObjectCfg, AssetBaseCfg
from isaaclab.sim.spawners.from_files.from_files_cfg import UsdFileCfg
from isaaclab.sim.schemas.schemas_cfg import RigidBodyPropertiesCfg
from isaaclab.utils import configclass
from isaaclab.utils.assets import ISAAC_NUCLEUS_DIR

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
_CUBE_SPAWN_Z = _TABLE_TOP_Z + 0.02                 # spawn slightly above → settles onto top (WORLD)
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
            init_state=RigidObjectCfg.InitialStateCfg(pos=[_CUBE_START_X, 0.0, _CUBE_SPAWN_Z], rot=[1.0, 0.0, 0.0, 0.0]),
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
        g = self.commands.left_ee_pose
        g.ranges.pos_x = _PIN4_X   # Pin-4a: −60mm in → (0.34, 0.54)
        g.ranges.pos_y = _PIN4_Y
        g.ranges.pos_z = (_CUBE_REST_Z_B, _CUBE_REST_Z_B)   # BASE-frame contact height (was world → frame bug)
        g.ranges.roll = (0.0, 0.0)
        g.ranges.pitch = (0.0, 0.0)
        g.ranges.yaw = (0.0, 0.0)          # position-region goal; orient N/A
