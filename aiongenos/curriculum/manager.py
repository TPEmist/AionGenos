"""AionGenosCurriculumManager — success-rate gating for level advancement.

Tracks per-level success rates and decides advance/hold/blocked.
Integrates with the replay buffer to compute stats.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from aiongenos.config import (
    AionGenosConfig,
    CurriculumConfig,
    LEVEL_CONFIGS,
    LEVEL_ORDER,
    LevelConfig,
)
from aiongenos.replay.buffer import ReplayBuffer
from aiongenos.replay.schema import EpisodeOutcome

logger = logging.getLogger(__name__)


class LevelStatus(str, Enum):
    LOCKED = "locked"
    ACTIVE = "active"
    PASSED = "passed"
    BLOCKED = "blocked"


@dataclass
class LevelState:
    """Runtime state for a single curriculum level."""
    level: int
    status: LevelStatus = LevelStatus.LOCKED
    success_count: int = 0
    total_count: int = 0
    start_time: Optional[float] = None  # epoch seconds

    @property
    def success_rate(self) -> float:
        if self.total_count == 0:
            return 0.0
        return self.success_count / self.total_count

    @property
    def elapsed_hours(self) -> float:
        if self.start_time is None:
            return 0.0
        return (time.time() - self.start_time) / 3600.0


class AionGenosCurriculumManager:
    """Manages curriculum progression across levels.

    Advance rules (from plan §2.2):
    - Level n reaches success rate ≥ 60% (threshold) → unlock Level n+1.
    - Level n+1 training data = current + all previous level successes (cumulative).
    - 12 hr collector without 100 successes → mark curriculum_blocked, stop loop.
    """

    def __init__(
        self,
        config: CurriculumConfig,
        replay_buffer: ReplayBuffer,
        start_level: int = 0,
        max_level: Optional[int] = None,
    ):
        self.config = config
        self.replay = replay_buffer
        # Source of truth for level traversal is LEVEL_ORDER (V4 added pre-L0
        # sub-stages with negative ids — integer arithmetic on the level field
        # is no longer safe).
        self._order: tuple[int, ...] = LEVEL_ORDER
        if start_level not in self._order:
            raise ValueError(
                f"start_level={start_level} not in LEVEL_ORDER={self._order}"
            )
        self.max_level = self._order[-1] if max_level is None else max_level
        self.current_level = start_level

        # Initialize level states for every level in LEVEL_ORDER.
        self.levels: dict[int, LevelState] = {}
        for lv in self._order:
            status = LevelStatus.ACTIVE if lv == start_level else LevelStatus.LOCKED
            self.levels[lv] = LevelState(
                level=lv,
                status=status,
                start_time=time.time() if lv == start_level else None,
            )

    def get_current_level_config(self) -> LevelConfig:
        """Get the LevelConfig for the current active level."""
        return LEVEL_CONFIGS[self.current_level]

    def record_episode(self, outcome: EpisodeOutcome) -> None:
        """Record an episode outcome for the current level."""
        state = self.levels[self.current_level]
        state.total_count += 1
        if outcome == EpisodeOutcome.SUCCESS:
            state.success_count += 1

    def check_advance(self) -> tuple[bool, str]:
        """Check if current level should advance.

        Returns:
            (should_advance, reason_message)
        """
        state = self.levels[self.current_level]

        # Check blocked condition
        if (
            state.elapsed_hours >= self.config.blocked_timeout_hours
            and state.success_count < self.config.min_success_episodes
        ):
            state.status = LevelStatus.BLOCKED
            msg = (
                f"L{self.current_level} BLOCKED: {state.elapsed_hours:.1f}h elapsed, "
                f"only {state.success_count}/{self.config.min_success_episodes} successes"
            )
            logger.error(msg)
            return False, msg

        # Check advance condition
        if (
            state.success_rate >= self.config.advance_threshold
            and state.total_count >= 10  # minimum sample size
        ):
            cur_idx = self._order.index(self.current_level)
            if cur_idx >= len(self._order) - 1:
                msg = f"L{self.current_level} passed but already at max level"
                return False, msg

            # Advance to the next level in LEVEL_ORDER.
            prev_level = self.current_level
            state.status = LevelStatus.PASSED
            self.current_level = self._order[cur_idx + 1]
            next_state = self.levels[self.current_level]
            next_state.status = LevelStatus.ACTIVE
            next_state.start_time = time.time()

            msg = (
                f"ADVANCE: L{prev_level} → L{self.current_level} "
                f"(SR={state.success_rate:.1%}, n={state.total_count})"
            )
            logger.info(msg)
            return True, msg

        # Hold
        msg = (
            f"HOLD L{self.current_level}: SR={state.success_rate:.1%}, "
            f"n={state.total_count}, elapsed={state.elapsed_hours:.1f}h"
        )
        return False, msg

    def is_blocked(self) -> bool:
        """Check if current level is blocked."""
        return self.levels[self.current_level].status == LevelStatus.BLOCKED

    def get_cumulative_success_levels(self) -> list[int]:
        """Get all levels whose success replays should be used for training.

        Per plan: training data = current level + all passed levels (cumulative).
        """
        result = []
        for lv in range(self.current_level + 1):
            state = self.levels[lv]
            if state.status in (LevelStatus.PASSED, LevelStatus.ACTIVE):
                result.append(lv)
        return result

    def summary(self) -> dict[str, dict]:
        """Return a summary dict of all level states."""
        return {
            f"L{lv}": {
                "status": state.status.value,
                "success_rate": f"{state.success_rate:.1%}",
                "success_count": state.success_count,
                "total_count": state.total_count,
                "elapsed_hours": f"{state.elapsed_hours:.1f}",
            }
            for lv, state in self.levels.items()
        }
