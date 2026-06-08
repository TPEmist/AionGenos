#!/usr/bin/env python3
"""Sync local replays to remote server and trigger QLoRA training + reloading."""

import argparse
import logging
import sys
from pathlib import Path

# Setup simple logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Add root folder to python path for AionGenos imports
sys.path.append(str(Path(__file__).parent.parent.resolve()))

from aiongenos.config import AionGenosConfig
from aiongenos.replay.sync import sync_replays_to_remote
from aiongenos.pipeline.stage4_distill_remote_trigger import (
    trigger_remote_train,
    trigger_remote_export_and_reload,
)


def get_latest_run_id(replay_base: Path) -> str:
    """Find the most recently modified run_id directory."""
    if not replay_base.exists():
        raise FileNotFoundError(f"Replay base directory does not exist: {replay_base}")
    
    subdirs = [d for d in replay_base.iterdir() if d.is_dir()]
    if not subdirs:
        raise ValueError(f"No run directories found in {replay_base}")
        
    # Sort by modification time (most recent first)
    subdirs.sort(key=lambda d: d.stat().st_mtime, reverse=True)
    return subdirs[0].name


def main():
    parser = argparse.ArgumentParser(description="AionGenos Sync and Remote Training Trigger")
    parser.add_argument("--run-id", type=str, help="Run ID to train on. Defaults to latest local run.")
    parser.add_argument("--ssh-key", type=str, help="Optional SSH key path for remote server access.")
    parser.add_argument("--base-model", type=str, help="Hugging Face base model ID to use (e.g. google/gemma-4-E4B-it).")
    args = parser.parse_args()

    # Load configuration
    config = AionGenosConfig()
    
    # 1. Resolve Run ID
    run_id = args.run_id
    if not run_id:
        try:
            run_id = get_latest_run_id(config.local_replay_path)
            logger.info(f"Auto-detected latest run ID: {run_id}")
        except Exception as e:
            logger.error(f"Failed to auto-detect run ID: {e}")
            sys.exit(1)

    logger.info(f"=== Syncing and Training Run ID: {run_id} ===")

    # 2. Sync replays to remote server
    logger.info("Step 1: Syncing local replays to remote server...")
    sync_ok = sync_replays_to_remote(
        local_path=config.local_replay_path,
        remote_host=config.remote_host,
        remote_user=config.remote_user,
        remote_path=config.remote_replay_path,
        ssh_key=args.ssh_key,
    )
    
    if not sync_ok:
        logger.error("Replay sync failed. Aborting training trigger.")
        sys.exit(1)
    
    # 3. Trigger remote QLoRA training
    logger.info("Step 2: Triggering remote QLoRA training...")
    train_ok = trigger_remote_train(
        remote_host=config.remote_host,
        remote_user=config.remote_user,
        replay_path=config.remote_replay_path,
        run_id=run_id,
        ssh_key=args.ssh_key,
        remote_python=config.remote_python,
        base_model=args.base_model,
    )
    
    if not train_ok:
        logger.error("Remote training failed. Aborting export/reload.")
        sys.exit(1)

    # 4. Export LoRA adapter to GGUF and reload student server
    logger.info("Step 3: Exporting LoRA to GGUF and reloading student server...")
    reload_ok = trigger_remote_export_and_reload(
        remote_host=config.remote_host,
        remote_user=config.remote_user,
        run_id=run_id,
        ssh_key=args.ssh_key,
        remote_python=config.remote_python,
        base_model=args.base_model,
    )

    if reload_ok:
        logger.info("=== Distillation and reload completed successfully! ===")
    else:
        logger.error("Export/reload failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
