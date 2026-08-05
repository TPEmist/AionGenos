# WP1-① OSC bisection — s1: s0 + SECOND arm (dual articulation, each an OSC
# action term). Highest-suspicion step: the official OSC example never
# covers two OSC action terms on a bimanual robot. s0 (single arm) PASSED,
# so assets×OSC is fine; s1 isolates the bimanual×OSC dimension.
#
# Still on the OFFICIAL reach base (NO camera) — camera is s2.

from isaaclab.controllers.operational_space_cfg import OperationalSpaceControllerCfg
from isaaclab.envs.mdp.actions.actions_cfg import OperationalSpaceControllerActionCfg
from isaaclab.utils import configclass

from isaaclab_tasks.manager_based.manipulation.reach.config.franka import joint_pos_env_cfg

from isaaclab_assets.robots.openarm import OPENARM_BI_CFG  # two arms


def _osc_cfg() -> OperationalSpaceControllerCfg:
    return OperationalSpaceControllerCfg(
        target_types=["pose_abs"],
        impedance_mode="variable_kp",
        inertial_dynamics_decoupling=True,
        partial_inertial_dynamics_decoupling=False,
        gravity_compensation=False,
        motion_stiffness_task=100.0,
        motion_damping_ratio_task=1.0,
        motion_stiffness_limits_task=(50.0, 200.0),
        nullspace_control="position",
    )


def _osc_action(joints: str, body: str) -> OperationalSpaceControllerActionCfg:
    return OperationalSpaceControllerActionCfg(
        asset_name="robot",
        joint_names=[joints],
        body_name=body,
        controller_cfg=_osc_cfg(),
        nullspace_joint_pos_target="center",
        position_scale=1.0,
        orientation_scale=1.0,
        stiffness_scale=100.0,
    )


@configclass
class OscBisectS1EnvCfg(joint_pos_env_cfg.FrankaReachEnvCfg):
    """Official OSC reach base, dual-arm openarm, two OSC action terms."""

    def __post_init__(self):
        super().__post_init__()

        # Dual-arm openarm; zero the arm actuator gains + disable gravity
        # (OSC effort-control prerequisite, per official osc_env_cfg).
        self.scene.robot = OPENARM_BI_CFG.replace(prim_path="{ENV_REGEX_NS}/Robot")
        self.scene.robot.actuators["openarm_arm"].stiffness = 0.0
        self.scene.robot.actuators["openarm_arm"].damping = 0.0
        self.scene.robot.spawn.rigid_props.disable_gravity = True

        # Reward/command bodies → left hand (single tracked EE is enough for
        # the bisection; s1 tests whether TWO OSC terms coexist, not the task).
        self.rewards.end_effector_position_tracking.params["asset_cfg"].body_names = ["openarm_left_hand"]
        self.rewards.end_effector_position_tracking_fine_grained.params["asset_cfg"].body_names = ["openarm_left_hand"]
        self.rewards.end_effector_orientation_tracking.params["asset_cfg"].body_names = ["openarm_left_hand"]
        self.commands.ee_pose.body_name = "openarm_left_hand"

        # Drop the inherited single Franka arm_action (uses panda_joint.* →
        # regex fails on openarm). s0 didn't hit this because it OVERWROTE
        # arm_action with one term; s1 adds left/right terms, so the stale
        # inherited arm_action must be explicitly removed.
        self.actions.arm_action = None

        # TWO OSC action terms — the variable under test.
        self.actions.left_arm_action = _osc_action("openarm_left_joint.*", "openarm_left_hand")
        self.actions.right_arm_action = _osc_action("openarm_right_joint.*", "openarm_right_hand")

        self.observations.policy.joint_pos = None
        self.observations.policy.joint_vel = None
        self.scene.num_envs = 1
        self.scene.env_spacing = 2.5
