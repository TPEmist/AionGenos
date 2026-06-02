"""Rsync wrapper for replay buffer synchronization to remote server."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def sync_replays_to_remote(
    local_path: str | Path,
    remote_host: str,
    remote_user: str,
    remote_path: str,
    ssh_key: str | None = None,
) -> bool:
    """Rsync local replay directory to remote server.

    Args:
        local_path: Local replay base directory.
        remote_host: Remote server hostname/IP.
        remote_user: SSH username.
        remote_path: Remote replay directory path.
        ssh_key: Optional SSH key path.

    Returns:
        True if sync succeeded.
    """
    local_path = Path(local_path)
    if not local_path.exists():
        logger.warning(f"Local replay path does not exist: {local_path}")
        return False

    ssh_cmd = "ssh"
    if ssh_key:
        ssh_cmd = f"ssh -i {ssh_key}"

    cmd = [
        "rsync", "-avz", "--progress",
        "-e", ssh_cmd,
        f"{local_path}/",
        f"{remote_user}@{remote_host}:{remote_path}/",
    ]

    logger.info(f"Syncing replays: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,  # 10 min timeout
        )
        if result.returncode == 0:
            logger.info("Replay sync completed successfully")
            return True
        else:
            logger.error(f"Replay sync failed: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        logger.error("Replay sync timed out after 600s")
        return False
    except Exception as e:
        logger.error(f"Replay sync error: {e}")
        return False
