# Copyright (c) 2026, AionGenos Cognitive Evolution Pipeline
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""L0a single-arm reach configurations.

Two variants:
- ``L0aSingleReachLeftEnvCfg``: only the left arm is actuated; the right
  arm's joints stay at their default home pose. The visible target marker
  uses the same red cuboid as L0's left target.
- ``L0aSingleReachRightEnvCfg``: mirror image.

The opposite arm's command term is kept in the scene (Isaac Lab's reward
manager and pose visualizer assume both terms exist) but its goal
visualizer is hidden, and its action term is replaced by an
``mdp.OffsetActionCfg``-style hold-in-place hack via a
``DifferentialInverseKinematicsActionCfg`` whose target is bound to the
current home EE pose. The action space exposed to gymnasium therefore
keeps 6 dims (3 per arm) for plumbing compatibility, but only 3 dims are
*meaningful*; ``IsaacLabEnvInterface`` zero-fills the other 3 so the
inactive arm holds steady.
"""

from isaaclab.controllers.differential_ik_cfg import DifferentialIKControllerCfg
from isaaclab.envs.mdp.actions.actions_cfg import DifferentialInverseKinematicsActionCfg
from isaaclab.markers.config import CUBOID_MARKER_CFG
from isaaclab.utils import configclass
import isaaclab.sim as sim_utils

from isaaclab_assets.robots.openarm import OPENARM_BI_HIGH_PD_CFG
from aiongenos.tasks.base.reach_env_base_cfg import AionGenosReachEnvBaseCfg


@configclass
class _L0aSingleReachBaseCfg(AionGenosReachEnvBaseCfg):
    """Internals shared by L0a-Left and L0a-Right.

    Concrete subclasses set ``ACTIVE_ARM`` to ``"left"`` or ``"right"``.
    """

    ACTIVE_ARM: str = "left"

    def __post_init__(self):
        super().__post_init__()

        # Switch robot to OpenArm bimanual configuration (same as L0).
        self.scene.robot = OPENARM_BI_HIGH_PD_CFG.replace(prim_path="{ENV_REGEX_NS}/Robot")

        self.commands.left_ee_pose.body_name = "openarm_left_hand"
        self.commands.right_ee_pose.body_name = "openarm_right_hand"

        for side in ("left", "right"):
            self.rewards.__getattribute__(f"{side}_end_effector_position_tracking").params[
                "asset_cfg"
            ].body_names = [f"openarm_{side}_hand"]
            self.rewards.__getattribute__(
                f"{side}_end_effector_position_tracking_fine_grained"
            ).params["asset_cfg"].body_names = [f"openarm_{side}_hand"]
            self.rewards.__getattribute__(
                f"{side}_end_effector_orientation_tracking"
            ).params["asset_cfg"].body_names = [f"openarm_{side}_hand"]

        # Goal visualizers — red for whichever arm is the active reach target,
        # invisible for the inactive arm.
        active = self.ACTIVE_ARM
        inactive = "right" if active == "left" else "left"

        active_cmd = getattr(self.commands, f"{active}_ee_pose")
        active_cmd.goal_pose_visualizer_cfg = CUBOID_MARKER_CFG.replace(
            prim_path=f"/Visuals/Command/{active}_goal_cube"
        )
        active_cmd.goal_pose_visualizer_cfg.markers["cuboid"].visual_material = (
            sim_utils.PreviewSurfaceCfg(diffuse_color=(1.0, 0.0, 0.0))
        )
        active_cmd.goal_pose_visualizer_cfg.markers["cuboid"].size = (0.05, 0.05, 0.05)

        inactive_cmd = getattr(self.commands, f"{inactive}_ee_pose")
        if hasattr(inactive_cmd, "goal_pose_visualizer_cfg") and inactive_cmd.goal_pose_visualizer_cfg is not None:
            for marker in inactive_cmd.goal_pose_visualizer_cfg.markers.values():
                marker.visible = False

        # Hide both arms' "current EE" markers to avoid confusing the VLM.
        for side in ("left", "right"):
            cmd = getattr(self.commands, f"{side}_ee_pose")
            if hasattr(cmd, "current_pose_visualizer_cfg"):
                for marker in cmd.current_pose_visualizer_cfg.markers.values():
                    marker.visible = False

        # Both arm action terms remain present to keep the action space shape
        # stable across L0a / L0; runtime IsaacLabEnvInterface masks the inactive
        # arm's 3 dims by zero-filling them, which our hold-in-place reset
        # makes safe (V3 fix).
        for side in ("left", "right"):
            setattr(
                self.actions,
                f"{side}_arm_action",
                DifferentialInverseKinematicsActionCfg(
                    asset_name="robot",
                    joint_names=[f"openarm_{side}_joint.*"],
                    body_name=f"openarm_{side}_hand",
                    controller=DifferentialIKControllerCfg(
                        command_type="position",
                        use_relative_mode=False,
                        ik_method="dls",
                    ),
                    scale=1.0,
                ),
            )

        self.scene.num_envs = 1
        self.scene.env_spacing = 2.5


@configclass
class L0aSingleReachLeftEnvCfg(_L0aSingleReachBaseCfg):
    """Single-arm reach: left arm reaches the (red) target."""

    ACTIVE_ARM: str = "left"


@configclass
class L0aSingleReachRightEnvCfg(_L0aSingleReachBaseCfg):
    """Single-arm reach: right arm reaches the (red) target."""

    ACTIVE_ARM: str = "right"
