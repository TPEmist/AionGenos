"""Phase 4 D11 — parse collect logs to recover the exact set of past
episodes retrieved at each new episode's R1.

For every episode in a collect log, extract:
  - The retrieval that happened at R1 (top-K past ep_ids + similarities)
  - Load each retrieved recap's text_lesson

Emit JSONL mapping ``{new_run_id, ep_id} -> {retrieved: [{ep_id, sim, lesson}]}``
so ``prep_training_data.py`` can attach the historically-consistent
rationale to each training sample.

Falls back gracefully when:
  - Log line missing (early D6 episodes had no memory) → empty retrieval
  - Retrieved recap file missing → skip that entry, keep others

Log format expected (aiongenos/orchestrator/collect.py line ~224):
    2026-06-30 18:36:29,455 - aiongenos.orchestrator.collect - INFO -
      Episode N/M | L-2 | <ep_id>
    ... (may have many other lines) ...
      memory: injected 3 past eps [id1,id2,id3] sims=[0.86,0.85,0.82]

And the "memory: buffer empty" variant when no injection happened.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


# One "Episode N/100 | L<level> | <ep_id_full>" line. We keep the full id
# because collect writes the full uuid-slug into replay filenames.
_EP_RE = re.compile(
    r"Episode\s+(\d+)/(\d+)\s+\|\s+L(-?\d+)\s+\|\s+([a-f0-9-]+)"
)
# One "memory: injected K past eps [ids] sims=[values]" line.
_MEM_RE = re.compile(
    r"memory:\s+injected\s+(\d+)\s+past\s+eps\s+\[([^\]]+)\]\s+sims=\[([^\]]+)\]"
)
_MEM_EMPTY_RE = re.compile(r"memory:\s+buffer\s+empty")


def parse_log(log_path: Path) -> list[dict]:
    """Return chronologically-ordered list of episodes with their retrieval.

    Each entry:
      {
        "ep_idx":     int (1-based),
        "ep_id":      str (full),
        "level":      int,
        "retrieved":  list[{"ep_id_prefix": str, "sim": float}] — 8-char prefixes
        "empty":      bool — True if "memory: buffer empty" logged
      }
    """
    if not log_path.exists():
        raise FileNotFoundError(str(log_path))

    entries: list[dict] = []
    current: Optional[dict] = None
    with log_path.open("r", errors="replace") as fp:
        for line in fp:
            m_ep = _EP_RE.search(line)
            if m_ep is not None:
                # Flush the previous ep if it hadn't seen a memory line yet.
                if current is not None:
                    entries.append(current)
                current = {
                    "ep_idx": int(m_ep.group(1)),
                    "ep_id": m_ep.group(4),
                    "level": int(m_ep.group(3)),
                    "retrieved": [],
                    "empty": False,
                }
                continue

            if current is None:
                continue  # pre-episode noise

            m_mem = _MEM_RE.search(line)
            if m_mem is not None:
                ids_raw = m_mem.group(2).strip()
                sims_raw = m_mem.group(3).strip()
                ids = [s.strip() for s in ids_raw.split(",") if s.strip()]
                try:
                    sims = [float(s.strip()) for s in sims_raw.split(",") if s.strip()]
                except ValueError as e:
                    logger.warning(f"  bad sims line: {line.strip()} ({e})")
                    sims = []
                if len(ids) != len(sims):
                    # Truncate to the shorter — defensive against future format changes.
                    n = min(len(ids), len(sims))
                    ids, sims = ids[:n], sims[:n]
                current["retrieved"] = [
                    {"ep_id_prefix": eid, "sim": s} for eid, s in zip(ids, sims)
                ]
                # An episode only sees one memory-injection line at R1.
                continue

            m_empty = _MEM_EMPTY_RE.search(line)
            if m_empty is not None:
                current["empty"] = True
                continue

    if current is not None:
        entries.append(current)
    return entries


def build_recap_index(recap_root: Path) -> dict[str, Path]:
    """Map every ep_id_prefix (first 8 chars) → recap json path."""
    idx: dict[str, Path] = {}
    for run_dir in sorted(recap_root.iterdir()):
        if not run_dir.is_dir():
            continue
        for f in run_dir.glob("*.json"):
            # Recap filenames use full episode_id (uuid-8chars-3chars).
            # Prefix key = first 8 chars.
            prefix = f.stem[:8]
            if prefix in idx:
                # Prefix collision — very unlikely (16^8 space) but log.
                logger.debug(f"  prefix collision {prefix}: {idx[prefix]} vs {f}")
            idx[prefix] = f
    return idx


def _load_lesson(recap_path: Optional[Path]) -> Optional[dict]:
    if recap_path is None or not recap_path.exists():
        return None
    try:
        d = json.loads(recap_path.read_text())
        return {
            "ep_id": d["ep_id"],
            "outcome": d.get("outcome"),
            "is_success": d.get("is_success"),
            "text_lesson": d.get("text_lesson", ""),
            "final_L_dist_cm": (d.get("state_anchor") or {}).get("final_L_dist_cm"),
        }
    except (json.JSONDecodeError, KeyError, OSError) as e:
        logger.debug(f"  recap load fail {recap_path}: {e}")
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--logs", nargs="+", required=True,
                        help="One or more collect-log paths.")
    parser.add_argument("--recap_root", type=Path, default=Path("workspace/recaps_d10"),
                        help="Recap buffer root.")
    parser.add_argument("--out", type=Path, required=True,
                        help="Output JSONL. One line per episode with retrieval + resolved lessons.")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    logger.info(f"Loading recap index from {args.recap_root}")
    recap_index = build_recap_index(args.recap_root)
    logger.info(f"  indexed {len(recap_index)} recaps")

    total_eps = 0
    total_with_retrieval = 0
    total_with_all_lessons = 0
    total_partial = 0
    total_orphan_ids = 0

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w") as out_fp:
        for log_path_str in args.logs:
            log_path = Path(log_path_str)
            entries = parse_log(log_path)
            logger.info(f"  {log_path.name}: {len(entries)} episodes parsed")
            for e in entries:
                total_eps += 1
                lessons: list[dict] = []
                for hit in e["retrieved"]:
                    r = recap_index.get(hit["ep_id_prefix"])
                    l = _load_lesson(r)
                    if l is None:
                        total_orphan_ids += 1
                        continue
                    l["sim"] = hit["sim"]
                    lessons.append(l)
                if e["retrieved"] and lessons:
                    total_with_retrieval += 1
                    if len(lessons) == len(e["retrieved"]):
                        total_with_all_lessons += 1
                    else:
                        total_partial += 1
                out_fp.write(json.dumps({
                    "log_file": log_path.name,
                    "ep_idx": e["ep_idx"],
                    "ep_id": e["ep_id"],
                    "level": e["level"],
                    "buffer_empty": e["empty"],
                    "retrieved_lessons": lessons,
                }) + "\n")

    logger.info("")
    logger.info(f"Total episodes:        {total_eps}")
    logger.info(f"  with any retrieval:  {total_with_retrieval}")
    logger.info(f"  with all lessons:    {total_with_all_lessons}")
    logger.info(f"  partial (some miss): {total_partial}")
    logger.info(f"  orphan retrieval ids (recap file missing): {total_orphan_ids}")
    logger.info(f"Wrote → {args.out}")


if __name__ == "__main__":
    main()
