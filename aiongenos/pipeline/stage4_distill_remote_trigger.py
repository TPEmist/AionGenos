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
    remote_python: str = "python3",
    base_model: Optional[str] = None,
) -> bool:
    """Trigger QLoRA training on the remote server via SSH.

    Args:
        remote_host: Remote server IP/hostname.
        remote_user: SSH username.
        replay_path: Path to replays on remote server.
        run_id: Current run ID for training data selection.
        ssh_key: Optional SSH key path.
        remote_python: Path to python interpreter on remote server.
        base_model: Optional base model ID to use for training.

    Returns:
        True if trigger succeeded.
    """
    ssh_args = ["ssh"]
    if ssh_key:
        ssh_args.extend(["-i", ssh_key])
    ssh_args.append(f"{remote_user}@{remote_host}")

    base_model_arg = f"--base-model {base_model} " if base_model else ""

    # Build remote command
    remote_cmd = (
        f"cd ~/CYTu/AionGenos_server && "
        f"{remote_python} server_side/train_qlora_gemma4.py "
        f"--replay-path {replay_path}/{run_id}/success "
        f"--output-dir ~/CYTu/AionGenos_server/data/lora_checkpoints/{run_id} "
        f"{base_model_arg}"
        f"2>&1 | tee ~/CYTu/AionGenos_server/data/logs/train_{run_id}.log"
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
    remote_python: str = "python3",
    base_model: Optional[str] = None,
) -> bool:
    """Export LoRA to GGUF and reload student server.

    Args:
        remote_host: Remote server IP/hostname.
        remote_user: SSH username.
        run_id: Run ID for checkpoint path.
        ssh_key: Optional SSH key path.
        remote_python: Path to python interpreter on remote server.
        base_model: Optional base model ID to use for export.

    Returns:
        True if export + reload succeeded.
    """
    ssh_args = ["ssh"]
    if ssh_key:
        ssh_args.extend(["-i", ssh_key])
    ssh_args.append(f"{remote_user}@{remote_host}")

    base_model_arg = f"--base-model {base_model} " if base_model else ""

    model_env = ""
    if base_model and "E4B" in base_model:
        model_env = (
            "export MODEL_PATH=/home/exx/.cache/llama.cpp/unsloth_gemma-4-E4B-it-GGUF_gemma-4-E4B-it-Q4_K_M.gguf && "
            "export MMPROJ_PATH=/home/exx/.cache/llama.cpp/unsloth_gemma-4-E4B-it-GGUF_mmproj-F16.gguf && "
        )
    elif base_model and "31b" in base_model.lower():
        model_env = (
            "export MODEL_PATH=/home/exx/.cache/llama.cpp/ggml-org_gemma-4-31B-it-GGUF_gemma-4-31B-it-Q4_K_M.gguf && "
            "export MMPROJ_PATH=/home/exx/.cache/llama.cpp/ggml-org_gemma-4-31B-it-GGUF_mmproj-gemma-4-31B-it-Q8_0.gguf && "
        )

    venv_python = "~/CYTu/test_zone/gemma3-bbox-finetune/.venv/bin/python"
    remote_cmd = (
        f"cd ~/CYTu/AionGenos_server && "
        f"{remote_python} server_side/export_lora_gguf.py "
        f"--checkpoint-dir ~/CYTu/AionGenos_server/data/lora_checkpoints/{run_id} "
        f"--output ~/CYTu/AionGenos_server/data/lora_gguf/{run_id}/adapter.gguf "
        f"{base_model_arg}&& "
        f"{venv_python} server_side/patch_gguf.py ~/CYTu/AionGenos_server/data/lora_gguf/{run_id}/adapter.gguf && "
        f"{model_env}bash server_side/reload_student.sh ~/CYTu/AionGenos_server/data/lora_gguf/{run_id}/adapter.gguf"
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
