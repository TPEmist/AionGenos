# Copyright (c) 2026, AionGenos Cognitive Evolution Pipeline
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

import math
import isaaclab.envs.mdp as mdp
import isaaclab.sim as sim_utils
from aiongenos.mdp.reset import reset_joints_to_target_with_offset
from isaaclab.envs import ManagerBasedRLEnvCfg
from isaaclab.managers import ActionTermCfg as ActionTerm
from isaaclab.managers import CurriculumTermCfg as CurrTerm
from isaaclab.managers import EventTermCfg as EventTerm
from isaaclab.managers import ObservationGroupCfg as ObsGroup
from isaaclab.managers import ObservationTermCfg as ObsTerm
from isaaclab.managers import RewardTermCfg as RewTerm
from isaaclab.managers import SceneEntityCfg
from isaaclab.managers import TerminationTermCfg as DoneTerm
from isaaclab.sensors import CameraCfg
from isaaclab.utils import configclass
from isaaclab.utils.noise import AdditiveUniformNoiseCfg as Unoise

from isaaclab_tasks.manager_based.manipulation.reach.config.openarm.bimanual.reach_openarm_bi_env_cfg import ReachEnvCfg, ReachSceneCfg

@configclass
class AionGenosReachEnvBaseCfg(ReachEnvCfg):
    """Base environment configuration for all AionGenos tasks."""

    def __post_init__(self):
        super().__post_init__()

        # Add the high-resolution RGB camera for VLM observation
        self.scene.camera = CameraCfg(
            prim_path="{ENV_REGEX_NS}/Robot/Camera",
            update_period=0.0,  # Update every step
            height=256,
            width=256,
            data_types=["rgb"],
            spawn=sim_utils.PinholeCameraCfg(
                focal_length=12.0,
                focus_distance=400.0,
                horizontal_aperture=45.0,  # Wide FOV to capture hands and workspace
                clipping_range=(0.1, 1.0e5),
            ),
            # Positioned at the robot's head/neck looking forward and down at the table
            offset=CameraCfg.OffsetCfg(
                pos=(0.1, 0.0, 0.85),
                # Pure +35 degrees pitch under world convention (looking forward and down)
                rot=(0.95372, 0.0, 0.30071, 0.0),
                convention="world",
            ),
        )

        # Ensure that simulation outputs RGB images at correct intervals
        self.sim.render_interval = self.decimation

        # ── F35 fix: lock target through whole episode ──────────────────
        # IsaacLab's stock reach env resamples the goal pose every 4 sim-sec
        # (resampling_time_range=(4.0, 4.0) on each pose command). With our
        # multi-round episodes (≤40 rounds × 30 sim steps × 1/60 s ≈ up to
        # 20 sim-sec) the cube target jumps 2-5 times mid-episode; the VLM
        # sees its previously-correct guess suddenly become "wrong" and
        # rewrites its mental model. Run b6783e98 ep e892cd33 R17 caught
        # this in the act (right-arm dist 11.6→5.1cm with right arm
        # hold-in-place — only the GT target moved). For collect/eval we
        # want the target stable for the whole episode; "freeze" it by
        # pushing the resampling window past episode_length_s.
        _LOCK = (1e6, 1e6)  # effectively never resample
        self.commands.left_ee_pose.resampling_time_range = _LOCK
        self.commands.right_ee_pose.resampling_time_range = _LOCK

        # ── Initial-pose randomization (T-8a, F15 fix → C3 pre-reach) ─────
        # History:
        # • F15: IsaacLab's reset_joints_by_scale silently no-ops on OpenArm
        #   (default joints all zero, scale × 0 = 0).
        # • T-8a: switched to reset_joints_by_offset(±0.2 rad) — fixed X/Y
        #   diversity but Z still locked because the default pose has both
        #   arms hanging straight down, so the EE Z is dominated by the rigid
        #   forearm length.
        # • C3 (visual debug, F22): with arms hanging the wrist EEs land in
        #   the lower 1/3 of the camera image and frequently occlude the
        #   cube target. View-sanity script picked
        #     P1_mild_forward = {joint2: 0.5, joint4: 0.8}
        #   (i.e. shoulder pitched forward, elbow flexed) as the cleanest
        #   pre-reach pose: cube clearly visible, both EEs in frame, no
        #   self-occlusion across ~10 random samples.
        #
        # We use our custom reset_joints_to_target_with_offset which sets
        # the target joint pose first, then jitters by ±0.2 rad on top.
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
