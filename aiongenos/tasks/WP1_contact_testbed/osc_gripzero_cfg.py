# WP1-① single-variable test on the ORIGINAL test-bed (2026-08-06).
#
# Direct test per PI: take the REAL WP1ContactTestbedEnvCfg (which stalls at
# reset) and change exactly ONE thing — zero the GRIPPER actuator gains
# (HIGH_PD leaves stiffness=2e3/damping=1e2 on openarm_gripper; the arm
# gains were already zeroed in the original). If this un-stalls → gripper
# gains are the cause, verified on the real config (not a rebuilt proxy).
# If it still stalls → gripper is exonerated, bisect the remaining
# AionGenosReachEnvBaseCfg differences on the real config.
#
# This inherits the ORIGINAL test-bed verbatim, so no base-class-mismatch
# confound: the only delta vs the stalling config is the gripper gains.

from isaaclab.utils import configclass

from aiongenos.tasks.WP1_contact_testbed.osc_testbed_cfg import WP1ContactTestbedEnvCfg


@configclass
class WP1GripZeroEnvCfg(WP1ContactTestbedEnvCfg):
    """Original OSC test-bed with the gripper actuator gains zeroed."""

    def __post_init__(self):
        super().__post_init__()
        # The ONE variable under test. Arm gains already zeroed by the parent;
        # this adds the gripper.
        self.scene.robot.actuators["openarm_gripper"].stiffness = 0.0
        self.scene.robot.actuators["openarm_gripper"].damping = 0.0
