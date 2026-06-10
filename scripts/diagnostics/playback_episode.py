"""Playback inspector for a single collected episode.

Reads the dump produced by ``scripts/run_collect.py --dump_images_root <DIR>``
and prints the round-by-round VLM I/O alongside the on-disk PNG paths so
you can step through ``feh round_NN_pre.png`` (or any image viewer) while
reading the VLM's thought / coordinates / dist evolution.

Usage:
    python3 scripts/diagnostics/playback_episode.py \\
        --dump_root data/collect_dumps \\
        [--run RUN_ID] [--episode EPISODE_ID]

If ``--episode`` is omitted, picks the most recently modified episode in
the run; if ``--run`` is also omitted, picks the latest run.
"""

from __future__ import annotations

import argparse
import json
import logging
import textwrap
from pathlib import Path

logger = logging.getLogger(__name__)


def _latest_dir(parent: Path) -> Path:
    candidates = [p for p in parent.iterdir() if p.is_dir()]
    if not candidates:
        raise RuntimeError(f"No subdirectories under {parent}")
    return max(candidates, key=lambda p: p.stat().st_mtime)


def _format_round(rd: dict, ep_dir: Path) -> str:
    n = rd.get("round")
    pre = ep_dir / f"round_{n:02d}_pre.png"
    post = ep_dir / f"round_{n:02d}_post.png"
    pre_str = str(pre) if pre.exists() else "(missing)"
    post_str = str(post) if post.exists() else "(missing)"

    fl = rd.get("final_dist_l_cm")
    fr = rd.get("final_dist_r_cm")
    dist_str = (
        f"L={fl:.1f}cm R={fr:.1f}cm"
        if fl is not None and fr is not None
        else "L/R=?/?"
    )

    thought = (rd.get("vlm_thought") or "").strip().replace("\n", " ")
    thought_wrapped = textwrap.fill(thought, width=100, initial_indent="    ", subsequent_indent="    ")

    return (
        f"[Round {n:02d}] active={rd.get('active_arm')} "
        f"vlm_stop={rd.get('vlm_stop')} latency={rd.get('stage1_latency_ms', 0)/1000:.1f}s\n"
        f"  pred_int   L={rd.get('vlm_left_pos_int')} R={rd.get('vlm_right_pos_int')}\n"
        f"  cmd_metric L={[round(v, 3) for v in rd.get('command_left_pos_m') or []]} "
        f"R={[round(v, 3) for v in rd.get('command_right_pos_m') or []]}\n"
        f"  ee_start   L={rd.get('actual_left_start')} R={rd.get('actual_right_start')}\n"
        f"  end_dist   {dist_str}  attempt_outcome={rd.get('attempt_outcome')}\n"
        f"  pre_png    {pre_str}\n"
        f"  post_png   {post_str}\n"
        f"  thought:\n{thought_wrapped}"
    )


def main() -> None:
    """CLI entry."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dump_root", type=Path, required=True)
    parser.add_argument("--run", type=str, default=None)
    parser.add_argument("--episode", type=str, default=None)
    args = parser.parse_args()

    if args.run:
        run_dir = args.dump_root / args.run
    else:
        run_dir = _latest_dir(args.dump_root)
    if args.episode:
        ep_dir = run_dir / args.episode
    else:
        ep_dir = _latest_dir(run_dir)

    meta_path = ep_dir / "meta.json"
    if not meta_path.exists():
        raise RuntimeError(f"meta.json not found under {ep_dir}")

    meta = json.loads(meta_path.read_text())

    logger.info("=" * 80)
    logger.info(f"Run     : {meta.get('run_id')}")
    logger.info(f"Episode : {meta.get('episode_id')}")
    logger.info(f"Level   : L{meta.get('level')}  ({meta.get('level_name')})")
    logger.info(f"Outcome : {meta.get('outcome')}  flags={meta.get('flags')}")
    start_png = ep_dir / "episode_start.png"
    end_png = ep_dir / "episode_end.png"
    logger.info(f"Start PNG: {start_png if start_png.exists() else '(missing)'}")
    logger.info(f"End   PNG: {end_png if end_png.exists() else '(missing)'}")
    logger.info("=" * 80)
    logger.info("")

    for rd in meta.get("rounds", []):
        logger.info(_format_round(rd, ep_dir))
        logger.info("")


if __name__ == "__main__":
    main()
