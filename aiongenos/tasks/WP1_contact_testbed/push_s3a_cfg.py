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
from isaaclab.assets import RigidObjectCfg
from isaaclab.sim.spawners.from_files.from_files_cfg import UsdFileCfg
from isaaclab.sim.schemas.schemas_cfg import RigidBodyPropertiesCfg
from isaaclab.utils import configclass
from isaaclab.utils.assets import ISAAC_NUCLEUS_DIR

from aiongenos.tasks.WP1_contact_testbed.osc_testbed_cfg import WP1ContactTestbedEnvCfg


@configclass
class WP1PushS3aEnvCfg(WP1ContactTestbedEnvCfg):
    """Real push: OSC bimanual test-bed + a dynamic pushable cube."""

    def __post_init__(self):
        super().__post_init__()

        # Pin-7 (2026-08-17): BI init WORKING pose, not the asset all-0
        # hanging pose. From hanging, OSC needs super-limit torque → saturates
        # → no servo (the 8-round root cause). Working pose → servos (4.3cm).
        # BI-legal values (verified vs joint limits).
        self.scene.robot.init_state.joint_pos = {
            "openarm_left_joint1": 0.6, "openarm_left_joint2": 0.0,
            "openarm_left_joint3": 0.0, "openarm_left_joint4": 1.2,
            "openarm_left_joint5": 0.0, "openarm_left_joint6": 0.5,
            "openarm_left_joint7": 0.0,
            "openarm_right_joint1": 0.6, "openarm_right_joint4": 1.2,
            "openarm_right_joint6": 0.5,
            "openarm_left_finger_joint.*": 0.0, "openarm_right_finger_joint.*": 0.0,
        }

        # Dynamic pushable cube — reuse L3's validated DexCube physics
        # (gravity ON so it moves; the exact params pinned in provenance Pin 2).
        self.scene.object = RigidObjectCfg(
            prim_path="{ENV_REGEX_NS}/PushCube",
            init_state=RigidObjectCfg.InitialStateCfg(pos=[0.45, 0.0, 0.02], rot=[1.0, 0.0, 0.0, 0.0]),
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

        # Pin-1 HOLD gate: raise motion stiffness so the EE holds at the
        # contact target rather than reaching-then-drifting (#2's lesson).
        # 100 reached-but-drifted; bump the ceiling of the variable_kp range
        # and the nominal, tuned further in the hold smoke.
        for act in (self.actions.left_arm_action, self.actions.right_arm_action):
            act.controller_cfg.motion_stiffness_task = 300.0
            act.controller_cfg.motion_stiffness_limits_task = (100.0, 500.0)

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
        g.ranges.pos_x = (0.40, 0.60)
        g.ranges.pos_y = (-0.15, 0.15)
        g.ranges.pos_z = (0.02, 0.02)      # cube resting height (planar)
        g.ranges.roll = (0.0, 0.0)
        g.ranges.pitch = (0.0, 0.0)
        g.ranges.yaw = (0.0, 0.0)          # position-region goal; orient N/A
