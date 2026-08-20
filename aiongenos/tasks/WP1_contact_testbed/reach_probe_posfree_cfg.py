# WP1-③a reachability CONFOUND-KILLER (2026-08-20): L2 env with the DiffIK
# action switched to command_type="position" (orientation-FREE IK).
#
# The reachability sweep (human-eye gate verdict 2026-08-20) showed the wall
# is LATERAL, not vertical, and is likely COMPOUNDED by the held-orientation
# constraint pinning the wrist in a poor IK config ("往右沒問題" — a better
# config would reach). To test that, we need orientation-FREE reachability:
# can the EE reach the point AT ALL, with any wrist orientation?
#
# command_type="position" makes DiffIK solve position only (3-DoF task), so
# the wrist is free to adopt whatever orientation reaches. This isolates pure
# positional reachability from orientation cost — the clean confound-killer.
#
# Pure-diagnostic env (PI: "先純診斷,不預設歸屬"). No task-geometry decision
# baked in; both arms stay symmetric so the sweep can map the true (x,y,z)
# envelope for EITHER arm and let assignment emerge from data.

from isaaclab.utils import configclass
from isaaclab.envs.mdp.actions.actions_cfg import DifferentialInverseKinematicsActionCfg
from isaaclab.controllers.differential_ik_cfg import DifferentialIKControllerCfg

from aiongenos.tasks.L2_dual_push.dual_push_cfg import L2DualPushEnvCfg


@configclass
class WP1ReachProbePosFreeEnvCfg(L2DualPushEnvCfg):
    """L2 instrument, DiffIK in POSITION mode (orientation-free reachability)."""

    def __post_init__(self):
        super().__post_init__()

        # Override BOTH arm actions to position-only IK. Everything else
        # (robot, scene, command terms, goal visualizers) inherits L2 verbatim
        # so this is the SAME validated instrument, only the IK task-dim change.
        self.actions.left_arm_action = DifferentialInverseKinematicsActionCfg(
            asset_name="robot",
            joint_names=["openarm_left_joint.*"],
            body_name="openarm_left_hand",
            controller=DifferentialIKControllerCfg(
                command_type="position",
                use_relative_mode=False,
                ik_method="dls",
            ),
            scale=1.0,
        )
        self.actions.right_arm_action = DifferentialInverseKinematicsActionCfg(
            asset_name="robot",
            joint_names=["openarm_right_joint.*"],
            body_name="openarm_right_hand",
            controller=DifferentialIKControllerCfg(
                command_type="position",
                use_relative_mode=False,
                ik_method="dls",
            ),
            scale=1.0,
        )
