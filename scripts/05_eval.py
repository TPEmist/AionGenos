# Copyright (c) 2026, AionGenos Cognitive Evolution Pipeline
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""Launch script to evaluate and compare student vs teacher performance."""

import argparse
import logging
import os
import sys

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Launch Isaac Sim Simulator first
from isaaclab.app import AppLauncher

# Add custom arguments
parser = argparse.ArgumentParser(description="Evaluate and compare teacher vs student endpoints.")
parser.add_argument("--num_episodes", type=int, default=5, help="Number of episodes to evaluate.")
parser.add_argument("--level", type=int, default=0, help="Curriculum level to evaluate (0-4).")
parser.add_argument("--teacher_url", type=str, default=None, help="Overrides VLM teacher URL.")
parser.add_argument("--student_url", type=str, default=None, help="Overrides VLM student URL.")
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
from aiongenos.orchestrator.eval import run_eval
from aiongenos.eval.metrics import compute_distillation_gap

def main():
    logger.info("Initializing AionGenos evaluation script...")
    
    # Initialize global config
    config = AionGenosConfig()
    if args_cli.teacher_url:
        config.teacher_url = args_cli.teacher_url
    if args_cli.student_url:
        config.student_url = args_cli.student_url
        
    logger.info(f"VLM Teacher URL: {config.teacher_url}")
    logger.info(f"VLM Student URL: {config.student_url}")
    
    level_config = config.get_level_config(args_cli.level)
    
    # Build environment using Arena/IsaacLab builder
    logger.info(f"Building environment for Level {args_cli.level}...")
    env = ArenaEnvBuilder.build_env(level=args_cli.level, num_envs=1)
    
    # Wrap environment with the concrete EnvInterface
    env_interface = IsaacLabEnvInterface(env)
    
    try:
        # 1. Evaluate Teacher
        logger.info("Evaluating Teacher Endpoint...")
        teacher_metrics = run_eval(
            config=config,
            env=env_interface,
            level_config=level_config,
            vlm_url=config.teacher_url,
            num_episodes=args_cli.num_episodes,
        )
        
        # 2. Evaluate Student
        logger.info("Evaluating Student Endpoint...")
        student_metrics = run_eval(
            config=config,
            env=env_interface,
            level_config=level_config,
            vlm_url=config.student_url,
            num_episodes=args_cli.num_episodes,
        )
        
        # 3. Compute and display distillation gap
        logger.info("Computing Distillation Gap...")
        gap = compute_distillation_gap(
            teacher_sr=teacher_metrics["success_rate"],
            student_sr=student_metrics["success_rate"],
            teacher_latency_ms=teacher_metrics["avg_latency_ms"],
            student_latency_ms=student_metrics["avg_latency_ms"],
        )
        
        print("\n" + "=" * 50)
        print("           EVALUATION RESULTS SUMMARY           ")
        print("=" * 50)
        print(f"Curriculum Level:   {args_cli.level} ({level_config.name})")
        print(f"Number of Episodes: {args_cli.num_episodes}")
        print("-" * 50)
        print(f"Teacher Success Rate: {gap['teacher_sr']:.1%}")
        print(f"Student Success Rate: {gap['student_sr']:.1%}")
        print(f"Success Rate Ratio:   {gap['sr_ratio']:.2f} (Target: >= 0.70)")
        print("-" * 50)
        print(f"Teacher Avg Latency:  {gap['teacher_latency_ms']:.0f} ms")
        print(f"Student Avg Latency:  {gap['student_latency_ms']:.0f} ms")
        print(f"Latency Ratio:        {gap['latency_ratio']:.2f} (Target: <= 0.13)")
        print(f"Speedup Factor:       {gap['speedup_factor']:.2f}x")
        print("=" * 50 + "\n")
        
    except Exception as e:
        logger.exception(f"Error during evaluation execution: {e}")
    finally:
        # Clean up environment and close app
        logger.info("Shutting down environment and simulator...")
        env.close()

if __name__ == "__main__":
    main()
    simulation_app.close()
