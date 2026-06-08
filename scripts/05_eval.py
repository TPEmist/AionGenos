# Copyright (c) 2026, AionGenos Cognitive Evolution Pipeline
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""Launch script to evaluate and compare student vs teacher performance."""

import argparse
import logging
import os
import sys

# Setup logging — IsaacLab reconfigures the root logger after AppLauncher,
# so we install a stream handler on the aiongenos namespace explicitly.
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

# Add custom arguments
parser = argparse.ArgumentParser(description="Evaluate and compare teacher vs student endpoints.")
parser.add_argument("--num_episodes", type=int, default=5, help="Number of episodes to evaluate.")
parser.add_argument("--level", type=int, default=0, help="Curriculum level to evaluate (0-4).")
parser.add_argument("--teacher_url", type=str, default=None, help="Overrides VLM teacher URL.")
parser.add_argument("--student_url", type=str, default=None, help="Overrides VLM student URL.")
parser.add_argument("--sim_steps", type=int, default=None, help="Override sim_steps_per_subgoal (e.g. 600 for ~10s).")
parser.add_argument("--skip_teacher", action="store_true", help="Skip teacher eval (student-only).")
parser.add_argument("--skip_student", action="store_true", help="Skip student eval (teacher-only).")
parser.add_argument(
    "--dump_images",
    action="store_true",
    help="Dump per-round RGB pre/post + meta.json under data/eval_dumps/.",
)
parser.add_argument(
    "--dump_root",
    type=str,
    default="data/eval_dumps",
    help="Root directory for dumped images when --dump_images is set.",
)
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
    
    from datetime import datetime
    from pathlib import Path

    dump_root: Path | None = None
    run_stamp: str | None = None
    if args_cli.dump_images:
        run_stamp = f"L{args_cli.level}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        dump_root = Path(args_cli.dump_root) / run_stamp
        dump_root.mkdir(parents=True, exist_ok=True)
        logger.info(f"Image dump enabled: {dump_root}")

    try:
        teacher_metrics = None
        student_metrics = None

        # 1. Evaluate Teacher
        if not args_cli.skip_teacher:
            logger.info("Evaluating Teacher Endpoint...")
            teacher_metrics = run_eval(
                config=config,
                env=env_interface,
                level_config=level_config,
                vlm_url=config.teacher_url,
                num_episodes=args_cli.num_episodes,
                sim_steps_override=args_cli.sim_steps,
                dump_root=dump_root,
                run_label="teacher" if dump_root else None,
            )

        # 2. Evaluate Student
        if not args_cli.skip_student:
            logger.info("Evaluating Student Endpoint...")
            student_metrics = run_eval(
                config=config,
                env=env_interface,
                level_config=level_config,
                vlm_url=config.student_url,
                num_episodes=args_cli.num_episodes,
                sim_steps_override=args_cli.sim_steps,
                dump_root=dump_root,
                run_label="student" if dump_root else None,
            )

        print("\n" + "=" * 60)
        print("           EVALUATION RESULTS SUMMARY           ")
        print("=" * 60)
        print(f"Curriculum Level:   {args_cli.level} ({level_config.name})")
        print(f"Number of Episodes: {args_cli.num_episodes}")
        print(f"sim_steps_per_subgoal: {args_cli.sim_steps if args_cli.sim_steps else level_config.sim_steps_per_subgoal}")
        print("-" * 60)

        def _summarize(label: str, m: dict) -> None:
            print(f"[{label}]")
            print(f"  Success Rate           : {m['success_rate']:.1%}  ({int(m['success_episodes'])}/{int(m['total_episodes'])})")
            print(f"  Avg Rounds / Episode   : {m['avg_rounds_per_episode']:.1f}")
            print(f"  Total VLM Calls        : {int(m['total_vlm_calls'])}")
            print(f"  Parse Fail             : {int(m['parse_fail'])}")
            print(f"  Avg Latency / VLM call : {m['avg_latency_ms']:.0f} ms")
            print(f"  Avg Episode Duration   : {m['avg_duration_s']:.1f} s")
            print(f"  Avg Grounding Err  L/R : {m['avg_grounding_err_left_m']*100:.1f} / {m['avg_grounding_err_right_m']*100:.1f} cm")
            print(f"  Avg Final Dist     L/R : {m['avg_final_dist_left_m']*100:.1f} / {m['avg_final_dist_right_m']*100:.1f} cm")
            print(f"  Outcome Distribution   : {m['outcome_counts']}")

        if teacher_metrics is not None:
            _summarize("TEACHER", teacher_metrics)
        if student_metrics is not None:
            _summarize("STUDENT", student_metrics)

        if teacher_metrics is not None and student_metrics is not None:
            gap = compute_distillation_gap(
                teacher_sr=teacher_metrics["success_rate"],
                student_sr=student_metrics["success_rate"],
                teacher_latency_ms=teacher_metrics["avg_latency_ms"],
                student_latency_ms=student_metrics["avg_latency_ms"],
            )
            print("-" * 60)
            print(f"Success Rate Ratio:   {gap['sr_ratio']:.2f} (Target: >= 0.70)")
            print(f"Latency Ratio:        {gap['latency_ratio']:.2f} (Target: <= 0.13)")
            print(f"Speedup Factor:       {gap['speedup_factor']:.2f}x")
        print("=" * 60 + "\n")

    except Exception as e:
        logger.exception(f"Error during evaluation execution: {e}")
    finally:
        # Clean up environment and close app
        logger.info("Shutting down environment and simulator...")
        env.close()

if __name__ == "__main__":
    main()
    simulation_app.close()
