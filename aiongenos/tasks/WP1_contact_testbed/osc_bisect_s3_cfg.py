# WP1-① OSC bisection — s3: s2 + the AionGenos custom reset event.
# s0/s1/s2 (single→dual arm→camera, all on OSC) PASSED. s3 adds the ONE
# item most-suspected to be the root cause of the original test-bed's
# reset stall: AionGenosReachEnvBaseCfg's custom `reset_robot_joints`
# EventTerm (reset_joints_to_target_with_offset, reach_env_base_cfg.py:90),
# which the official reach base does NOT have. If s3 hangs at reset → this
# reset event × OSC is the culprit; run the 2×2 confirm (same event + DiffIK)
# to pin whether it's the event itself or its interaction with OSC.

from isaaclab.managers import EventTermCfg as EventTerm
from isaaclab.utils import configclass

from aiongenos.mdp.reset import reset_joints_to_target_with_offset
from aiongenos.tasks.WP1_contact_testbed.osc_bisect_s2_cfg import OscBisectS2EnvCfg


@configclass
class OscBisectS3EnvCfg(OscBisectS2EnvCfg):
    """s2 (dual-arm OSC + camera) + AionGenos custom reset event."""

    def __post_init__(self):
        super().__post_init__()

        # The custom reset the AionGenos base uses (verbatim from
        # reach_env_base_cfg.py:90) — sets target joint pose then jitters
        # ±0.2 rad. This is the prime suspect for the reset-time stall.
        self.events.reset_robot_joints = EventTerm(
            func=reset_joints_to_target_with_offset,
            mode="reset",
            params={
                "target_joint_pos": {
                    "openarm_left_joint2": 0.5,
                    "openarm_left_joint4": 0.8,
                    "openarm_right_joint2": 0.5,
                    "openarm_right_joint4": 0.8,
                },
                "position_range": (-0.2, 0.2),
                "velocity_range": (0.0, 0.0),
            },
        )
