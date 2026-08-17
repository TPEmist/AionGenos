# WP1-③a diagnosis Step 0a (2026-08-17): MIRROR of bileft — BI robot +
# RIGHT arm on ONE OSC term + LEFT arm on JointPosition.
#
# Interleaved-index hypothesis predicts the RIGHT arm (ids [1,3,5,7,9,11,13],
# equally interleaved) is ALSO NO-TRACK. If the right arm instead TRACKS,
# the interleaving hypothesis dies immediately — the culprit is elsewhere.

from isaaclab.controllers.operational_space_cfg import OperationalSpaceControllerCfg
from isaaclab.envs.mdp.actions.actions_cfg import OperationalSpaceControllerActionCfg
import isaaclab.envs.mdp as mdp
from isaaclab.utils import configclass

from isaaclab_tasks.manager_based.manipulation.reach.config.franka import joint_pos_env_cfg
from isaaclab_assets.robots.openarm import OPENARM_BI_CFG


@configclass
class OscBiRightOnlyEnvCfg(joint_pos_env_cfg.FrankaReachEnvCfg):
    """BI robot, RIGHT arm = one OSC term, LEFT arm = JointPosition hold."""

    def __post_init__(self):
        super().__post_init__()

        self.scene.robot = OPENARM_BI_CFG.replace(prim_path="{ENV_REGEX_NS}/Robot")
        self.scene.robot.actuators["openarm_arm"].stiffness = 0.0
        self.scene.robot.actuators["openarm_arm"].damping = 0.0
        self.scene.robot.spawn.rigid_props.disable_gravity = True

        # Reward/command on the RIGHT hand (the tracked EE for this mirror).
        self.rewards.end_effector_position_tracking.params["asset_cfg"].body_names = ["openarm_right_hand"]
        self.rewards.end_effector_position_tracking_fine_grained.params["asset_cfg"].body_names = ["openarm_right_hand"]
        self.rewards.end_effector_orientation_tracking.params["asset_cfg"].body_names = ["openarm_right_hand"]
        self.commands.ee_pose.body_name = "openarm_right_hand"

        self.actions.arm_action = None

        # RIGHT arm: the ONLY OSC term.
        self.actions.right_arm_action = OperationalSpaceControllerActionCfg(
            asset_name="robot",
            joint_names=["openarm_right_joint.*"],
            body_name="openarm_right_hand",
            controller_cfg=OperationalSpaceControllerCfg(
                target_types=["pose_abs"],
                impedance_mode="variable_kp",
                inertial_dynamics_decoupling=True,
                partial_inertial_dynamics_decoupling=False,
                gravity_compensation=False,
                motion_stiffness_task=100.0,
                motion_damping_ratio_task=1.0,
                motion_stiffness_limits_task=(50.0, 200.0),
                nullspace_control="position",
            ),
            nullspace_joint_pos_target="center",
            position_scale=1.0,
            orientation_scale=1.0,
            stiffness_scale=100.0,
        )
        # LEFT arm: JointPosition hold (not a 2nd OSC term).
        self.actions.left_arm_action = mdp.JointPositionActionCfg(
            asset_name="robot",
            joint_names=["openarm_left_joint.*"],
            scale=0.5,
            use_default_offset=True,
        )

        self.observations.policy.joint_pos = None
        self.observations.policy.joint_vel = None
        self.scene.num_envs = 1
        self.scene.env_spacing = 2.5
