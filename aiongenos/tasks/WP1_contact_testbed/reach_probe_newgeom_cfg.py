# WP1-③a step 6 — reachability CONFIRM on the REBUILT geometry (2026-08-24).
#
# Old reachability sweeps are VOID: they ran on the mis-assembled scene (no
# table, arm base on the floor, cube at z=0.02). This cfg re-runs the SAME
# validated instrument — L2 DiffIK in orientation-FREE (command_type="position")
# mode — but on the NEW geometry: table Table_sor_1.usd, robot base at z=0.55,
# so the contact height z_b≈0.37 (cube-on-table) can be confirmed reachable.
#
# This is CONFIRMATION not exploration: z_b≈0.37 is already in the NEAR-verified
# servo band; the sweep checks the new scene actually delivers it. Reuses the
# pinned push_s3a geometry constants so probe and task cannot drift.

from isaaclab.utils import configclass
from isaaclab.assets import AssetBaseCfg
from isaaclab.envs.mdp.actions.actions_cfg import DifferentialInverseKinematicsActionCfg
from isaaclab.controllers.differential_ik_cfg import DifferentialIKControllerCfg
from isaaclab.sim.spawners.from_files.from_files_cfg import UsdFileCfg

from aiongenos.tasks.L2_dual_push.dual_push_cfg import L2DualPushEnvCfg
from aiongenos.tasks.WP1_contact_testbed.push_s3a_cfg import (
    _TABLE_USD, _TABLE_POS, _ROBOT_BASE_Z,
)


@configclass
class WP1ReachProbeNewGeomEnvCfg(L2DualPushEnvCfg):
    """L2 DiffIK instrument (orientation-free) on the REBUILT table+base scene."""

    def __post_init__(self):
        super().__post_init__()

        # New geometry (same pinned constants as push_s3a — no drift).
        self.scene.robot.init_state.pos = (0.0, 0.0, _ROBOT_BASE_Z)
        self.scene.table = AssetBaseCfg(
            prim_path="{ENV_REGEX_NS}/Table",
            init_state=AssetBaseCfg.InitialStateCfg(pos=list(_TABLE_POS), rot=[1.0, 0.0, 0.0, 0.0]),
            spawn=UsdFileCfg(usd_path=_TABLE_USD),
        )

        # Orientation-FREE IK on both arms (position-only 3-DoF task) — the
        # clean reachability tester (isolates position reach from wrist slew).
        for name in ("left_arm_action", "right_arm_action"):
            joint = "openarm_left_joint.*" if name == "left_arm_action" else "openarm_right_joint.*"
            body = "openarm_left_hand" if name == "left_arm_action" else "openarm_right_hand"
            setattr(self.actions, name, DifferentialInverseKinematicsActionCfg(
                asset_name="robot",
                joint_names=[joint],
                body_name=body,
                controller=DifferentialIKControllerCfg(
                    command_type="position", use_relative_mode=False, ik_method="dls"),
                scale=1.0,
            ))
