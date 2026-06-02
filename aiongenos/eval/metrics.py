"""Evaluation metrics — success rate, latency, distillation gap."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from aiongenos.replay.buffer import ReplayBuffer
from aiongenos.replay.schema import EpisodeOutcome

logger = logging.getLogger(__name__)


@dataclass
class LevelMetrics:
    """Metrics for a single curriculum level."""
    level: int
    total_episodes: int
    success_episodes: int
    success_rate: float
    avg_episode_duration_s: float
    avg_vlm_latency_ms: float
    teacher_sr: Optional[float] = None
    student_sr: Optional[float] = None
    latency_ratio: Optional[float] = None  # student_latency / teacher_latency


def compute_level_metrics(
    buffer: ReplayBuffer,
    run_id: str,
    level: int,
) -> LevelMetrics:
    """Compute metrics for a specific level from replay data.

    Args:
        buffer: Replay buffer to read from.
        run_id: Run ID to filter.
        level: Curriculum level.

    Returns:
        LevelMetrics with computed stats.
    """
    episodes = [
        ep for ep in buffer.iterate(run_id=run_id)
        if ep.level == level
    ]

    total = len(episodes)
    successes = sum(1 for ep in episodes if ep.outcome == EpisodeOutcome.SUCCESS)
    sr = successes / total if total > 0 else 0.0

    avg_duration = (
        sum(ep.episode_duration_s for ep in episodes) / total
        if total > 0 else 0.0
    )

    avg_latency = (
        sum(ep.total_vlm_latency_ms for ep in episodes) / total
        if total > 0 else 0.0
    )

    return LevelMetrics(
        level=level,
        total_episodes=total,
        success_episodes=successes,
        success_rate=sr,
        avg_episode_duration_s=avg_duration,
        avg_vlm_latency_ms=avg_latency,
    )


def compute_distillation_gap(
    teacher_sr: float,
    student_sr: float,
    teacher_latency_ms: float,
    student_latency_ms: float,
) -> dict[str, float]:
    """Compute distillation quality metrics.

    Args:
        teacher_sr: Teacher success rate.
        student_sr: Student success rate.
        teacher_latency_ms: Teacher avg latency per step.
        student_latency_ms: Student avg latency per step.

    Returns:
        Dict with gap metrics.
    """
    sr_ratio = student_sr / teacher_sr if teacher_sr > 0 else 0.0
    latency_ratio = student_latency_ms / teacher_latency_ms if teacher_latency_ms > 0 else 0.0

    return {
        "teacher_sr": teacher_sr,
        "student_sr": student_sr,
        "sr_ratio": sr_ratio,  # target ≥ 0.7
        "teacher_latency_ms": teacher_latency_ms,
        "student_latency_ms": student_latency_ms,
        "latency_ratio": latency_ratio,  # target ≤ 0.13 (200ms / 1500ms)
        "speedup_factor": teacher_latency_ms / student_latency_ms if student_latency_ms > 0 else 0.0,
    }
