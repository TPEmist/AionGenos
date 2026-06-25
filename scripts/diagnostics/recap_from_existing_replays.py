"""Backfill recaps from existing D6 (or any prior-run) replay episodes.

Usage:
    python3 scripts/diagnostics/recap_from_existing_replays.py \
        --run_id 67685984 \
        --teacher_url http://10.80.9.148:18888 \
        --buffer_root workspace/recaps \
        [--limit 5]                # cap for smoke testing
        [--include_failures]       # also process failure/*.json
        [--device cpu]

Produces ``workspace/recaps/{run_id}/{ep_id}.json`` for each replay episode
by replaying its trajectory data + per-round PNGs through ``generate_recap``.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run_id", required=True)
    parser.add_argument("--teacher_url", required=True)
    parser.add_argument("--replay_root", default="data/replays")
    parser.add_argument("--dump_root", default="data/collect_dumps")
    parser.add_argument("--buffer_root", default="workspace/recaps")
    parser.add_argument("--include_failures", action="store_true",
                        help="Also process failure/*.json (default: success only).")
    parser.add_argument("--limit", type=int, default=None,
                        help="Stop after N total recaps (smoke test).")
    parser.add_argument("--device", default="cpu", help="ImageEmbedder device.")
    parser.add_argument("--max_words", type=int, default=100)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s - %(levelname)s - %(message)s")

    # Lazy import so torchvision is only loaded when actually needed.
    sys.path.insert(0, ".")
    from aiongenos.memory.recap_buffer import RecapBuffer
    from aiongenos.pipeline.stage4_recap import (
        _RoundInfo, generate_recap,
    )

    buffer = RecapBuffer(root=args.buffer_root)
    buffer.load()
    existing = {(r.run_id, r.ep_id) for r in buffer.all()}
    logger.info(f"Existing recaps: {len(existing)} in buffer")

    replay_dir = Path(args.replay_root) / args.run_id
    dump_root = Path(args.dump_root)

    candidates: list[tuple[Path, bool]] = []
    succ_dir = replay_dir / "success"
    if succ_dir.exists():
        candidates.extend((p, True) for p in sorted(succ_dir.glob("*.json")))
    if args.include_failures:
        fail_dir = replay_dir / "failure"
        if fail_dir.exists():
            candidates.extend((p, False) for p in sorted(fail_dir.glob("*.json")))

    logger.info(f"Found {len(candidates)} replay file(s) (succ_only={not args.include_failures})")

    processed = 0
    for replay_path, _is_success in candidates:
        if args.limit is not None and processed >= args.limit:
            logger.info(f"Hit --limit={args.limit}, stop.")
            break

        try:
            replay = json.loads(replay_path.read_text())
        except json.JSONDecodeError as e:
            logger.warning(f"  skip {replay_path}: bad JSON ({e})")
            continue

        ep_id = replay["episode_id"]
        if (args.run_id, ep_id) in existing:
            logger.info(f"  skip {ep_id}: already in buffer")
            continue

        outcome = replay.get("outcome", "unknown")
        instruction = replay.get("instruction", "")
        task_name = replay.get("task_name", "")
        active_arm = _active_arm_from_task(task_name)

        traj = replay.get("trajectory", [])
        if not traj:
            logger.warning(f"  skip {ep_id}: empty trajectory")
            continue

        init_ts = traj[0]
        final_ts = traj[-1]
        init_L = tuple(init_ts.get("left_ee_pos") or (0, 0, 0))
        final_L = tuple(final_ts.get("left_ee_pos") or (0, 0, 0))
        init_R = tuple(init_ts.get("right_ee_pos") or ())
        final_R = tuple(final_ts.get("right_ee_pos") or ())

        # Per-round meta from dump_root if available
        ep_dump_dir = dump_root / args.run_id / ep_id
        meta_path = ep_dump_dir / "meta.json"
        round_meta: list[dict] = []
        if meta_path.exists():
            try:
                round_meta = json.loads(meta_path.read_text()).get("rounds", [])
            except json.JSONDecodeError:
                pass

        # Build _RoundInfo list from replay + dump meta
        stage1s = [i for i in replay.get("vlm_interactions", []) if i.get("stage") == "stage1"]
        rounds: list[_RoundInfo] = []
        n = min(len(stage1s), len(round_meta)) if round_meta else len(stage1s)
        if n == 0:
            logger.warning(f"  skip {ep_id}: no stage1 interactions")
            continue
        for i in range(n):
            s1 = stage1s[i]
            meta_r = round_meta[i] if i < len(round_meta) else {}
            if active_arm == "right":
                dist = meta_r.get("final_dist_r_cm")
            else:
                dist = meta_r.get("final_dist_l_cm")
            pre_png = ep_dump_dir / f"round_{i + 1:02d}_pre.png"
            rounds.append(_RoundInfo(
                round_idx=i + 1,
                pre_png=pre_png if pre_png.exists() else None,
                final_dist_cm=float(dist) if dist is not None else float("nan"),
                parsed_left_pos=list(s1.get("parsed_left_pos") or []) or None,
            ))

        # Initial-frame image bytes (replay schema stores a path; we already
        # rely on dump_dir's round_01_pre.png inside generate_recap, so we
        # do not need to load init bytes here unless dump dir is missing).

        rec = generate_recap(
            ep_id=ep_id,
            run_id=args.run_id,
            outcome=outcome,
            active_arm=active_arm,
            instruction=instruction,
            init_L_EE=init_L,
            final_L_EE=final_L,
            init_R_EE=init_R if init_R else None,
            final_R_EE=final_R if final_R else None,
            rounds=rounds,
            ep_dump_dir=ep_dump_dir if ep_dump_dir.exists() else None,
            rgb_start_bytes=None,
            rgb_end_bytes=None,
            teacher_url=args.teacher_url,
            buffer=buffer,
            embedder_device=args.device,
            max_words=args.max_words,
        )
        if rec is not None:
            processed += 1
            logger.info(f"  [{processed}] {ep_id}: outcome={outcome} lesson={rec.text_lesson[:80]!r}…")
        else:
            logger.warning(f"  [skip] {ep_id}: generate_recap returned None")

    logger.info("")
    logger.info(f"Done. New recaps: {processed}. Buffer stats:")
    for k, v in buffer.stats().items():
        logger.info(f"  {k}: {v}")


def _active_arm_from_task(task_name: str) -> Optional[str]:
    if task_name.endswith("_left"):
        return "left"
    if task_name.endswith("_right"):
        return "right"
    return None


if __name__ == "__main__":
    main()
