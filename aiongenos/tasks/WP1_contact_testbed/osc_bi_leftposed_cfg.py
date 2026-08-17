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
        # Override init joint pose: left arm to UNI's working pose, right arm
        # stays 0 (it's held by JointPosition anyway).
        # BI joint limits DIFFER from UNI (e.g. left_joint1 in [-3.491,1.396],
        # so UNI's 1.57 is illegal). Use a BI-legal "arm raised, elbow bent"
        # pose (values inside BI limits) — the point is a non-hanging working
        # config, not UNI's exact angles.
        self.scene.robot.init_state.joint_pos = {
            "openarm_left_joint1": 1.30,
            "openarm_left_joint2": 0.5,
            "openarm_left_joint3": -1.0,
            "openarm_left_joint4": 1.0,
            "openarm_left_joint5": 0.0,
            "openarm_left_joint6": 0.5,
            "openarm_left_joint7": 0.0,
            "openarm_right_joint.*": 0.0,
            "openarm_left_finger_joint.*": 0.0,
            "openarm_right_finger_joint.*": 0.0,
        }
