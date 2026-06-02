# Copyright (c) 2026, AionGenos Cognitive Evolution Pipeline
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""Test Level 1 environment registration and execution within Isaac Sim."""

import argparse
import sys
import unittest
import torch
import numpy as np

from isaaclab.app import AppLauncher

# Set simulation to headless for automated testing
args_cli = argparse.Namespace(headless=True, num_envs=1, use_fabric=True, enable_cameras=True)
app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

from aiongenos.curriculum.arena_adapter import ArenaEnvBuilder
from aiongenos.orchestrator.isaaclab_env_interface import IsaacLabEnvInterface
from aiongenos.config import LEVEL_CONFIGS

class TestAionGenosL1Env(unittest.TestCase):
    """Test suite to verify custom level 1 environment."""

    def test_env_l1_lifecycle(self):
        """Verify that Level 1 environment can be created, run, and parsed."""
        print("Building Level 1 Environment...")
        env = ArenaEnvBuilder.build_env(level=1, num_envs=1)
        self.assertIsNotNone(env)

        # Wrap with interface
        print("Wrapping environment in IsaacLabEnvInterface...")
        env_interface = IsaacLabEnvInterface(env)
        
        # Reset environment
        print("Resetting environment...")
        env_interface.reset()
        
        # Capture RGB image
        print("Capturing RGB image from camera...")
        rgb_bytes = env_interface.get_rgb()
        self.assertGreater(len(rgb_bytes), 0, "RGB image should not be empty")
        
        # Verify state formatting
        print("Fetching environment state dict...")
        level_cfg = LEVEL_CONFIGS[1]
        state = env_interface.get_state(level_cfg)
        self.assertIn("left_x", state)
        self.assertIn("right_x", state)
        
        # Check action space shape
        action_shape = env.action_space.shape
        print(f"Action space shape: {action_shape}")
        self.assertEqual(action_shape, (1, 6), "L1 Dual Trace action space should be shape (1, 6)")

        # Clean up
        print("Closing environment...")
        env.close()

if __name__ == "__main__":
    unittest.main()
