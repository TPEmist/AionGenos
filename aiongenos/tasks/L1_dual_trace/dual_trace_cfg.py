# Copyright (c) 2026, AionGenos Cognitive Evolution Pipeline
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

from isaaclab.utils import configclass
from isaaclab.envs.mdp.actions.actions_cfg import DifferentialInverseKinematicsActionCfg
from isaaclab.controllers.differential_ik_cfg import DifferentialIKControllerCfg
from isaaclab.markers.config import CUBOID_MARKER_CFG
import isaaclab.sim as sim_utils

from isaaclab_assets.robots.openarm import OPENARM_BI_HIGH_PD_CFG
from aiongenos.tasks.base.reach_env_base_cfg import AionGenosReachEnvBaseCfg

@configclass
class L1DualTraceEnvCfg(AionGenosReachEnvBaseCfg):
    """Environment configuration for the L1 Dual Trace task."""

    def __post_init__(self):
        # Initialize parent which sets up the scene, camera and MDP defaults
        super().__post_init__()

        # Switch robot to OpenArm bimanual configuration
        self.scene.robot = OPENARM_BI_HIGH_PD_CFG.replace(prim_path="{ENV_REGEX_NS}/Robot")

        # Override commands targets and body tracking names
        self.commands.left_ee_pose.body_name = "openarm_left_hand"
        self.commands.right_ee_pose.body_name = "openarm_right_hand"

        # Set tracking body names for reward calculations
        self.rewards.left_end_effector_position_tracking.params["asset_cfg"].body_names = ["openarm_left_hand"]
        self.rewards.left_end_effector_position_tracking_fine_grained.params["asset_cfg"].body_names = ["openarm_left_hand"]
        self.rewards.left_end_effector_orientation_tracking.params["asset_cfg"].body_names = ["openarm_left_hand"]

        self.rewards.right_end_effector_position_tracking.params["asset_cfg"].body_names = ["openarm_right_hand"]
        self.rewards.right_end_effector_position_tracking_fine_grained.params["asset_cfg"].body_names = ["openarm_right_hand"]
        self.rewards.right_end_effector_orientation_tracking.params["asset_cfg"].body_names = ["openarm_right_hand"]

        # Set goal visualizer to red cuboid (left) and blue cuboid (right)
        self.commands.left_ee_pose.goal_pose_visualizer_cfg = CUBOID_MARKER_CFG.replace(
            prim_path="/Visuals/Command/left_goal_cube"
        )
        self.commands.left_ee_pose.goal_pose_visualizer_cfg.markers["cuboid"].visual_material = sim_utils.PreviewSurfaceCfg(
            diffuse_color=(1.0, 0.0, 0.0)  # Red
        )
        self.commands.left_ee_pose.goal_pose_visualizer_cfg.markers["cuboid"].size = (0.05, 0.05, 0.05)

        self.commands.right_ee_pose.goal_pose_visualizer_cfg = CUBOID_MARKER_CFG.replace(
            prim_path="/Visuals/Command/right_goal_cube"
        )
        self.commands.right_ee_pose.goal_pose_visualizer_cfg.markers["cuboid"].visual_material = sim_utils.PreviewSurfaceCfg(
            diffuse_color=(0.0, 0.0, 1.0)  # Blue
        )
        self.commands.right_ee_pose.goal_pose_visualizer_cfg.markers["cuboid"].size = (0.05, 0.05, 0.05)

        # Make the current end-effector pose visualizers invisible to avoid VLM confusion
        if hasattr(self.commands.left_ee_pose, "current_pose_visualizer_cfg"):
            for marker in self.commands.left_ee_pose.current_pose_visualizer_cfg.markers.values():
                marker.visible = False
        if hasattr(self.commands.right_ee_pose, "current_pose_visualizer_cfg"):
            for marker in self.commands.right_ee_pose.current_pose_visualizer_cfg.markers.values():
                marker.visible = False

        # Configure action controllers to use Differential IK (Position-only)
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

        # Set number of environments for collector scaling
        self.scene.num_envs = 1
        self.scene.env_spacing = 2.5
