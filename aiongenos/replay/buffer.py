"""Replay buffer — atomic write + iterator for replay episodes."""

from __future__ import annotations

import json
import logging
import os
import tempfile
import uuid
from pathlib import Path
from typing import Iterator, Optional

from aiongenos.replay.schema import EpisodeOutcome, ReplayEpisode

logger = logging.getLogger(__name__)


class ReplayBuffer:
    """File-backed replay buffer with atomic writes.

    Directory structure:
        {base_path}/{run_id}/success/{episode_id}.json
        {base_path}/{run_id}/failure/{episode_id}.json
    """

    def __init__(self, base_path: str | Path):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _episode_dir(self, run_id: str, outcome: EpisodeOutcome) -> Path:
        if outcome == EpisodeOutcome.SUCCESS:
            subdir = "success"
        else:
            subdir = "failure"
        d = self.base_path / run_id / subdir
        d.mkdir(parents=True, exist_ok=True)
        return d

    def write(self, episode: ReplayEpisode) -> Path:
        """Atomically write an episode to disk.

        Uses write-to-temp + rename for atomicity.

        Returns:
            Path to the written file.
        """
        target_dir = self._episode_dir(episode.run_id, episode.outcome)
        target_path = target_dir / f"{episode.episode_id}.json"

        # Atomic write: write to temp file then rename
        fd, tmp_path = tempfile.mkstemp(
            dir=str(target_dir), suffix=".json.tmp"
        )
        try:
            with os.fdopen(fd, "w") as f:
                f.write(episode.model_dump_json(indent=2))
            os.rename(tmp_path, str(target_path))
        except Exception:
            # Clean up temp file on failure
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise

        logger.info(f"Wrote replay: {target_path}")
        return target_path

    def read(self, path: str | Path) -> ReplayEpisode:
        """Read a replay episode from disk."""
        with open(path, "r") as f:
            data = json.load(f)
        return ReplayEpisode(**data)

    def iterate(
        self,
        run_id: Optional[str] = None,
        outcome_filter: Optional[EpisodeOutcome] = None,
    ) -> Iterator[ReplayEpisode]:
        """Iterate over stored episodes.

        Args:
            run_id: Filter to specific run. None = all runs.
            outcome_filter: Filter to success/failure. None = all.

        Yields:
            ReplayEpisode objects.
        """
        if run_id:
            run_dir = self.base_path / run_id
            run_dirs = [run_dir] if run_dir.exists() else []
        else:
            run_dirs = [d for d in self.base_path.iterdir() if d.is_dir()] if self.base_path.exists() else []

        for run_dir in run_dirs:
            subdirs = []
            if outcome_filter is None:
                subdirs = [d for d in run_dir.iterdir() if d.is_dir()]
            elif outcome_filter == EpisodeOutcome.SUCCESS:
                s = run_dir / "success"
                if s.exists():
                    subdirs = [s]
            else:
                f = run_dir / "failure"
                if f.exists():
                    subdirs = [f]

            for subdir in subdirs:
                for ep_file in sorted(subdir.glob("*.json")):
                    try:
                        yield self.read(ep_file)
                    except Exception as e:
                        logger.warning(f"Failed to read {ep_file}: {e}")

    def count(
        self,
        run_id: Optional[str] = None,
        outcome_filter: Optional[EpisodeOutcome] = None,
    ) -> int:
        """Count episodes matching filters."""
        return sum(1 for _ in self.iterate(run_id, outcome_filter))

    def success_rate(self, run_id: str) -> float:
        """Compute success rate for a run."""
        total = self.count(run_id)
        if total == 0:
            return 0.0
        success = self.count(run_id, EpisodeOutcome.SUCCESS)
        return success / total

    @staticmethod
    def new_episode_id() -> str:
        """Generate a new unique episode ID."""
        return str(uuid.uuid4())[:12]

    @staticmethod
    def new_run_id() -> str:
        """Generate a new unique run ID."""
        return str(uuid.uuid4())[:8]
