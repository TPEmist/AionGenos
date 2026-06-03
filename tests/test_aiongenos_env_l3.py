# Copyright (c) 2026, AionGenos Cognitive Evolution Pipeline
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""Test Level 3 environment registration and execution within Isaac Sim."""

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

class TestAionGenosL3Env(unittest.TestCase):
    """Test suite to verify custom level 3 environment."""

    def test_env_l3_lifecycle(self):
        """Verify that Level 3 environment can be created, run, and parsed."""
        print("Building Level 3 Environment...")
        env = ArenaEnvBuilder.build_env(level=3, num_envs=1)
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
        level_cfg = LEVEL_CONFIGS[3]
        state = env_interface.get_state(level_cfg)
        self.assertIn("left_x", state)
        self.assertIn("right_x", state)
        self.assertIn("left_p", state)
        self.assertIn("right_p", state)
        self.assertIn("left_yaw", state)
        self.assertIn("right_yaw", state)
        self.assertIn("left_gripper", state)
        self.assertIn("right_gripper", state)
        
        # Check action space shape
        action_shape = env.action_space.shape
        print(f"Action space shape: {action_shape}")
        # L3: left_arm_action (7), left_gripper_action (1), right_arm_action (7), right_gripper_action (1) -> total 16
        self.assertEqual(action_shape, (1, 16), "L3 Dual Pick & Place action space should be shape (1, 16)")

        # Clean up
        print("Closing environment...")
        env.close()

if __name__ == "__main__":
    unittest.main()
