# Copyright (c) 2026, AionGenos Cognitive Evolution Pipeline
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

import math
import isaaclab.sim as sim_utils
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
                # Corrected quaternion signs for (orient: x0, y-35, z-90)
                rot=(0.67438, -0.21263, -0.21263, -0.67438),
                convention="world",
            ),
        )

        # Ensure that simulation outputs RGB images at correct intervals
        self.sim.render_interval = self.decimation
