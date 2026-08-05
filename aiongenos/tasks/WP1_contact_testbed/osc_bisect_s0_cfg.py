# WP1-① OSC bisection — s0: official OSC reach env + openarm SINGLE arm.
#
# A1 diagnosis (PI spec 2026-08-05): build UP from a known-good config, not
# down from our broken base. s0 = the OFFICIAL FrankaReachEnvCfg (OSC), with
# ONLY the robot swapped Franka→openarm single-arm. If s0 hangs → the fault
# is asset×OSC (openarm URDF incompatible with OSC). If s0 runs → assets are
# fine, escalate: s1 (+2nd arm), s2 (+camera), s3 (+reach-base extras).
#
# Deliberately inherits the OFFICIAL reach base (NO camera, NO AionGenos
# base), so every s-step's baseline before the added variable is green.

from isaaclab.controllers.operational_space_cfg import OperationalSpaceControllerCfg
from isaaclab.envs.mdp.actions.actions_cfg import OperationalSpaceControllerActionCfg
from isaaclab.utils import configclass

from isaaclab_tasks.manager_based.manipulation.reach.config.franka import joint_pos_env_cfg

from isaaclab_assets.robots.openarm import OPENARM_UNI_CFG  # single arm


# EE body name — resolved at runtime by the smoke (it prints all body names
# first); default guess documented, overridden if the print says otherwise.
_OPENARM_UNI_EE_BODY = "openarm_hand"
_OPENARM_UNI_JOINTS = ["openarm_joint[1-7]"]


@configclass
class OscBisectS0EnvCfg(joint_pos_env_cfg.FrankaReachEnvCfg):
    """Official OSC reach env, robot swapped to openarm single-arm."""

    def __post_init__(self):
        super().__post_init__()  # official Franka reach + OSC setup

        # Swap robot Franka → openarm single-arm. Mirror the official OSC
        # effort-control prerequisite: zero the arm actuator gains + disable
        # gravity (osc_env_cfg.py:27-31).
        self.scene.robot = OPENARM_UNI_CFG.replace(prim_path="{ENV_REGEX_NS}/Robot")
        self.scene.robot.actuators["openarm_arm"].stiffness = 0.0
        self.scene.robot.actuators["openarm_arm"].damping = 0.0
        self.scene.robot.spawn.rigid_props.disable_gravity = True

        # Re-point every Franka-specific body/joint name to openarm.
        self.rewards.end_effector_position_tracking.params["asset_cfg"].body_names = [_OPENARM_UNI_EE_BODY]
        self.rewards.end_effector_position_tracking_fine_grained.params["asset_cfg"].body_names = [_OPENARM_UNI_EE_BODY]
        self.rewards.end_effector_orientation_tracking.params["asset_cfg"].body_names = [_OPENARM_UNI_EE_BODY]
        self.commands.ee_pose.body_name = _OPENARM_UNI_EE_BODY

        # Rebuild the OSC action term for openarm joints/body (same official
        # OSC controller params as osc_env_cfg.py, just retargeted).
        self.actions.arm_action = OperationalSpaceControllerActionCfg(
            asset_name="robot",
            joint_names=_OPENARM_UNI_JOINTS,
            body_name=_OPENARM_UNI_EE_BODY,
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
        self.observations.policy.joint_pos = None
        self.observations.policy.joint_vel = None

        self.scene.num_envs = 1
        self.scene.env_spacing = 2.5
