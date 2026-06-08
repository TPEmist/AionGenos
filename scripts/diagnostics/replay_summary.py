"""Round-by-round convergence summary for AionGenos replay episodes.

Reads ``data/replays/{run_id}/{success,failure}/*.json`` and prints, per
episode, the per-round distance trajectory (start → end), VLM prediction,
plateau triggers, and aggregate run statistics.

Usage:
    python3 scripts/diagnostics/replay_summary.py [--run RUN_ID] [--steps_per_round N]

If ``--run`` is omitted the latest run by mtime is selected. Default
``--steps_per_round`` matches ``LevelConfig.sim_steps_per_subgoal=60``.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from dataclasses import dataclass
from glob import glob
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RoundStat:
    """Distance / prediction snapshot for one VLM round within an episode."""

    round_idx: int
    pred_left: tuple[int, int, int]
    pred_right: tuple[int, int, int]
    dist_l_start_cm: float
    dist_r_start_cm: float
    dist_l_end_cm: float
    dist_r_end_cm: float
    delta_l_cm: float
    delta_r_cm: float
    latency_ms: float


@dataclass(frozen=True)
class EpisodeStat:
    """Episode-level summary."""

    episode_id: str
    outcome: str
    flags: tuple[str, ...]
    rounds: tuple[RoundStat, ...]
    duration_s: float
    total_vlm_latency_ms: float
    final_dist_l_cm: float
    final_dist_r_cm: float
    best_combined_cm: float


def _round_distances(
    trajectory: list[dict[str, Any]],
    round_idx: int,
    steps_per_round: int,
) -> tuple[float, float, float, float]:
    """Return (l_start_cm, r_start_cm, l_end_cm, r_end_cm) for a single round."""
    start_step = round_idx * steps_per_round
    end_step = min((round_idx + 1) * steps_per_round - 1, len(trajectory) - 1)
    if start_step >= len(trajectory):
        return float("nan"), float("nan"), float("nan"), float("nan")
    start_d = trajectory[start_step].get("distances") or {}
    end_d = trajectory[end_step].get("distances") or {}
    return (
        start_d.get("dist_red", float("nan")) * 100,
        start_d.get("dist_blue", float("nan")) * 100,
        end_d.get("dist_red", float("nan")) * 100,
        end_d.get("dist_blue", float("nan")) * 100,
    )


def summarize_episode(path: Path, steps_per_round: int) -> EpisodeStat:
    """Load one replay JSON and produce an EpisodeStat."""
    data = json.loads(path.read_text())
    trajectory = data.get("trajectory", [])
    interactions = data.get("vlm_interactions", [])

    rounds: list[RoundStat] = []
    best_combined = float("inf")
    for i, inter in enumerate(interactions):
        l_s, r_s, l_e, r_e = _round_distances(trajectory, i, steps_per_round)
        rounds.append(
            RoundStat(
                round_idx=i + 1,
                pred_left=tuple(inter.get("parsed_left_pos") or (0, 0, 0)),
                pred_right=tuple(inter.get("parsed_right_pos") or (0, 0, 0)),
                dist_l_start_cm=l_s,
                dist_r_start_cm=r_s,
                dist_l_end_cm=l_e,
                dist_r_end_cm=r_e,
                delta_l_cm=l_e - l_s,
                delta_r_cm=r_e - r_s,
                latency_ms=inter.get("latency_ms", 0.0),
            )
        )
        combined = l_e + r_e
        if combined == combined and combined < best_combined:  # NaN-safe
            best_combined = combined

    last = trajectory[-1]["distances"] if trajectory else {}
    # total_vlm_latency_ms in the replay schema is process-cumulative (collector
    # never resets it across episodes). For per-episode stats, sum the per-round
    # latency_ms instead, which is the truthful per-call time.
    total_latency_ms = sum(r.latency_ms for r in rounds)
    return EpisodeStat(
        episode_id=data.get("episode_id", path.stem),
        outcome=data.get("outcome", "unknown"),
        flags=tuple(data.get("flags") or ()),
        rounds=tuple(rounds),
        duration_s=data.get("episode_duration_s", 0.0),
        total_vlm_latency_ms=total_latency_ms,
        final_dist_l_cm=last.get("dist_red", float("nan")) * 100,
        final_dist_r_cm=last.get("dist_blue", float("nan")) * 100,
        best_combined_cm=best_combined,
    )


def _latest_run(replay_root: Path) -> str:
    """Pick the run with the most recently modified replay file."""
    candidates = sorted(
        (p for p in replay_root.iterdir() if p.is_dir()),
        key=lambda p: max(
            (f.stat().st_mtime for f in p.rglob("*.json")), default=p.stat().st_mtime
        ),
        reverse=True,
    )
    if not candidates:
        raise RuntimeError(f"No runs found under {replay_root}")
    return candidates[0].name


def _gather(run_dir: Path, steps_per_round: int) -> list[EpisodeStat]:
    files = sorted(
        glob(str(run_dir / "success" / "*.json")) + glob(str(run_dir / "failure" / "*.json")),
        key=os.path.getmtime,
    )
    return [summarize_episode(Path(f), steps_per_round) for f in files]


def _format_episode(ep: EpisodeStat) -> str:
    """Render one episode block."""
    lines = [
        f"Episode {ep.episode_id}  outcome={ep.outcome}  flags={list(ep.flags)}  rounds={len(ep.rounds)}",
        f"  duration={ep.duration_s:.0f}s  vlm_total_latency={ep.total_vlm_latency_ms / 1000:.0f}s  "
        f"avg/call={ep.total_vlm_latency_ms / max(1, len(ep.rounds)) / 1000:.1f}s",
        f"  best_combined={ep.best_combined_cm:.1f} cm  final L/R={ep.final_dist_l_cm:.1f}/{ep.final_dist_r_cm:.1f} cm",
        "    R   pred L         pred R         L  start→end (Δ)        R  start→end (Δ)        latency",
    ]
    for r in ep.rounds:
        lines.append(
            f"   {r.round_idx:>2}  {str(r.pred_left):<14} {str(r.pred_right):<14}  "
            f"{r.dist_l_start_cm:>5.1f}→{r.dist_l_end_cm:>5.1f} ({r.delta_l_cm:+5.1f})   "
            f"{r.dist_r_start_cm:>5.1f}→{r.dist_r_end_cm:>5.1f} ({r.delta_r_cm:+5.1f})   "
            f"{r.latency_ms / 1000:>4.1f}s"
        )
    return "\n".join(lines)


def _aggregate(eps: list[EpisodeStat]) -> str:
    if not eps:
        return "(no episodes)"
    n = len(eps)
    succ = sum(1 for e in eps if e.outcome == "success")
    avg_rounds = sum(len(e.rounds) for e in eps) / n
    avg_best = sum(e.best_combined_cm for e in eps if e.best_combined_cm != float("inf")) / max(
        1, sum(1 for e in eps if e.best_combined_cm != float("inf"))
    )
    avg_final_l = sum(e.final_dist_l_cm for e in eps if e.final_dist_l_cm == e.final_dist_l_cm) / n
    avg_final_r = sum(e.final_dist_r_cm for e in eps if e.final_dist_r_cm == e.final_dist_r_cm) / n
    outcome_counts: dict[str, int] = {}
    flag_counts: dict[str, int] = {}
    for e in eps:
        outcome_counts[e.outcome] = outcome_counts.get(e.outcome, 0) + 1
        for f in e.flags:
            flag_counts[f] = flag_counts.get(f, 0) + 1

    plateau_only_episodes = [e for e in eps if "plateau" in e.flags]
    plateau_premature = 0
    for e in plateau_only_episodes:
        # "Premature" heuristic: best_combined dropped meaningfully in the
        # last 3 rounds before plateau triggered (i.e. progress was happening
        # but plateau patience cut it short).
        last3 = e.rounds[-3:]
        if len(last3) < 3:
            continue
        deltas = [r.delta_l_cm + r.delta_r_cm for r in last3]
        if min(deltas) < -2:  # at least one round still made >2cm combined progress
            plateau_premature += 1

    return "\n".join(
        [
            f"Episodes: {n}  Success: {succ}/{n} ({succ / n:.1%})  Avg rounds: {avg_rounds:.1f}",
            f"Avg best_combined: {avg_best:.1f} cm  Avg final L/R: {avg_final_l:.1f}/{avg_final_r:.1f} cm",
            f"Outcome distribution: {outcome_counts}",
            f"Flag distribution: {flag_counts}",
            f"Plateau-flagged episodes that still showed progress in last 3 rounds: "
            f"{plateau_premature}/{len(plateau_only_episodes)}  "
            f"(suggests plateau_patience={plateau_only_episodes[0].rounds[-1].round_idx if plateau_only_episodes else 'n/a'} "
            f"may be cutting too early)",
        ]
    )


def main() -> None:
    """CLI entry."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replay_root", type=Path, default=Path("data/replays"))
    parser.add_argument("--run", type=str, default=None, help="Run id (default: latest)")
    parser.add_argument("--steps_per_round", type=int, default=60)
    parser.add_argument("--episodes_only", action="store_true", help="Suppress per-round detail")
    args = parser.parse_args()

    run_id = args.run or _latest_run(args.replay_root)
    run_dir = args.replay_root / run_id
    eps = _gather(run_dir, args.steps_per_round)

    logger.info(f"=== Run: {run_id} ({run_dir}) ===")
    logger.info(_aggregate(eps))
    logger.info("")
    if not args.episodes_only:
        for e in eps:
            logger.info(_format_episode(e))
            logger.info("")


if __name__ == "__main__":
    main()
