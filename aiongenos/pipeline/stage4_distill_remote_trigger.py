"""Stage 4 — Distillation remote trigger.

Triggers the remote server to:
1. Run QLoRA training on success replays
2. Export LoRA to GGUF
3. Reload student llama-server with new adapter
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def trigger_remote_train(
    remote_host: str,
    remote_user: str,
    replay_path: str,
    run_id: str,
    ssh_key: Optional[str] = None,
) -> bool:
    """Trigger QLoRA training on the remote server via SSH.

    Args:
        remote_host: Remote server IP/hostname.
        remote_user: SSH username.
        replay_path: Path to replays on remote server.
        run_id: Current run ID for training data selection.
        ssh_key: Optional SSH key path.

    Returns:
        True if trigger succeeded.
    """
    ssh_args = ["ssh"]
    if ssh_key:
        ssh_args.extend(["-i", ssh_key])
    ssh_args.append(f"{remote_user}@{remote_host}")

    # Build remote command
    remote_cmd = (
        f"cd /data/aiongenos && "
        f"python3 server_side/train_qlora_gemma4.py "
        f"--replay-path {replay_path}/{run_id}/success "
        f"--output-dir /data/lora_checkpoints/{run_id} "
        f"2>&1 | tee /data/logs/train_{run_id}.log"
    )
    ssh_args.append(remote_cmd)

    logger.info(f"Triggering remote training: {' '.join(ssh_args)}")

    try:
        result = subprocess.run(
            ssh_args,
            capture_output=True,
            text=True,
            timeout=7200,  # 2 hour timeout for training
        )
        if result.returncode == 0:
            logger.info("Remote training completed successfully")
            return True
        else:
            logger.error(f"Remote training failed: {result.stderr[:500]}")
            return False
    except subprocess.TimeoutExpired:
        logger.error("Remote training timed out after 2 hours")
        return False
    except Exception as e:
        logger.error(f"Remote training trigger error: {e}")
        return False


def trigger_remote_export_and_reload(
    remote_host: str,
    remote_user: str,
    run_id: str,
    ssh_key: Optional[str] = None,
) -> bool:
    """Export LoRA to GGUF and reload student server.

    Args:
        remote_host: Remote server IP/hostname.
        remote_user: SSH username.
        run_id: Run ID for checkpoint path.
        ssh_key: Optional SSH key path.

    Returns:
        True if export + reload succeeded.
    """
    ssh_args = ["ssh"]
    if ssh_key:
        ssh_args.extend(["-i", ssh_key])
    ssh_args.append(f"{remote_user}@{remote_host}")

    remote_cmd = (
        f"cd /data/aiongenos && "
        f"python3 server_side/export_lora_gguf.py "
        f"--checkpoint-dir /data/lora_checkpoints/{run_id} "
        f"--output /data/lora_gguf/{run_id}/adapter.gguf && "
        f"bash server_side/reload_student.sh /data/lora_gguf/{run_id}/adapter.gguf"
    )
    ssh_args.append(remote_cmd)

    logger.info(f"Triggering export + reload: {' '.join(ssh_args)}")

    try:
        result = subprocess.run(
            ssh_args,
            capture_output=True,
            text=True,
            timeout=600,
        )
        if result.returncode == 0:
            logger.info("Export + reload completed successfully")
            return True
        else:
            logger.error(f"Export/reload failed: {result.stderr[:500]}")
            return False
    except Exception as e:
        logger.error(f"Export/reload error: {e}")
        return False
