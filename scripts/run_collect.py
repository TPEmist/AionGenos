# Copyright (c) 2026, AionGenos Cognitive Evolution Pipeline
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""Launch script to run the AionGenos Cognitive Evolution collector orchestrator loop."""

import argparse
import logging
import os
import sys
from pathlib import Path

# Setup logging — IsaacLab's AppLauncher reconfigures the root logger after
# import (see scripts/05_eval.py for the same fix). Install a stream handler
# directly on the aiongenos.* loggers so per-round INFO lines from
# collect/eval/stage1 still reach stdout.
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
parser = argparse.ArgumentParser(description="Run bimanual cognitive collect loop.")
parser.add_argument("--num_episodes", type=int, default=5, help="Number of episodes to collect.")
parser.add_argument("--level", type=int, default=0, help="Initial curriculum level to run (-2..4).")
parser.add_argument("--teacher_url", type=str, default=None, help="Overrides VLM teacher URL.")
parser.add_argument(
    "--dump_images_root",
    type=str,
    default=None,
    help="When set, write per-round RGB pairs and meta.json under "
         "{dump_images_root}/{run_id}/{episode_id}/. Use for V4 playback.",
)
parser.add_argument(
    "--recap_buffer_root",
    type=str,
    default=None,
    help="Phase 4: when set, after each ep generate + persist a self-recap to "
         "this directory (default workspace/recaps). Enables both write (this run) "
         "and read (memory retrieval) of the buffer.",
)
parser.add_argument(
    "--use_memory",
    action="store_true",
    help="Phase 4: at R1 of each ep, retrieve top-K visually similar past "
         "recaps from --recap_buffer_root and inject into the teacher prompt. "
         "Requires --recap_buffer_root.",
)
parser.add_argument(
    "--memory_top_k", type=int, default=3, help="Top-K retrieved recaps (default 3).",
)
parser.add_argument(
    "--memory_success_only", action="store_true",
    help="Filter retrieval to is_success=True recaps only (default: include both).",
)
parser.add_argument(
    "--memory_image_weight", type=float, default=0.4,
    help="Weight on image cosine in retrieval score (Phase 4 R2). 0.4 = state-leaning.",
)
parser.add_argument(
    "--memory_state_scale_cm", type=float, default=30.0,
    help="State similarity decay scale: state_sim = exp(-d_cm/scale).",
)
parser.add_argument(
    "--memory_success_floor", type=float, default=2.0/3.0,
    help="Minimum fraction of top-K that must be from success episodes (Q12).",
)
parser.add_argument(
    "--memory_mode_flag_path", type=str, default=None,
    help="Optional path to a file the watcher (R4/L2) toggles to flip retrieval "
         "to success-only during SR-dip recovery.",
)
parser.add_argument(
    "--env_seed_base", type=int, default=None,
    help="Amendment 7 §7.7 / Amendment 10 §10.4: base seed for deterministic "
         "env.reset. Per-ep seed = env_seed_base + ep_idx, so multiple D11 "
         "eval arms replay the same initial pose sequence (paired-samples "
         "statistical efficiency on T1). Omit to keep legacy random resets.",
)
parser.add_argument(
    "--recap_buffer_readonly", action="store_true",
    help="Amendment 8 §8.5: freeze buffer during eval — retrieval reads from "
         "existing recaps, but no new recaps are persisted this run. Required "
         "for the C_retrieval arm so its 'external memory' remains a "
         "point-in-time snapshot comparable to B_main's frozen weights.",
)
parser.add_argument(
    "--eval_template_variant",
    type=str,
    default=None,
    choices=(None, "action_only", "rationale", "gist_only",
             "rationale_with_gist", "rationale_with_retrieval"),
    help="Amendment 8 §8.5: per-arm inference prompt variant. "
         "action_only=A_action_only, rationale=A_ctrl_rat, "
         "gist_only=D_gist, rationale_with_gist=B_main, "
         "rationale_with_retrieval=C_retrieval. If unset, falls back to "
         "legacy teacher template with THOUGHT slot (D6/D10 backwards-compat). "
         "Only POSITION_ONLY (L0) is supported in Phase 4.",
)
parser.add_argument(
    "--freeze_level", action="store_true",
    help="When set, curriculum never auto-advances even if SR ≥ threshold. "
         "Required for single-task paper-quality collects: ext-5 auto-advanced "
         "from L0a-Left to L0a-Right at ep 11 (SR hit 60%), contaminating the "
         "run with a different task.",
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
from aiongenos.curriculum.manager import AionGenosCurriculumManager
from aiongenos.curriculum.arena_adapter import ArenaEnvBuilder
from aiongenos.replay.buffer import ReplayBuffer
from aiongenos.orchestrator import run_collect_loop, IsaacLabEnvInterface

def main():
    logger.info("Initializing AionGenos collector orchestrator...")
    
    # Initialize global config
    config = AionGenosConfig()
    if args_cli.teacher_url:
        config.teacher_url = args_cli.teacher_url
        
    logger.info(f"VLM Teacher URL: {config.teacher_url}")
    
    # Initialize ReplayBuffer
    replay = ReplayBuffer(config.local_replay_path)
    logger.info(f"Writing replays to: {config.local_replay_path}")
    
    # Initialize CurriculumManager
    curriculum = AionGenosCurriculumManager(
        config=config.curriculum,
        replay_buffer=replay,
        start_level=args_cli.level,
        freeze_level=args_cli.freeze_level,
    )
    if args_cli.freeze_level:
        logger.info(f"Curriculum FROZEN at level {args_cli.level} — no auto-advance")
    
    # Build environment using Arena/IsaacLab builder
    logger.info(f"Building environment for Level {args_cli.level}...")
    env = ArenaEnvBuilder.build_env(level=args_cli.level, num_envs=1)
    
    # Wrap environment with the concrete EnvInterface
    env_interface = IsaacLabEnvInterface(env)

    # Phase 4: wire optional memory buffer + retriever
    recap_buffer = None
    memory_retriever = None
    if args_cli.recap_buffer_root:
        from aiongenos.memory.recap_buffer import RecapBuffer
        recap_buffer = RecapBuffer(root=args_cli.recap_buffer_root)
        recap_buffer.load()
        logger.info(f"Recap buffer at {args_cli.recap_buffer_root}: {len(recap_buffer)} existing records")
        if args_cli.use_memory:
            from aiongenos.memory.retriever import MemoryRetriever
            memory_retriever = MemoryRetriever(
                buffer=recap_buffer,
                top_k=args_cli.memory_top_k,
                success_only=args_cli.memory_success_only,
                embedder_device="cpu",
                image_weight=args_cli.memory_image_weight,
                state_scale_cm=args_cli.memory_state_scale_cm,
                success_floor_frac=args_cli.memory_success_floor,
                success_only_flag_path=args_cli.memory_mode_flag_path,
            )
            logger.info(
                f"Memory retrieval enabled: top_k={args_cli.memory_top_k} "
                f"img_w={args_cli.memory_image_weight} state_scale={args_cli.memory_state_scale_cm}cm "
                f"success_floor={args_cli.memory_success_floor:.2f} "
                f"mode_flag={args_cli.memory_mode_flag_path or '(none)'}"
            )
    elif args_cli.use_memory:
        logger.warning("--use_memory ignored (no --recap_buffer_root provided)")

    try:
        # Run end-to-end collect loop
        stats = run_collect_loop(
            config=config,
            env=env_interface,
            curriculum=curriculum,
            replay=replay,
            max_episodes=args_cli.num_episodes,
            check_advance_every=10,
            dump_images_root=Path(args_cli.dump_images_root) if args_cli.dump_images_root else None,
            memory_retriever=memory_retriever,
            recap_buffer=recap_buffer,
            eval_template_variant=args_cli.eval_template_variant,
            recap_buffer_readonly=args_cli.recap_buffer_readonly,
            env_seed_base=args_cli.env_seed_base,
        )
        logger.info("Collect loop execution complete.")
        logger.info(f"Stats summary: {stats}")
    except Exception as e:
        logger.exception(f"Error during collect loop execution: {e}")
    finally:
        # Clean up environment and close app
        logger.info("Shutting down environment and simulator...")
        env.close()

if __name__ == "__main__":
    main()
    simulation_app.close()
