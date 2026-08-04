# Copyright (c) 2026, AionGenos Cognitive Evolution Pipeline
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause
#
# WP1 CONTACT TEST-BED (Paper 2, WP1-① closed-loop contact control).
#
# NEW task family. Replaces DifferentialIK with the Operational Space
# Controller (OSC), which ships a force/compliance channel that open-loop
# position servo lacks (the first "wall" from the P1 LIBERO gate). Per PI
# decision Q1 (2026-08-03): OSC only for new contact tasks; L0-L3 stay on
# DiffIK, byte-untouched. Controller choice pinned BEFORE first data in
# docs/p2_prereg/wp1_controller_provenance.md.
#
# ① SMOKE STAGE (this cfg): motion-only OSC (target_types=["pose_abs"],
# contact_wrench_control_axes all 0). Goal: show OSC is at least
# motion-equivalent to DiffIK on reaching BEFORE contact is enabled.
# Enabling wrench axes belongs to WP1-③ (press/twist) and re-pins
# provenance when it lands.

from isaaclab.utils import configclass
from isaaclab.envs.mdp.actions.actions_cfg import OperationalSpaceControllerActionCfg
from isaaclab.controllers.operational_space_cfg import OperationalSpaceControllerCfg

from isaaclab_assets.robots.openarm import OPENARM_BI_HIGH_PD_CFG
from aiongenos.tasks.base.reach_env_base_cfg import AionGenosReachEnvBaseCfg


@configclass
class WP1ContactTestbedEnvCfg(AionGenosReachEnvBaseCfg):
    """OSC bimanual test-bed. ① smoke = motion-only (pose_abs), no wrench.

    Inherits the same reach base as L2 so scene / camera / MDP defaults and
    the reward-tracking bodies match; the ONLY substantive change vs L2 is
    the action term: DifferentialInverseKinematicsActionCfg → OSC.
    """

    def __post_init__(self):
        super().__post_init__()

        # Same OpenArm bimanual robot as L2 (identical asset, so any OSC vs
        # DiffIK difference is attributable to the controller, not the robot).
        self.scene.robot = OPENARM_BI_HIGH_PD_CFG.replace(prim_path="{ENV_REGEX_NS}/Robot")

        # ── OSC effort-control prerequisite (2026-08-04 root-cause fix) ──
        # OSC is an operational-space EFFORT/torque controller: it computes
        # joint torques directly, so the arm actuators must NOT also run a
        # stiff position-PD loop (HIGH_PD) or the two fight and app-init
        # hangs. The official OSC reach env (isaaclab_tasks .../reach/config/
        # franka/osc_env_cfg.py) zeroes the arm actuators' stiffness/damping
        # and disables gravity. Mirror that for the openarm ARM actuator
        # (leave the gripper actuator as-is; OSC does not control it).
        self.scene.robot.actuators["openarm_arm"].stiffness = 0.0
        self.scene.robot.actuators["openarm_arm"].damping = 0.0
        self.scene.robot.spawn.rigid_props.disable_gravity = True

        # Command / reward body names — same hands as L2.
        self.commands.left_ee_pose.body_name = "openarm_left_hand"
        self.commands.right_ee_pose.body_name = "openarm_right_hand"
        self.rewards.left_end_effector_position_tracking.params["asset_cfg"].body_names = ["openarm_left_hand"]
        self.rewards.left_end_effector_position_tracking_fine_grained.params["asset_cfg"].body_names = ["openarm_left_hand"]
        self.rewards.left_end_effector_orientation_tracking.params["asset_cfg"].body_names = ["openarm_left_hand"]
        self.rewards.right_end_effector_position_tracking.params["asset_cfg"].body_names = ["openarm_right_hand"]
        self.rewards.right_end_effector_position_tracking_fine_grained.params["asset_cfg"].body_names = ["openarm_right_hand"]
        self.rewards.right_end_effector_orientation_tracking.params["asset_cfg"].body_names = ["openarm_right_hand"]

        # ── The one substantive change: OSC action terms (was DiffIK) ──
        # ① smoke: motion-only (target_types pose_abs, no contact wrench).
        # Controller params mirror the OFFICIAL OSC reach env verbatim
        # (variable_kp + inertial decoupling + nullspace position control) —
        # the config IsaacLab ships as a working OSC-on-reach example, so we
        # do not invent parameters. Contact-wrench axes stay OFF here;
        # enabling them is WP1-③ and re-pins provenance.
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

        self.actions.left_arm_action = OperationalSpaceControllerActionCfg(
            asset_name="robot",
            joint_names=["openarm_left_joint.*"],
            body_name="openarm_left_hand",
            controller_cfg=_osc_cfg(),
            nullspace_joint_pos_target="center",
            position_scale=1.0,
            orientation_scale=1.0,
            stiffness_scale=100.0,
        )
        self.actions.right_arm_action = OperationalSpaceControllerActionCfg(
            asset_name="robot",
            joint_names=["openarm_right_joint.*"],
            body_name="openarm_right_hand",
            controller_cfg=_osc_cfg(),
            nullspace_joint_pos_target="center",
            position_scale=1.0,
            orientation_scale=1.0,
            stiffness_scale=100.0,
        )

        self.scene.num_envs = 1
        self.scene.env_spacing = 2.5
