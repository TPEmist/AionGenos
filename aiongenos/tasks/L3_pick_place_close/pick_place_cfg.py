# Copyright (c) 2026, AionGenos Cognitive Evolution Pipeline
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

from isaaclab.utils import configclass
from isaaclab.envs.mdp.actions.actions_cfg import DifferentialInverseKinematicsActionCfg
from isaaclab.controllers.differential_ik_cfg import DifferentialIKControllerCfg
import isaaclab.envs.mdp as mdp
from isaaclab.markers.config import CUBOID_MARKER_CFG
import isaaclab.sim as sim_utils
from isaaclab.assets import RigidObjectCfg, AssetBaseCfg
from isaaclab.sim.spawners.from_files.from_files_cfg import UsdFileCfg
from isaaclab.sim.schemas.schemas_cfg import RigidBodyPropertiesCfg
from isaaclab.utils.assets import ISAAC_NUCLEUS_DIR

from isaaclab_assets.robots.openarm import OPENARM_BI_HIGH_PD_CFG
from aiongenos.tasks.base.reach_env_base_cfg import AionGenosReachEnvBaseCfg

@configclass
class L3PickPlaceEnvCfg(AionGenosReachEnvBaseCfg):
    """Environment configuration for the L3 Pick & Place task (utilizing Pose + Gripper control)."""

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

        # Spawn Table (top surface ends up at z = 0.0)
        self.scene.table = AssetBaseCfg(
            prim_path="{ENV_REGEX_NS}/Table",
            init_state=AssetBaseCfg.InitialStateCfg(pos=[0.5, 0.0, -1.05], rot=[0.707, 0.0, 0.0, 0.707]),
            spawn=UsdFileCfg(usd_path=f"{ISAAC_NUCLEUS_DIR}/Props/Mounts/SeattleLabTable/table_instanceable.usd"),
        )

        # Spawn Yellow Cube (Object) on the table
        self.scene.object = RigidObjectCfg(
            prim_path="{ENV_REGEX_NS}/Object",
            init_state=RigidObjectCfg.InitialStateCfg(pos=[0.45, -0.1, 0.02], rot=[1.0, 0.0, 0.0, 0.0]),
            spawn=UsdFileCfg(
                usd_path=f"{ISAAC_NUCLEUS_DIR}/Props/Blocks/DexCube/dex_cube_instanceable.usd",
                scale=(0.8, 0.8, 0.8),
                rigid_props=RigidBodyPropertiesCfg(
                    solver_position_iteration_count=16,
                    solver_velocity_iteration_count=1,
                    max_angular_velocity=1000.0,
                    max_linear_velocity=1000.0,
                    max_depenetration_velocity=5.0,
                    disable_gravity=False,
                ),
                visual_material=sim_utils.PreviewSurfaceCfg(
                    diffuse_color=(1.0, 1.0, 0.0)  # Yellow
                ),
            ),
        )

        # Set goal visualizer to green cuboid (left) and green cuboid (right)
        self.commands.left_ee_pose.goal_pose_visualizer_cfg = CUBOID_MARKER_CFG.replace(
            prim_path="/Visuals/Command/left_goal_cube"
        )
        self.commands.left_ee_pose.goal_pose_visualizer_cfg.markers["cuboid"].visual_material = sim_utils.PreviewSurfaceCfg(
            diffuse_color=(0.0, 1.0, 0.0)  # Green
        )
        self.commands.left_ee_pose.goal_pose_visualizer_cfg.markers["cuboid"].size = (0.05, 0.05, 0.05)

        self.commands.right_ee_pose.goal_pose_visualizer_cfg = CUBOID_MARKER_CFG.replace(
            prim_path="/Visuals/Command/right_goal_cube"
        )
        self.commands.right_ee_pose.goal_pose_visualizer_cfg.markers["cuboid"].visual_material = sim_utils.PreviewSurfaceCfg(
            diffuse_color=(0.0, 1.0, 0.0)  # Green
        )
        self.commands.right_ee_pose.goal_pose_visualizer_cfg.markers["cuboid"].size = (0.05, 0.05, 0.05)

        # Make the current end-effector pose visualizers invisible to avoid VLM confusion
        if hasattr(self.commands.left_ee_pose, "current_pose_visualizer_cfg"):
            for marker in self.commands.left_ee_pose.current_pose_visualizer_cfg.markers.values():
                marker.visible = False
        if hasattr(self.commands.right_ee_pose, "current_pose_visualizer_cfg"):
            for marker in self.commands.right_ee_pose.current_pose_visualizer_cfg.markers.values():
                marker.visible = False

        # Configure action controllers: Left Arm + Gripper, Right Arm + Gripper
        # Alphabetical sorting of keys: left_arm_action, left_gripper_action, right_arm_action, right_gripper_action
        self.actions.left_arm_action = DifferentialInverseKinematicsActionCfg(
            asset_name="robot",
            joint_names=["openarm_left_joint.*"],
            body_name="openarm_left_hand",
            controller=DifferentialIKControllerCfg(
                command_type="pose",
                use_relative_mode=False,
                ik_method="dls",
            ),
            scale=1.0,
        )

        self.actions.left_gripper_action = mdp.BinaryJointPositionActionCfg(
            asset_name="robot",
            joint_names=["openarm_left_finger_joint.*"],
            open_command_expr={"openarm_left_finger_joint.*": 0.044},
            close_command_expr={"openarm_left_finger_joint.*": 0.0},
        )

        self.actions.right_arm_action = DifferentialInverseKinematicsActionCfg(
            asset_name="robot",
            joint_names=["openarm_right_joint.*"],
            body_name="openarm_right_hand",
            controller=DifferentialIKControllerCfg(
                command_type="pose",
                use_relative_mode=False,
                ik_method="dls",
            ),
            scale=1.0,
        )

        self.actions.right_gripper_action = mdp.BinaryJointPositionActionCfg(
            asset_name="robot",
            joint_names=["openarm_right_finger_joint.*"],
            open_command_expr={"openarm_right_finger_joint.*": 0.044},
            close_command_expr={"openarm_right_finger_joint.*": 0.0},
        )

        # Set number of environments for collector scaling
        self.scene.num_envs = 1
        self.scene.env_spacing = 2.5
