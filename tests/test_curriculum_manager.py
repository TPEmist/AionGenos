"""Tests for AionGenosCurriculumManager — advance gating + cumulative replay."""

import time

import pytest

from aiongenos.config import CurriculumConfig
from aiongenos.curriculum.manager import (
    AionGenosCurriculumManager,
    LevelStatus,
)
from aiongenos.replay.buffer import ReplayBuffer
from aiongenos.replay.schema import EpisodeOutcome


@pytest.fixture
def tmp_buffer(tmp_path):
    return ReplayBuffer(tmp_path / "replays")


@pytest.fixture
def manager(tmp_buffer):
    config = CurriculumConfig(
        advance_threshold=0.6,
        blocked_timeout_hours=0.001,  # very short for testing
        min_success_episodes=5,
    )
    return AionGenosCurriculumManager(
        config=config,
        replay_buffer=tmp_buffer,
        start_level=0,
        max_level=4,
    )


class TestCurriculumManager:
    def test_initial_state(self, manager):
        assert manager.current_level == 0
        assert manager.levels[0].status == LevelStatus.ACTIVE
        assert manager.levels[1].status == LevelStatus.LOCKED

    def test_hold_below_threshold(self, manager):
        """Should hold when success rate is below threshold."""
        for _ in range(5):
            manager.record_episode(EpisodeOutcome.SUCCESS)
        for _ in range(10):
            manager.record_episode(EpisodeOutcome.TIMEOUT)

        advanced, msg = manager.check_advance()
        assert not advanced
        assert "HOLD" in msg

    def test_advance_above_threshold(self, manager):
        """Should advance when success rate ≥ 60% with enough samples."""
        for _ in range(7):
            manager.record_episode(EpisodeOutcome.SUCCESS)
        for _ in range(3):
            manager.record_episode(EpisodeOutcome.TIMEOUT)

        advanced, msg = manager.check_advance()
        assert advanced
        assert "ADVANCE" in msg
        assert manager.current_level == 1
        assert manager.levels[0].status == LevelStatus.PASSED
        assert manager.levels[1].status == LevelStatus.ACTIVE

    def test_blocked_detection(self, manager):
        """Should mark blocked after timeout with insufficient successes."""
        # Record only failures (below min_success_episodes=5)
        for _ in range(3):
            manager.record_episode(EpisodeOutcome.SUCCESS)
        for _ in range(10):
            manager.record_episode(EpisodeOutcome.TIMEOUT)

        # Simulate elapsed time by backdating start_time
        manager.levels[0].start_time = time.time() - 3600  # 1 hour ago

        _, msg = manager.check_advance()
        assert manager.is_blocked()
        assert "BLOCKED" in msg

    def test_cumulative_levels(self, manager):
        """After advancing, cumulative levels should include all passed + active."""
        # Advance L0 → L1
        for _ in range(10):
            manager.record_episode(EpisodeOutcome.SUCCESS)
        manager.check_advance()

        cumulative = manager.get_cumulative_success_levels()
        assert 0 in cumulative
        assert 1 in cumulative

    def test_max_level_boundary(self, manager):
        """Should not advance past max level."""
        # Force to max level
        manager.current_level = 4
        manager.levels[4].status = LevelStatus.ACTIVE
        manager.levels[4].start_time = time.time()

        for _ in range(10):
            manager.record_episode(EpisodeOutcome.SUCCESS)

        advanced, msg = manager.check_advance()
        assert not advanced
        assert "max level" in msg

    def test_summary(self, manager):
        for _ in range(5):
            manager.record_episode(EpisodeOutcome.SUCCESS)

        summary = manager.summary()
        assert "L0" in summary
        assert summary["L0"]["success_count"] == 5

    def test_get_current_level_config(self, manager):
        cfg = manager.get_current_level_config()
        assert cfg.level == 0
        assert cfg.name == "L0_reach_two_cubes"
