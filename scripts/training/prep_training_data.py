"""Prepare per-round JSONL training set from success replays + collect_dumps.

Each output JSONL line is one (round_pre_image, state, action) sample —
geometrically consistent so a behavior-cloning LoRA can learn
'state X → next action' without the cross-time mismatch v3.1 hit
(v3.1 paired episode_start.png with R_final's coord; that pair was
~25 cm apart and the LoRA learned to over-shoot from home pose).

Sources:
  data/replays/{run_id}/success/*.json     — replay schema (truth)
  data/collect_dumps/{run_id}/{ep_id}/     — per-round PNGs + meta.json

For each success episode, every round emits one sample:
  {
    "image_path"        : "data/collect_dumps/<run>/<ep>/round_NN_pre.png",
    "level"             : -2,
    "task_instruction"  : "<from replay>",
    "active_arm"        : "left" | "right" | null,
    "state"             : {"left_ee": [...], "right_ee": [...], ...},
    "critic_feedback"   : str | null,
    "target_response"   : "<vlm_full_response from that round>",
    "parsed_left_pos"   : [x,y,z],   # convenience, easier filtering
    "parsed_right_pos"  : [x,y,z],
    "final_dist_l_cm"   : float,
    "final_dist_r_cm"   : float,
    "ep_id"             : str,
    "run_id"            : str,
    "round_idx"         : int,
    "round_count_in_ep" : int,
  }

Filters supported via CLI:
  --min_round                  drop early-exploration samples (e.g. 5 keeps R5+)
  --max_active_dist_cm         drop samples where active arm is > this cm from target
  --skip_first_round           shorthand for --min_round 2
  --only_progress_round        keep only rounds where end_dist decreased vs round start

Stats printed at end: total samples, per-round histogram, dist histogram.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import Counter
from pathlib import Path

logger = logging.getLogger(__name__)


def _resolve_active_arm(level_name: str) -> str | None:
    """Mirror IsaacLabEnvInterface._active_arm_for_level."""
    if level_name.endswith("_left"):
        return "left"
    if level_name.endswith("_right"):
        return "right"
    return None


def _round_pre_png(dump_root: Path, run_id: str, ep_id: str, round_idx: int) -> Path | None:
    """Return path if round_NN_pre.png exists for this episode."""
    p = dump_root / run_id / ep_id / f"round_{round_idx:02d}_pre.png"
    return p if p.exists() else None


def _state_at_round(replay: dict, meta_round: dict, round_idx: int, sim_steps_per_round: int) -> dict:
    """Reconstruct state dict at start of this round.

    Two sources:
      - meta.json rounds[i]['actual_left_start'] / 'actual_right_start' — already
        integer grid coords at round start (preferred).
      - replay.trajectory[(round_idx-1)*sim_steps] as fallback.
    """
    state = {}
    if meta_round.get("actual_left_start"):
        state["left_ee"] = list(meta_round["actual_left_start"])
    if meta_round.get("actual_right_start"):
        state["right_ee"] = list(meta_round["actual_right_start"])

    # Trajectory fallback
    if not state.get("left_ee"):
        traj = replay.get("trajectory", [])
        start_step = (round_idx - 1) * sim_steps_per_round
        if 0 <= start_step < len(traj):
            ts = traj[start_step]
            state["left_ee"] = list(ts.get("left_ee_pos") or [])
            state["right_ee"] = list(ts.get("right_ee_pos") or [])
            state["distances"] = ts.get("distances") or {}
    return state


def build_samples(
    replay_root: Path,
    dump_root: Path,
    run_ids: list[str],
    sim_steps_per_round: int,
    min_round: int = 1,
    max_active_dist_cm: float | None = None,
    only_progress_round: bool = False,
) -> list[dict]:
    """Build per-round samples from success replays of the given runs."""
    samples: list[dict] = []
    skipped = Counter()

    for run_id in run_ids:
        succ_dir = replay_root / run_id / "success"
        if not succ_dir.exists():
            logger.warning(f"  {run_id}: no success/ dir, skip")
            continue

        for replay_path in sorted(succ_dir.glob("*.json")):
            ep_id = replay_path.stem
            replay = json.loads(replay_path.read_text())
            ep_dump_dir = dump_root / run_id / ep_id
            meta_path = ep_dump_dir / "meta.json"
            if not meta_path.exists():
                skipped["no_dump_meta"] += 1
                continue
            meta = json.loads(meta_path.read_text())
            meta_rounds = {r["round"]: r for r in meta.get("rounds", [])}

            inter = replay.get("vlm_interactions", [])
            instruction = replay.get("instruction", "")
            level = replay.get("level", -2)
            level_name = replay.get("task_name", "")
            active_arm = _resolve_active_arm(level_name)
            n_rounds = len(inter)

            for round_idx in range(1, n_rounds + 1):
                if round_idx < min_round:
                    skipped["below_min_round"] += 1
                    continue

                meta_round = meta_rounds.get(round_idx)
                if meta_round is None:
                    skipped["no_meta_round"] += 1
                    continue

                png_path = _round_pre_png(dump_root, run_id, ep_id, round_idx)
                if png_path is None:
                    skipped["no_pre_png"] += 1
                    continue

                interaction = inter[round_idx - 1]
                response = interaction.get("full_response") or meta_round.get("vlm_full_response") or ""
                if not response.strip():
                    skipped["empty_response"] += 1
                    continue

                state = _state_at_round(replay, meta_round, round_idx, sim_steps_per_round)
                dist_l = meta_round.get("final_dist_l_cm")
                dist_r = meta_round.get("final_dist_r_cm")

                # Filter: active-arm distance gate
                if max_active_dist_cm is not None:
                    if active_arm == "left" and dist_l is not None and dist_l > max_active_dist_cm:
                        skipped["above_dist_gate"] += 1
                        continue
                    if active_arm == "right" and dist_r is not None and dist_r > max_active_dist_cm:
                        skipped["above_dist_gate"] += 1
                        continue

                # Filter: only keep rounds that made progress
                if only_progress_round:
                    # Approximate: distance went down between start and end of this round.
                    # meta_round has only `final_dist_l/r_cm`; we compare to *next* round's
                    # actual_left_start? We use the trajectory: distance at step
                    # round_idx*sim_steps - 1 vs (round_idx-1)*sim_steps.
                    traj = replay.get("trajectory", [])
                    start_step = (round_idx - 1) * sim_steps_per_round
                    end_step = min(round_idx * sim_steps_per_round - 1, len(traj) - 1)
                    if 0 <= start_step < len(traj) and 0 <= end_step < len(traj):
                        d_key = "dist_red" if active_arm == "left" else "dist_blue"
                        d_start = (traj[start_step].get("distances") or {}).get(d_key, 0) * 100
                        d_end = (traj[end_step].get("distances") or {}).get(d_key, 0) * 100
                        if d_end >= d_start - 0.5:  # <0.5cm closer not "progress"
                            skipped["no_progress"] += 1
                            continue

                samples.append({
                    "image_path": str(png_path.resolve()),
                    "level": level,
                    "task_instruction": instruction,
                    "active_arm": active_arm,
                    "state": state,
                    "critic_feedback": meta_round.get("critic_feedback"),
                    "target_response": response,
                    "parsed_left_pos": interaction.get("parsed_left_pos"),
                    "parsed_right_pos": interaction.get("parsed_right_pos"),
                    "final_dist_l_cm": dist_l,
                    "final_dist_r_cm": dist_r,
                    "ep_id": ep_id,
                    "run_id": run_id,
                    "round_idx": round_idx,
                    "round_count_in_ep": n_rounds,
                })

    if skipped:
        logger.info(f"  skipped: {dict(skipped)}")
    return samples


def _print_stats(samples: list[dict]) -> None:
    if not samples:
        logger.info("  no samples")
        return
    n = len(samples)
    ep_counter = Counter(s["ep_id"] for s in samples)
    round_idx_hist = Counter(s["round_idx"] for s in samples)
    dist_hist: dict[str, int] = {"<5": 0, "5-10": 0, "10-20": 0, "20-30": 0, ">30": 0}
    for s in samples:
        arm = s.get("active_arm")
        d = s.get(f"final_dist_l_cm") if arm == "left" else s.get(f"final_dist_r_cm")
        if d is None:
            continue
        if d < 5: dist_hist["<5"] += 1
        elif d < 10: dist_hist["5-10"] += 1
        elif d < 20: dist_hist["10-20"] += 1
        elif d < 30: dist_hist["20-30"] += 1
        else: dist_hist[">30"] += 1

    logger.info("")
    logger.info(f"  total samples : {n}")
    logger.info(f"  unique episodes: {len(ep_counter)}")
    logger.info(f"  samples / ep   : min={min(ep_counter.values())} max={max(ep_counter.values())} avg={n/len(ep_counter):.1f}")
    logger.info(f"  round_idx histogram (R1..R10+):")
    for r in sorted(round_idx_hist):
        bar = "#" * min(60, round_idx_hist[r])
        logger.info(f"    R{r:>2}: {round_idx_hist[r]:>3} {bar}")
    logger.info(f"  active-arm end_dist (cm) histogram:")
    for k, v in dist_hist.items():
        bar = "#" * min(60, v)
        logger.info(f"    {k:>6}: {v:>3} {bar}")


def main() -> None:
    """CLI entry."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replay_root", type=Path, default=Path("data/replays"))
    parser.add_argument("--dump_root", type=Path, default=Path("data/collect_dumps"))
    parser.add_argument("--runs", nargs="+", required=True,
                        help="One or more run_ids to source success replays from.")
    parser.add_argument("--out", type=Path, required=True,
                        help="Output JSONL path (e.g. data/training_sets/v32_perround.jsonl).")
    parser.add_argument("--sim_steps_per_round", type=int, default=30)
    parser.add_argument("--min_round", type=int, default=1,
                        help="Drop samples from rounds < this (1 = keep R1).")
    parser.add_argument("--skip_first_round", action="store_true",
                        help="Shorthand for --min_round 2 (drops R1's exploration).")
    parser.add_argument("--max_active_dist_cm", type=float, default=None,
                        help="Drop rounds where the active arm is still > this cm from target.")
    parser.add_argument("--only_progress_round", action="store_true",
                        help="Keep only rounds whose end_dist < start_dist (no regression rounds).")
    args = parser.parse_args()

    if args.skip_first_round and args.min_round == 1:
        args.min_round = 2

    logger.info(f"Replay root: {args.replay_root}")
    logger.info(f"Dump root  : {args.dump_root}")
    logger.info(f"Runs       : {args.runs}")
    logger.info(f"Filters    : min_round={args.min_round}  max_dist={args.max_active_dist_cm}  only_progress={args.only_progress_round}")
    logger.info("")

    samples = build_samples(
        replay_root=args.replay_root,
        dump_root=args.dump_root,
        run_ids=args.runs,
        sim_steps_per_round=args.sim_steps_per_round,
        min_round=args.min_round,
        max_active_dist_cm=args.max_active_dist_cm,
        only_progress_round=args.only_progress_round,
    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w") as fp:
        for s in samples:
            fp.write(json.dumps(s) + "\n")
    logger.info(f"Wrote {len(samples)} samples → {args.out}")
    _print_stats(samples)


if __name__ == "__main__":
    main()
