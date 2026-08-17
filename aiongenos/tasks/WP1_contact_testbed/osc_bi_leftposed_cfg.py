# WP1-③a diagnosis Step 1b-alt (2026-08-17): BiLeftOnly but with the LEFT
# arm's init joint pose set to the UNI robot's WORKING pose (not all-zeros).
#
# Hypothesis (from Step 1a): the culprit is not OSC/index (Step 0b proved
# the mass-matrix sub-block is correct) but the BI robot's init pose. BI
# inits ALL joints to 0 (arms hanging down, EE at z~0.16, near a poor/
# singular config for OSC's Jacobian), whereas UNI inits joint1=1.57,
# joint3=-1.57, joint4=1.57 (an extended working pose) — and UNI servos to
# 2cm. Test: give the BI left arm the UNI working pose; if it now servos,
# the culprit is the init pose, not the bimanual OSC path.

from isaaclab.utils import configclass
from aiongenos.tasks.WP1_contact_testbed.osc_bi_leftonly_cfg import OscBiLeftOnlyEnvCfg


@configclass
class OscBiLeftPosedEnvCfg(OscBiLeftOnlyEnvCfg):
    """BiLeftOnly + left arm init at the UNI working pose."""

    def __post_init__(self):
        super().__post_init__()
        # BI-LEGAL raised working pose, per VERIFIED limits (not guessed):
        #   j1[-3.49,1.40] j2[-3.32,0.17] j3[-1.57,1.57] j4[0,2.44]
        #   j5[-1.57,1.57] j6[-0.79,0.79] j7[-1.57,1.57]
        # A non-hanging "elbow-bent, forearm forward" config, all in-limits
        # (j2 capped at 0.17 — the one I overran before). Applied to BOTH
        # arms (left mirrored by joint sign where the URDF mirrors; here the
        # right arm is held by JointPosition so its pose is for balance/vis).
        self.scene.robot.init_state.joint_pos = {
            "openarm_left_joint1": 0.6,
            "openarm_left_joint2": 0.0,     # <= 0.17 limit; keep 0 (safe)
            "openarm_left_joint3": 0.0,
            "openarm_left_joint4": 1.2,     # elbow bend (limit 2.44)
            "openarm_left_joint5": 0.0,
            "openarm_left_joint6": 0.5,     # wrist (limit 0.79)
            "openarm_left_joint7": 0.0,
            "openarm_right_joint1": 0.6,
            "openarm_right_joint4": 1.2,
            "openarm_right_joint6": 0.5,
            "openarm_left_finger_joint.*": 0.0,
            "openarm_right_finger_joint.*": 0.0,
        }
