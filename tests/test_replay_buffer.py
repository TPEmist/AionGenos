"""Tests for replay buffer — write, read, iterate, success rate."""

import json
import tempfile
from pathlib import Path

import pytest

from aiongenos.replay.buffer import ReplayBuffer
from aiongenos.replay.schema import EpisodeOutcome, ReplayEpisode, TimeStep


@pytest.fixture
def tmp_replay_dir(tmp_path):
    return tmp_path / "replays"


@pytest.fixture
def buffer(tmp_replay_dir):
    return ReplayBuffer(tmp_replay_dir)


def _make_episode(
    run_id: str = "test_run",
    outcome: EpisodeOutcome = EpisodeOutcome.SUCCESS,
    episode_id: str | None = None,
) -> ReplayEpisode:
    return ReplayEpisode(
        episode_id=episode_id or ReplayBuffer.new_episode_id(),
        run_id=run_id,
        level=0,
        task_name="L0_reach_two_cubes",
        instruction="Reach the targets",
        outcome=outcome,
        trajectory=[
            TimeStep(
                t=0.0,
                left_ee_pos=(0, 0, 50),
                right_ee_pos=(0, 0, 50),
            ),
            TimeStep(
                t=1.0,
                left_ee_pos=(30, -20, 50),
                right_ee_pos=(-10, 40, 60),
            ),
        ],
        episode_duration_s=2.0,
    )


class TestReplayBuffer:
    def test_write_and_read(self, buffer):
        ep = _make_episode()
        path = buffer.write(ep)
        assert path.exists()

        loaded = buffer.read(path)
        assert loaded.episode_id == ep.episode_id
        assert loaded.outcome == EpisodeOutcome.SUCCESS
        assert len(loaded.trajectory) == 2

    def test_directory_structure(self, buffer):
        ep_success = _make_episode(outcome=EpisodeOutcome.SUCCESS)
        ep_fail = _make_episode(outcome=EpisodeOutcome.TIMEOUT)

        path_s = buffer.write(ep_success)
        path_f = buffer.write(ep_fail)

        assert "success" in str(path_s)
        assert "failure" in str(path_f)

    def test_iterate_all(self, buffer):
        for i in range(3):
            buffer.write(_make_episode(episode_id=f"ep_{i}"))
        buffer.write(_make_episode(outcome=EpisodeOutcome.TIMEOUT, episode_id="ep_fail"))

        episodes = list(buffer.iterate(run_id="test_run"))
        assert len(episodes) == 4

    def test_iterate_filter(self, buffer):
        for i in range(3):
            buffer.write(_make_episode(episode_id=f"ep_s{i}"))
        buffer.write(_make_episode(outcome=EpisodeOutcome.TIMEOUT, episode_id="ep_f"))

        successes = list(buffer.iterate(run_id="test_run", outcome_filter=EpisodeOutcome.SUCCESS))
        assert len(successes) == 3

    def test_count(self, buffer):
        for i in range(5):
            outcome = EpisodeOutcome.SUCCESS if i < 3 else EpisodeOutcome.TIMEOUT
            buffer.write(_make_episode(outcome=outcome, episode_id=f"ep_{i}"))

        assert buffer.count("test_run") == 5
        assert buffer.count("test_run", EpisodeOutcome.SUCCESS) == 3

    def test_success_rate(self, buffer):
        for i in range(10):
            outcome = EpisodeOutcome.SUCCESS if i < 6 else EpisodeOutcome.TIMEOUT
            buffer.write(_make_episode(outcome=outcome, episode_id=f"ep_{i}"))

        rate = buffer.success_rate("test_run")
        assert abs(rate - 0.6) < 1e-9

    def test_empty_success_rate(self, buffer):
        assert buffer.success_rate("nonexistent") == 0.0

    def test_atomic_write(self, buffer):
        """No .tmp files should remain after successful write."""
        ep = _make_episode()
        buffer.write(ep)

        # Check no temp files
        for f in buffer.base_path.rglob("*.tmp"):
            pytest.fail(f"Temp file found: {f}")

    def test_schema_version(self, buffer):
        ep = _make_episode()
        path = buffer.write(ep)

        with open(path) as f:
            data = json.load(f)
        assert data["schema_version"] == 1
