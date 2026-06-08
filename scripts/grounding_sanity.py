# Copyright (c) 2026, AionGenos Cognitive Evolution Pipeline
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""Launch script to measure grounding bias and variance on a fixed environment state."""

import argparse
import logging
import os
import sys
import numpy as np

# Setup logging
_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
for _name in ("aiongenos", "__main__"):
    _l = logging.getLogger(_name)
    _l.setLevel(logging.INFO)
    _l.addHandler(_handler)
    _l.propagate = False
logger = logging.getLogger(__name__)

# Launch Isaac Sim Simulator first
from isaaclab.app import AppLauncher

parser = argparse.ArgumentParser(description="Measure grounding bias and variance on a fixed scene.")
parser.add_argument("--num_queries", type=int, default=20, help="Number of queries to perform.")
parser.add_argument("--level", type=int, default=0, help="Curriculum level (0-4).")
parser.add_argument("--vlm_url", type=str, default=None, help="VLM endpoint URL (defaults to teacher_url).")
parser.add_argument("--temperature", type=float, default=0.7, help="VLM temperature.")

# Append AppLauncher CLI args
AppLauncher.add_app_launcher_args(parser)
args_cli = parser.parse_args()

# Launch the simulation app
app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

# Rest of the imports follow simulation launch
import gymnasium as gym
import torch

from aiongenos.config import AionGenosConfig
from aiongenos.curriculum.arena_adapter import ArenaEnvBuilder
from aiongenos.orchestrator.isaaclab_env_interface import IsaacLabEnvInterface
from aiongenos.pipeline.stage1_reasoning import run_stage1
from aiongenos.vlm.scalar_guard import position_metric_to_int


def main():
    logger.info("Initializing Grounding Sanity checker...")

    config = AionGenosConfig()
    vlm_url = args_cli.vlm_url or config.teacher_url
    logger.info(f"Target VLM URL: {vlm_url}")

    level_config = config.get_level_config(args_cli.level)
    bounds = level_config.workspace_bounds

    # Build and wrap environment
    logger.info(f"Building environment for Level {args_cli.level}...")
    env = ArenaEnvBuilder.build_env(level=args_cli.level, num_envs=1)
    env_interface = IsaacLabEnvInterface(env)

    try:
        # Reset once to freeze state
        logger.info("Resetting environment to acquire fixed state...")
        env_interface.reset()

        # Capture fixed image and state
        rgb_bytes = env_interface.get_rgb()
        state = env_interface.get_state(level_config)
        try:
            state["instruction"] = level_config.task_instruction_template.format(**state)
        except Exception:
            state["instruction"] = level_config.task_instruction_template

        # Get GT targets in base frame
        root_pos_w = env_interface.robot.data.root_pos_w[0].cpu().numpy()
        left_target_w, right_target_w = env_interface._get_target_poses()

        left_target_b = left_target_w - root_pos_w
        right_target_b = right_target_w - root_pos_w

        gt_left, _ = position_metric_to_int(
            left_target_b[0], left_target_b[1], left_target_b[2],
            bounds.x_bounds, bounds.y_bounds, bounds.z_bounds
        )
        gt_right, _ = position_metric_to_int(
            right_target_b[0], right_target_b[1], right_target_b[2],
            bounds.x_bounds, bounds.y_bounds, bounds.z_bounds
        )

        logger.info(f"Ground Truth Targets (Integer Grid):")
        logger.info(f"  Left Target (Red) : X={gt_left[0]}, Y={gt_left[1]}, Z={gt_left[2]}")
        logger.info(f"  Right Target (Blue): X={gt_right[0]}, Y={gt_right[1]}, Z={gt_right[2]}")

        left_preds = []
        right_preds = []
        latencies = []
        failures = 0

        logger.info(f"Starting {args_cli.num_queries} repeat queries on the fixed state...")
        for i in range(args_cli.num_queries):
            logger.info(f"Query {i+1}/{args_cli.num_queries}...")
            parsed, latency, err = run_stage1(
                level_config=level_config,
                teacher_url=vlm_url,
                rgb_bytes=rgb_bytes,
                state=state,
                conversation=None,  # Zero-shot, no history
                critic_feedback=None,
                temperature=args_cli.temperature,
                max_retries=2,
            )

            if parsed is None or err is not None:
                logger.warning(f"Query {i+1} failed to parse or VLM error: {err}")
                failures += 1
                continue

            latencies.append(latency)
            left_preds.append([parsed.left.position.x, parsed.left.position.y, parsed.left.position.z])
            right_preds.append([parsed.right.position.x, parsed.right.position.y, parsed.right.position.z])

        # Analyze statistics
        if not left_preds:
            logger.error("All queries failed. Unable to compute statistics.")
            return

        left_preds = np.array(left_preds)
        right_preds = np.array(right_preds)
        latencies = np.array(latencies)

        # Means and Stddevs
        mean_l = np.mean(left_preds, axis=0)
        std_l = np.std(left_preds, axis=0)
        bias_l = mean_l - np.array(gt_left)

        mean_r = np.mean(right_preds, axis=0)
        std_r = np.std(right_preds, axis=0)
        bias_r = mean_r - np.array(gt_right)

        print("\n" + "=" * 60)
        print("          GROUNDING SANITY ANALYSIS REPORT          ")
        print("=" * 60)
        print(f"VLM Endpoint   : {vlm_url}")
        print(f"Total Queries  : {args_cli.num_queries}")
        print(f"Success/Fail   : {len(left_preds)} / {failures}")
        print(f"Avg Latency    : {np.mean(latencies):.1f} ms")
        print("-" * 60)
        print("LEFT ARM (Red Target):")
        print(f"  GT Target    : (X={gt_left[0]:4d}, Y={gt_left[1]:4d}, Z={gt_left[2]:4d})")
        print(f"  Mean Pred    : (X={mean_l[0]:4.1f}, Y={mean_l[1]:4.1f}, Z={mean_l[2]:4.1f})")
        print(f"  Std Pred     : (X={std_l[0]:4.1f}, Y={std_l[1]:4.1f}, Z={std_l[2]:4.1f})")
        print(f"  Bias (Mean-GT: (X={bias_l[0]:+4.1f}, Y={bias_l[1]:+4.1f}, Z={bias_l[2]:+4.1f})")
        print("-" * 60)
        print("RIGHT ARM (Blue Target):")
        print(f"  GT Target    : (X={gt_right[0]:4d}, Y={gt_right[1]:4d}, Z={gt_right[2]:4d})")
        print(f"  Mean Pred    : (X={mean_r[0]:4.1f}, Y={mean_r[1]:4.1f}, Z={mean_r[2]:4.1f})")
        print(f"  Std Pred     : (X={std_r[0]:4.1f}, Y={std_r[1]:4.1f}, Z={std_r[2]:4.1f})")
        print(f"  Bias (Mean-GT: (X={bias_r[0]:+4.1f}, Y={bias_r[1]:+4.1f}, Z={bias_r[2]:+4.1f})")
        print("=" * 60 + "\n")

    except Exception as e:
        logger.exception(f"Error during grounding sanity check: {e}")
    finally:
        logger.info("Shutting down environment and simulator...")
        env.close()


if __name__ == "__main__":
    main()
    simulation_app.close()
