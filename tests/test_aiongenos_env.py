# Copyright (c) 2026, AionGenos Cognitive Evolution Pipeline
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""Test environment registration and execution within Isaac Sim."""

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

class TestAionGenosEnv(unittest.TestCase):
    """Test suite to verify custom level 0 environment."""

    def test_env_lifecycle(self):
        """Verify that Level 0 environment can be created, run, and parsed."""
        print("Building Level 0 Environment...")
        env = ArenaEnvBuilder.build_env(level=0, num_envs=1)
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
        level_cfg = LEVEL_CONFIGS[0]
        state = env_interface.get_state(level_cfg)
        self.assertIn("left_x", state)
        self.assertIn("right_x", state)
        self.assertIn("left_target_color", state)
        self.assertIn("right_target_color", state)
        
        # Check action space shape
        action_shape = env.action_space.shape
        print(f"Action space shape: {action_shape}")
        self.assertEqual(action_shape, (1, 6), "L0 Reach Two Cubes action space should be shape (1, 6)")

        # Step environment with zero action
        print("Stepping environment with zero commands...")
        action_tensor = torch.zeros((1, 6), device=env.unwrapped.device)
        obs, reward, terminated, truncated, info = env.step(action_tensor)
        self.assertIsNotNone(obs)
        
        # Verify body position retrieval
        left_pos_b, right_pos_b, left_quat_w, right_quat_w = env_interface._get_ee_poses()
        print(f"Left EE Position (base): {left_pos_b}")
        print(f"Right EE Position (base): {right_pos_b}")
        self.assertEqual(left_pos_b.shape, (3,))
        self.assertEqual(right_pos_b.shape, (3,))
        
        # Verify target pose retrieval
        left_target, right_target = env_interface._get_target_poses()
        print(f"Left Target (world): {left_target}")
        print(f"Right Target (world): {right_target}")
        self.assertEqual(left_target.shape, (3,))
        self.assertEqual(right_target.shape, (3,))

        # Clean up
        print("Closing environment...")
        env.close()

if __name__ == "__main__":
    unittest.main()
