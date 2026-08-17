# WP1-③a diagnosis (2026-08-17, per recon agent's decisive isolation):
# BI robot + LEFT arm on ONE OSC term + RIGHT arm on JointPosition.
#
# This cuts the two confounded variables apart that all prior comparisons
# mixed:
#   - s0 used OPENARM_UNI_CFG (a DIFFERENT robot), s1/push used BI — so
#     "single-arm servos / bimanual doesn't" confounded UNI-vs-BI with
#     arm-count.
#   - s1/push had TWO OSC terms — confounding "two OSC terms interfere"
#     with the robot change.
# Here: same BI robot as the real task, ONE OSC term (left), right arm held
# by JointPosition (not a second OSC term). If the LEFT EE servos → the fault
# was the two-OSC-terms interaction; if it still fails → the fault is the BI
# articulation itself (indexing / gain), independent of arm count.

from isaaclab.controllers.operational_space_cfg import OperationalSpaceControllerCfg
from isaaclab.envs.mdp.actions.actions_cfg import OperationalSpaceControllerActionCfg
import isaaclab.envs.mdp as mdp
from isaaclab.utils import configclass

from isaaclab_tasks.manager_based.manipulation.reach.config.franka import joint_pos_env_cfg
from isaaclab_assets.robots.openarm import OPENARM_BI_CFG


@configclass
class OscBiLeftOnlyEnvCfg(joint_pos_env_cfg.FrankaReachEnvCfg):
    """BI robot, LEFT arm = one OSC term, RIGHT arm = JointPosition hold."""

    def __post_init__(self):
        super().__post_init__()

        self.scene.robot = OPENARM_BI_CFG.replace(prim_path="{ENV_REGEX_NS}/Robot")
        # Zero the (single, both-arm) arm actuator group so OSC effort is not
        # fought by implicit PD. NOTE: openarm_arm covers BOTH arms' 14 joints
        # — zeroing it once affects both; the right arm's JointPosition term
        # then has no PD either, so hold it via effort=0 default (it will sag
        # under gravity, but robot gravity is off in this diagnostic).
        self.scene.robot.actuators["openarm_arm"].stiffness = 0.0
        self.scene.robot.actuators["openarm_arm"].damping = 0.0
        self.scene.robot.spawn.rigid_props.disable_gravity = True

        # Reward/command on the LEFT hand (single tracked EE for the probe).
        self.rewards.end_effector_position_tracking.params["asset_cfg"].body_names = ["openarm_left_hand"]
        self.rewards.end_effector_position_tracking_fine_grained.params["asset_cfg"].body_names = ["openarm_left_hand"]
        self.rewards.end_effector_orientation_tracking.params["asset_cfg"].body_names = ["openarm_left_hand"]
        self.commands.ee_pose.body_name = "openarm_left_hand"

        # Drop the inherited franka arm_action.
        self.actions.arm_action = None

        # LEFT arm: ONE OSC term (the only OSC term in this env).
        self.actions.left_arm_action = OperationalSpaceControllerActionCfg(
            asset_name="robot",
            joint_names=["openarm_left_joint.*"],
            body_name="openarm_left_hand",
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

        # RIGHT arm: JointPosition (NOT a second OSC term) — the whole point
        # is to remove the second OSC term from the comparison.
        self.actions.right_arm_action = mdp.JointPositionActionCfg(
            asset_name="robot",
            joint_names=["openarm_right_joint.*"],
            scale=0.5,
            use_default_offset=True,
        )

        self.observations.policy.joint_pos = None
        self.observations.policy.joint_vel = None
        self.scene.num_envs = 1
        self.scene.env_spacing = 2.5
