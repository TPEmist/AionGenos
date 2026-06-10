"""Reasoning-trace inspector for a collected episode.

Reads ``meta.json`` from a ``data/collect_dumps/{run}/{ep}/`` directory and
reports cross-round patterns in the VLM's thought chain. The aim is to
distinguish three failure modes:

1. **Geometric grounding failure** — VLM's mental model of the scene's
   axes/coordinates is wrong. We surface this by checking whether the
   thought references "X+ = forward" / "Y+ = left" style claims at all,
   and whether they evolve.
2. **Reasoning sterility** — VLM repeats almost-identical thoughts each
   round (no new hypothesis), which means critic feedback isn't being
   used.
3. **Locked-in mistake** — VLM commits to an interpretation early and
   refuses to update even when distance trajectory contradicts it.

This is task-agnostic instrumentation; the analyser does not encode any
correct answer. It only flags suspicious patterns for human review.

Usage:
    python3 scripts/diagnostics/reasoning_analysis.py \\
        --dump_root data/collect_dumps \\
        [--run RUN_ID] [--episode EPISODE_ID]
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import textwrap
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

logger = logging.getLogger(__name__)


_AXIS_TOKENS = {
    "x_pos": re.compile(r"\bx\s*[+]|\+\s*x|x\s*=\s*positive|x\s*increases?", re.I),
    "x_neg": re.compile(r"\bx\s*[-]|\-\s*x|x\s*=\s*negative|x\s*decreases?", re.I),
    "y_pos": re.compile(r"\by\s*[+]|\+\s*y|y\s*=\s*positive|y\s*increases?", re.I),
    "y_neg": re.compile(r"\by\s*[-]|\-\s*y|y\s*=\s*negative|y\s*decreases?", re.I),
    "z_pos": re.compile(r"\bz\s*[+]|\+\s*z|z\s*=\s*positive|z\s*increases?|up", re.I),
    "z_neg": re.compile(r"\bz\s*[-]|\-\s*z|z\s*=\s*negative|z\s*decreases?|down", re.I),
    "forward": re.compile(r"\bforward|\bahead|further away|away from the robot", re.I),
    "backward": re.compile(r"\bbackward|\btoward(?:s)? the robot|closer to the robot|behind", re.I),
    "left": re.compile(r"\bleft\b", re.I),
    "right": re.compile(r"\bright\b", re.I),
}


_REASONING_TOKENS = {
    "regression": re.compile(r"\b(regress|further from|moved away|wrong direction|further back)", re.I),
    "progress": re.compile(r"\b(closer|made progress|moving toward|reduced distance)", re.I),
    "uncertainty": re.compile(r"\b(unsure|might|could|possibly|seems|appears)", re.I),
    "correction": re.compile(r"\b(adjust|correct|revise|change direction|try)", re.I),
    "self_critique": re.compile(r"\b(my (?:assumption|estimate|guess) was|incorrect|mistake|misjudge)", re.I),
    "frame_reflection": re.compile(r"\b(coordinate(?:\s+system)?|frame of reference|axis|axes|convention)", re.I),
}


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def _token_table(rounds: list[dict]) -> dict[str, list[int]]:
    """Per-round occurrence count for each axis/reasoning token."""
    tbl: dict[str, list[int]] = {k: [] for k in {**_AXIS_TOKENS, **_REASONING_TOKENS}}
    for rd in rounds:
        thought = rd.get("vlm_thought") or ""
        for k, pat in _AXIS_TOKENS.items():
            tbl[k].append(len(pat.findall(thought)))
        for k, pat in _REASONING_TOKENS.items():
            tbl[k].append(len(pat.findall(thought)))
    return tbl


def _format_token_row(name: str, counts: list[int]) -> str:
    cells = " ".join(f"{c:>2}" if c else " ." for c in counts)
    return f"  {name:<22} {cells}"


def _round_similarity_matrix(rounds: list[dict]) -> list[float]:
    """Pairwise consecutive thought similarity (0..1)."""
    sims: list[float] = []
    for a, b in zip(rounds, rounds[1:]):
        sims.append(_similarity(a.get("vlm_thought") or "", b.get("vlm_thought") or ""))
    return sims


def _coordinate_volatility(rounds: list[dict], arm: str) -> tuple[int, int, int]:
    """Per-axis std of the integer prediction over rounds (proxy for
    'is the VLM still searching?'). Returns (std_x, std_y, std_z)."""
    key = f"vlm_{arm}_pos_int"
    coords = [rd.get(key) for rd in rounds if rd.get(key)]
    if len(coords) < 2:
        return (0, 0, 0)
    import statistics
    cols = list(zip(*coords))
    return tuple(int(statistics.stdev(c)) for c in cols)  # type: ignore[return-value]


def _distance_progression(rounds: list[dict], side: str) -> list[float]:
    key = f"final_dist_{side}_cm"
    return [rd.get(key) or float("nan") for rd in rounds]


def _format_dist(side: str, vals: list[float]) -> str:
    cells = " ".join(f"{v:>5.1f}" if v == v else "  nan" for v in vals)
    return f"  {side}_dist (cm) {' ' * 8}{cells}"


def _latest_dir(parent: Path) -> Path:
    candidates = [p for p in parent.iterdir() if p.is_dir()]
    if not candidates:
        raise RuntimeError(f"No subdirectories under {parent}")
    return max(candidates, key=lambda p: p.stat().st_mtime)


def main() -> None:
    """CLI entry."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dump_root", type=Path, required=True)
    parser.add_argument("--run", type=str, default=None)
    parser.add_argument("--episode", type=str, default=None)
    parser.add_argument("--show_thoughts", action="store_true",
                        help="Print full per-round vlm_thought text in addition to stats.")
    parser.add_argument("--show_critic", action="store_true",
                        help="Print the programmatic critic feedback that was injected each round.")
    args = parser.parse_args()

    run_dir = args.dump_root / args.run if args.run else _latest_dir(args.dump_root)
    ep_dir = run_dir / args.episode if args.episode else _latest_dir(run_dir)
    meta_path = ep_dir / "meta.json"
    meta = json.loads(meta_path.read_text())
    rounds = meta.get("rounds", [])
    if not rounds:
        logger.info("No rounds in meta.json")
        return

    logger.info("=" * 80)
    logger.info(f"Run     : {meta.get('run_id')}")
    logger.info(f"Episode : {meta.get('episode_id')}")
    logger.info(f"Level   : L{meta.get('level')}  ({meta.get('level_name')})")
    logger.info(f"Outcome : {meta.get('outcome')}  flags={meta.get('flags')}")
    logger.info(f"Rounds  : {len(rounds)}")
    logger.info("=" * 80)
    logger.info("")

    # ── Section A: token presence per round ──────────────────────────
    tbl = _token_table(rounds)
    header = "round                  " + " ".join(f"{r['round']:>2}" for r in rounds)
    logger.info("[Token presence per round (count of regex hits)]")
    logger.info(header)
    logger.info("axis claims:")
    for k in ("x_pos", "x_neg", "y_pos", "y_neg", "z_pos", "z_neg",
              "forward", "backward", "left", "right"):
        logger.info(_format_token_row(k, tbl[k]))
    logger.info("reasoning markers:")
    for k in ("regression", "progress", "uncertainty", "correction",
              "self_critique", "frame_reflection"):
        logger.info(_format_token_row(k, tbl[k]))
    logger.info("")

    # ── Section B: distance progression ──────────────────────────────
    logger.info("[Distance progression]")
    logger.info(header)
    logger.info(_format_dist("L", _distance_progression(rounds, "l")))
    logger.info(_format_dist("R", _distance_progression(rounds, "r")))
    logger.info("")

    # ── Section C: thought volatility ────────────────────────────────
    sims = _round_similarity_matrix(rounds)
    logger.info("[Thought similarity to previous round (0=different, 1=identical)]")
    logger.info("  " + " ".join(f"{s:>4.2f}" for s in sims))
    if sims:
        avg = sum(sims) / len(sims)
        logger.info(f"  mean={avg:.2f}  max={max(sims):.2f}  min={min(sims):.2f}")
        if avg > 0.7:
            logger.info("  → WARN: high cross-round similarity (≥0.7 mean) — VLM may be repeating.")
    logger.info("")

    # ── Section D: coordinate volatility per arm ─────────────────────
    l_std = _coordinate_volatility(rounds, "left")
    r_std = _coordinate_volatility(rounds, "right")
    logger.info("[Predicted-coordinate std across rounds (in [-100,100] grid units)]")
    logger.info(f"  LEFT  arm  std=(x={l_std[0]}, y={l_std[1]}, z={l_std[2]})")
    logger.info(f"  RIGHT arm  std=(x={r_std[0]}, y={r_std[1]}, z={r_std[2]})")
    logger.info("")

    # ── Section E: optional full thought / critic dump ───────────────
    if args.show_thoughts or args.show_critic:
        for rd in rounds:
            logger.info("-" * 80)
            logger.info(
                f"Round {rd['round']:02d}  pred_L={rd.get('vlm_left_pos_int')} "
                f"pred_R={rd.get('vlm_right_pos_int')}  vlm_stop={rd.get('vlm_stop')}"
            )
            if args.show_critic and rd.get("critic_feedback"):
                logger.info("  CRITIC FEEDBACK injected:")
                logger.info(textwrap.indent(rd["critic_feedback"], "    "))
            if args.show_thoughts:
                thought = (rd.get("vlm_thought") or "").strip()
                logger.info("  THOUGHT:")
                logger.info(textwrap.indent(thought, "    "))


if __name__ == "__main__":
    main()
