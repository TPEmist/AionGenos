"""Quick sanity check: how diverse is the initial EE pose across episodes?

Useful for verifying T-8a (reset_joints_by_offset). If the std of init EE
position across episodes is small (< 3 grid units ≈ 1.2 cm), the randomization
is structurally broken (see F15) and we should fall back to Plan B (IK-based
task-space randomization).

Usage:
    python3 scripts/diagnostics/check_ee_randomness.py [--run RUN_ID]
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)


def collect_initial_ee(run_dir: Path) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Gather (L_init_xyz, R_init_xyz, episode_ids) over a run."""
    L: list[tuple[int, int, int]] = []
    R: list[tuple[int, int, int]] = []
    ids: list[str] = []
    for sub in ("success", "failure"):
        for f in sorted((run_dir / sub).glob("*.json")):
            data = json.loads(f.read_text())
            traj = data.get("trajectory", [])
            if not traj:
                continue
            t0 = traj[0]
            L.append(tuple(t0.get("left_ee_pos") or (0, 0, 0)))
            R.append(tuple(t0.get("right_ee_pos") or (0, 0, 0)))
            ids.append(data.get("episode_id", f.stem)[:12])
    return np.asarray(L), np.asarray(R), ids


def main() -> None:
    """CLI entry."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replay_root", type=Path, default=Path("data/replays"))
    parser.add_argument("--run", type=str, required=True)
    parser.add_argument("--passing_std_grid", type=float, default=3.0,
                        help="If std (per axis) >= this many grid units, randomization is healthy.")
    args = parser.parse_args()

    run_dir = args.replay_root / args.run
    L, R, ids = collect_initial_ee(run_dir)
    if len(L) < 2:
        logger.info(f"Only {len(L)} episode(s) in {run_dir} — need ≥2 to assess randomness.")
        return

    L_std = L.std(axis=0)
    R_std = R.std(axis=0)
    L_range = L.max(axis=0) - L.min(axis=0)
    R_range = R.max(axis=0) - R.min(axis=0)

    logger.info(f"Run {args.run}: {len(L)} episodes")
    logger.info(f"  Left  EE init mean = {L.mean(axis=0)}  std = {L_std}  range = {L_range}")
    logger.info(f"  Right EE init mean = {R.mean(axis=0)}  std = {R_std}  range = {R_range}")
    healthy = bool(L_std.min() >= args.passing_std_grid and R_std.min() >= args.passing_std_grid)
    logger.info(
        f"  Verdict: {'HEALTHY ✓' if healthy else 'STRUCTURALLY-BROKEN ✗ (use Plan B IK reset)'}"
    )
    logger.info("")
    logger.info("Per-episode initial EE:")
    for eid, l, r in zip(ids, L, R):
        logger.info(f"  {eid:<14} L={tuple(l)}  R={tuple(r)}")


if __name__ == "__main__":
    main()
