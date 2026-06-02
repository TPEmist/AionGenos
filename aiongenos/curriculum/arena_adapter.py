# Copyright (c) 2026, AionGenos Cognitive Evolution Pipeline
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""Arena adapter for AionGenos.

Provides an interface to construct and adapt IsaacLab-Arena environments
for curriculum-based training, with fallback to core IsaacLab configurations.
"""

import logging
import gymnasium as gym
from typing import Any

from aiongenos.curriculum.ladder import CurriculumLadder
import isaaclab_tasks  # Auto-registers IsaacLab built-in tasks

# If IsaacLab-Arena is installed/available, we could import it here.
# For this POC, we support native IsaacLab tasks and custom registered tasks.
try:
    import isaaclab_arena
    ARENA_AVAILABLE = True
except ImportError:
    ARENA_AVAILABLE = False

logger = logging.getLogger(__name__)

class ArenaEnvBuilder:
    """Builder class for AionGenos environments using Arena/IsaacLab."""

    @staticmethod
    def build_env(level: int, num_envs: int = 1, use_fabric: bool = True) -> gym.Env:
        """Build and return a Gymnasium environment for the specified curriculum level.

        Args:
            level: The curriculum level index (0-4).
            num_envs: The number of environments to simulate in parallel.
            use_fabric: Whether to enable Fabric for fast GPU communication.

        Returns:
            The configured and created Gymnasium environment.
        """
        gym_id = CurriculumLadder.get_gym_id(level)
        logger.info(f"Building environment for Level {level} (Gym ID: {gym_id}), num_envs={num_envs}")

        # Import task configs dynamically to ensure they are registered
        import aiongenos.tasks  # noqa: F401

        from isaaclab_tasks.utils import parse_env_cfg
        env_cfg = parse_env_cfg(gym_id, num_envs=num_envs, use_fabric=use_fabric)

        # Create gymnasium environment
        env = gym.make(gym_id, cfg=env_cfg)
        logger.info(f"Successfully created environment {gym_id}")
        return env
