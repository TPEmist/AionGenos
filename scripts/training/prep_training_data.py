"""Prepare per-round JSONL training set from success replays + collect_dumps.

Each output JSONL line is one (round_pre_image, state, action) sample —
geometrically consistent so a behavior-cloning LoRA can learn
'state X → next action' without the cross-time mismatch v3.1 hit
(v3.1 paired episode_start.png with R_final's coord; that pair was
~25 cm apart and the LoRA learned to over-shoot from home pose).

Sources:
  data/replays/{run_id}/success/*.json     — replay schema (truth)
  data/collect_dumps/{run_id}/{ep_id}/     — per-round PNGs + meta.json

Phase 4 D11 additions:
  --rationale_map <jsonl>    from extract_historical_retrievals.py — attaches
                             the historically-consistent retrieved-lessons text
                             to each sample. This lets the trainer emit target
                             responses that PREPEND a "PAST_LESSONS: ..."
                             preamble to the teacher's original THOUGHT block,
                             so the student LoRA internalises the memory-derived
                             reasoning rather than the raw action alone.

  --dataset_mode {sft,kto,whole_ep_sft}
                             sft         : per-round success rounds only (BC).
                             kto         : per-round with kto_label (KTO desirable/undesirable).
                             whole_ep_sft: one sample per success ep, using R1's image
                                           and the LAST successful round's action — for
                                           C.3-B stage 4-A. (F59 was avoided in Phase 4
                                           by memory-retrieval scaffolding; still a
                                           lossy pairing so use with care.)

For each per-round sample:
  {
    "image_path"        : "data/collect_dumps/<run>/<ep>/round_NN_pre.png",
    "level"             : -2,
    "task_instruction"  : "<from replay>",
    "active_arm"        : "left" | "right" | null,
    "state"             : {"left_ee": [...], "right_ee": [...], ...},
    "critic_feedback"   : str | null,
    "target_response"   : "<optional PAST_LESSONS: ...\\n\\n><vlm_full_response>",
    "parsed_left_pos"   : [x,y,z],
    "parsed_right_pos"  : [x,y,z],
    "final_dist_l_cm"   : float,
    "final_dist_r_cm"   : float,
    "ep_id"             : str,
    "run_id"            : str,
    "round_idx"         : int,
    "round_count_in_ep" : int,
    "outcome"           : "success" | "failure",
    "is_progress"       : bool | null,
    "d_start_cm"        : float | null,
    "d_end_cm"          : float | null,
    "kto_label"         : "desirable" | "undesirable" | null,
    "has_rationale"     : bool,
  }
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import Counter
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


# ─────────────────────────── Rationale helpers ───────────────────────────

# Max words we keep from each past lesson when building the gist. 100 words
# per recap × 3 recaps ≈ 300 words worst case; we cap at 40 each to keep
# the total under ~120 words (student rationale learning cost).
_LESSON_WORD_CAP = 40


def load_rationale_map(path: Optional[Path]) -> dict[tuple[str, str], list[dict]]:
    """Load the JSONL emitted by extract_historical_retrievals.py.

    Key = (log_file, ep_id) is unique because a single collect run's log
    contains that run's episodes exactly once. But we also allow lookup by
    (run_id, ep_id) since callers typically know run_id, not log filename.
    So we store TWO indices with the same value.
    """
    idx: dict[tuple[str, str], list[dict]] = {}
    if path is None:
        return idx
    with path.open() as fp:
        for line in fp:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            lessons = d.get("retrieved_lessons") or []
            log_file = d.get("log_file", "")
            ep_id = d.get("ep_id", "")
            if ep_id:
                # Key by ep_id alone (ep_ids are uuid-like enough to be unique
                # across all runs so far — we assert this on collision).
                if ep_id in idx and idx[ep_id] != lessons:
                    logger.debug(f"  rationale_map: ep_id collision {ep_id} — keeping first")
                else:
                    idx[ep_id] = lessons
    return idx


def format_rationale_gist(lessons: list[dict], max_lessons: int = 3) -> str:
    """Compress up to ``max_lessons`` retrieved-recap lessons into a single
    PAST_LESSONS preamble that fits comfortably in a training target."""
    if not lessons:
        return ""
    parts: list[str] = ["PAST_LESSONS (from similar past attempts):"]
    for i, l in enumerate(lessons[:max_lessons], 1):
        text = (l.get("text_lesson") or "").strip()
        if not text:
            continue
        words = text.split()
        if len(words) > _LESSON_WORD_CAP:
            words = words[:_LESSON_WORD_CAP]
            text = " ".join(words) + " …"
        outcome_marker = "✓" if l.get("is_success") else "✗"
        parts.append(f"  ({i}) [{outcome_marker}] {text}")
    parts.append("")  # blank line before teacher's THOUGHT
    return "\n".join(parts)


def wrap_target_with_rationale(rationale_gist: str, original_response: str) -> str:
    """Prepend rationale gist to teacher's original response. If rationale
    is empty (early ep with no retrieval), returns original response unchanged."""
    if not rationale_gist:
        return original_response
    return f"{rationale_gist}\n{original_response}"


# ─────────────────────────── D6-native THOUGHT extractor (A_ctrl_rat) ───────

import re as _re_native
# D6 stage-1 responses do NOT literally emit "THOUGHT:" as a header — the
# model produces prose reasoning followed by the LEFT_TARGET_POS lines.
# Empirical inspection confirms: raw response = <prose paragraph>
# \n LEFT_TARGET_POS: ... \n RIGHT_TARGET_POS: ... \n STOP: ...
# So the "thought" is everything BEFORE the first coordinate output line.
_THOUGHT_RE = _re_native.compile(
    r"(?:THOUGHT:)?\s*(.*?)(?=\n?LEFT_TARGET_POS:|\n?RIGHT_TARGET_POS:|$)",
    _re_native.DOTALL | _re_native.IGNORECASE,
)

# Cap picked to match B_main gist median (129 words) — pre-registration
# Amendment 7 §7.1 pins this. Longer thoughts have decision content in
# the tail, so we keep the LAST N words rather than truncating from the
# front.
_A_CTRL_RAT_WORD_CAP = 130


def _build_action_lines(interaction: dict) -> str:
    """Build canonical action-lines string from parsed coordinate fields.

    D6 (and other) stage-1 responses save `full_response` as prose only,
    with LEFT_TARGET_POS/etc. parsed out separately into interaction
    fields. To construct an "action-only" target we synthesize the
    canonical LEFT_TARGET_POS: X=.. Y=.. Z=.. \n RIGHT_TARGET_POS: ...
    from those fields. This is what the Stage-1 prompt template expects
    the model to emit, so it matches training format exactly.
    """
    left = interaction.get("parsed_left_pos") or [0, 0, 0]
    right = interaction.get("parsed_right_pos") or [0, 0, 0]
    stop_flag = interaction.get("parsed_stop", False)
    parts = []
    parts.append(f"LEFT_TARGET_POS:  X={left[0]} Y={left[1]} Z={left[2]}")
    parts.append(f"RIGHT_TARGET_POS: X={right[0]} Y={right[1]} Z={right[2]}")
    parts.append(f"STOP: {'true' if stop_flag else 'false'}")
    return "\n".join(parts)


def extract_native_thought(full_response: str) -> str:
    """Extract the THOUGHT paragraph from a D6 stage-1 raw response.

    Returns empty string if no THOUGHT section found. Length-cap and
    tail-preserving truncation applied per Amendment 7 §7.1.
    """
    m = _THOUGHT_RE.search(full_response or "")
    if not m:
        return ""
    text = m.group(1).strip()
    words = text.split()
    if len(words) > _A_CTRL_RAT_WORD_CAP:
        # Preserve DECISION tail — decision terms appear at end of D6's CoT
        # (empirical inspection: "I need to move the left arm in..." is the
        # closing pattern). Prefix "..." makes truncation legible in target.
        text = "… " + " ".join(words[-_A_CTRL_RAT_WORD_CAP:])
    return text


def format_native_rationale_gist(native_thought: str) -> str:
    """Prefix a D6 native thought with a header that mirrors the structural
    shape of the B_main PAST_LESSONS block but uses only intrinsic content
    (no cross-episode retrieval). This lets A_ctrl_rat's target format
    match B_main's schema without importing memory content.
    """
    if not native_thought:
        return ""
    parts = ["INTRINSIC_RATIONALE (this attempt's own reasoning):",
             f"  {native_thought}",
             ""]
    return "\n".join(parts)


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
    include_failures: bool = False,
    progress_threshold_cm: float = 0.5,
    rationale_map: Optional[dict[str, list[dict]]] = None,
    rationale_source: str = "retrieval",  # "retrieval" | "native" | "gist_only" | "none"
    restrict_to_retrievable: bool = False,
) -> list[dict]:
    """Build per-round samples from replay episodes (Phase 4 Option C+).

    Output schema per sample (one JSONL line):
      - ``outcome``    : "success" | "failure"  (Q9.2)
      - ``is_progress``: bool, distance decreased >progress_threshold_cm this round (Q9.1)
      - ``kto_label``  : "desirable" if (outcome=success AND is_progress)
                         "undesirable" if (outcome=failure AND is_progress)
                         omitted otherwise

    Non-progress rounds are dropped by default (``only_progress_round=True``
    is the Phase 4 Option C+ recommendation).
    """
    samples: list[dict] = []
    skipped = Counter()

    for run_id in run_ids:
        run_dir = replay_root / run_id
        if not run_dir.exists():
            logger.warning(f"  {run_id}: no run dir, skip")
            continue

        subdirs: list[tuple[str, Path]] = []
        succ_dir = run_dir / "success"
        if succ_dir.exists():
            subdirs.append(("success", succ_dir))
        if include_failures:
            fail_dir = run_dir / "failure"
            if fail_dir.exists():
                subdirs.append(("failure", fail_dir))

        if not subdirs:
            logger.warning(f"  {run_id}: no success/ or failure/ dirs, skip")
            continue

        for ep_outcome, subdir in subdirs:
            for replay_path in sorted(subdir.glob("*.json")):
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
                traj = replay.get("trajectory", [])
                d_key = "dist_red" if active_arm == "left" else "dist_blue"

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

                    # Phase 4 D11 rationale attachment — Amendment 8 2×2
                    # factorial. All arms terminate with canonical action
                    # lines synthesized from parsed coords (cross-arm
                    # ablation hygiene: single output-format synthesizer
                    # _build_action_lines used everywhere so R1 ΔX probe
                    # is well-defined on every arm).
                    #
                    #                    | no gist          | with gist
                    #   no native thought| "none"  A_ctrl   | "gist_only" D_gist
                    #   native thought   | "native" A_ctrl_rat | "retrieval" B_main
                    #
                    # Same-round pairing (Amendment 7 §7.3): native THOUGHT
                    # source and action target come from the SAME interaction
                    # (inter[round_idx-1]) — enforced by construction.
                    has_rationale = False
                    action_lines = _build_action_lines(interaction)

                    # Cross-arm hygiene: A_ctrl / A_ctrl_rat should share the
                    # SAME row-set as B_main / D_gist. Drop rows whose ep has
                    # no retrieval hit even when the current arm doesn't
                    # need the gist itself.
                    if (restrict_to_retrievable
                            and rationale_source in ("none", "native")
                            and rationale_map is not None
                            and not (rationale_map.get(ep_id) or [])):
                        skipped["no_retrieval_for_ep"] += 1
                        continue

                    if rationale_source == "retrieval" and rationale_map is not None:
                        # B_main: PAST_LESSONS gist + native thought + canonical.
                        lessons = rationale_map.get(ep_id) or []
                        gist_block = format_rationale_gist(lessons) if lessons else ""
                        native_thought = extract_native_thought(
                            interaction.get("full_response", "")
                        )
                        thought_block = (
                            format_native_rationale_gist(native_thought)
                            if native_thought else ""
                        )
                        if gist_block and thought_block:
                            response = gist_block + "\n" + thought_block + action_lines
                            has_rationale = True
                        elif gist_block:
                            # Rare: interaction has no parseable native thought.
                            # Keep sample with gist + canonical only rather than
                            # dropping — Amendment 8 §8.6 logs these.
                            response = gist_block + "\n" + action_lines
                            has_rationale = True
                        elif thought_block:
                            # Rare: ep has no retrieval hits. Skip — this row
                            # would not be a B_main sample.
                            skipped["no_retrieval_for_ep"] += 1
                            continue
                        else:
                            skipped["no_retrieval_for_ep"] += 1
                            continue
                    elif rationale_source == "native":
                        # A_ctrl_rat: native thought + canonical.
                        native_thought = extract_native_thought(
                            interaction.get("full_response", "")
                        )
                        if native_thought:
                            thought_block = format_native_rationale_gist(native_thought)
                            if thought_block:
                                response = thought_block + action_lines
                                has_rationale = True
                    elif rationale_source == "gist_only":
                        # D_gist (Amendment 8 secondary): gist + canonical,
                        # no native thought. Fills the {gist=yes, thought=no}
                        # cell of the 2×2 factorial.
                        lessons = rationale_map.get(ep_id) if rationale_map else None
                        if lessons:
                            gist_block = format_rationale_gist(lessons)
                            if gist_block:
                                response = gist_block + "\n" + action_lines
                                has_rationale = True
                            else:
                                skipped["no_retrieval_for_ep"] += 1
                                continue
                        else:
                            skipped["no_retrieval_for_ep"] += 1
                            continue
                    elif rationale_source == "none":
                        # A_ctrl: canonical action lines only.
                        response = action_lines

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

                    # Compute is_progress: distance dropped > progress_threshold_cm
                    # this round (Q9.1). Use trajectory delta when possible.
                    is_progress: Optional[bool] = None
                    d_start_cm = d_end_cm = None
                    if traj:
                        start_step = (round_idx - 1) * sim_steps_per_round
                        end_step = min(round_idx * sim_steps_per_round - 1, len(traj) - 1)
                        if 0 <= start_step < len(traj) and 0 <= end_step < len(traj):
                            d_start_cm = (traj[start_step].get("distances") or {}).get(d_key, 0) * 100
                            d_end_cm = (traj[end_step].get("distances") or {}).get(d_key, 0) * 100
                            is_progress = (d_end_cm < d_start_cm - progress_threshold_cm)

                    # Filter: only keep rounds that made progress (Phase 4 Option C+)
                    if only_progress_round and is_progress is False:
                        skipped[f"no_progress_{ep_outcome}"] += 1
                        continue
                    if only_progress_round and is_progress is None:
                        skipped["no_progress_indeterminate"] += 1
                        continue

                    # KTO label (Q9.2):
                    #   desirable   = success ep + progress round  (good action that led to global success)
                    #   undesirable = failure ep + progress round  (locally good but globally failed)
                    #   not set otherwise (skipped or non-progress)
                    if is_progress is True:
                        if ep_outcome == "success":
                            kto_label = "desirable"
                        elif ep_outcome == "failure":
                            kto_label = "undesirable"
                        else:
                            kto_label = None
                    else:
                        kto_label = None

                    samples.append({
                        "image_path": str(png_path.resolve()),
                        "level": level,
                        "task_instruction": instruction,
                        "active_arm": active_arm,
                        "state": state,
                        "critic_feedback": meta_round.get("critic_feedback"),
                        "target_response": response,
                        "has_rationale": has_rationale,
                        "parsed_left_pos": interaction.get("parsed_left_pos"),
                        "parsed_right_pos": interaction.get("parsed_right_pos"),
                        "final_dist_l_cm": dist_l,
                        "final_dist_r_cm": dist_r,
                        "ep_id": ep_id,
                        "run_id": run_id,
                        "round_idx": round_idx,
                        "round_count_in_ep": n_rounds,
                        # Phase 4 Option C+ fields
                        "outcome": ep_outcome,
                        "is_progress": is_progress,
                        "d_start_cm": d_start_cm,
                        "d_end_cm": d_end_cm,
                        "kto_label": kto_label,
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

    # Phase 4 Option C+ extras
    outcome_hist = Counter(s.get("outcome") for s in samples)
    kto_hist = Counter(s.get("kto_label") for s in samples)
    progress_hist = Counter(s.get("is_progress") for s in samples)
    rationale_hist = Counter(s.get("has_rationale") for s in samples)
    logger.info(f"  outcome split  : {dict(outcome_hist)}")
    logger.info(f"  is_progress    : {dict(progress_hist)}")
    logger.info(f"  kto_label      : {dict(kto_hist)}")
    logger.info(f"  has_rationale  : {dict(rationale_hist)}")


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
                        help="Keep only rounds where end_dist < start_dist - progress_threshold_cm "
                             "(Phase 4 Option C+).")
    parser.add_argument("--progress_threshold_cm", type=float, default=0.5,
                        help="Min cm of distance reduction to count as 'progress' (Q9.1, default 0.5).")
    parser.add_argument("--include_failures", action="store_true",
                        help="Also pull samples from failure/*.json (Q9.2). Each sample is tagged with "
                             "outcome=success|failure and kto_label=desirable|undesirable.")
    parser.add_argument("--rationale_map", type=Path, default=None,
                        help="Phase 4 D11: JSONL produced by extract_historical_retrievals.py. "
                             "For each ep with retrieval history, prepend a PAST_LESSONS block "
                             "to the training target so student LoRA learns memory-derived reasoning.")
    parser.add_argument("--restrict_to_retrievable", action="store_true",
                        help="Amendment 8 cross-arm hygiene: even for --rationale_source none/native "
                             "(which do not need PAST_LESSONS gist), still drop samples whose ep_id "
                             "has no rationale_map hit. This aligns the sample set across all four "
                             "arms of the 2×2 factorial so training-step count is a shared variable, "
                             "not a between-arm confound. Requires --rationale_map.")
    parser.add_argument("--rationale_source",
                        choices=("retrieval", "native", "gist_only", "none"),
                        default="retrieval",
                        help="Amendment 8 2×2 factorial: rationale attachment mode. "
                             "All arms terminate with canonical action lines from "
                             "_build_action_lines(inter). "
                             "'retrieval'  (B_main):   PAST_LESSONS gist + native THOUGHT + canonical. "
                             "'native'     (A_ctrl_rat): native THOUGHT + canonical. "
                             "'gist_only'  (D_gist, secondary): PAST_LESSONS gist + canonical. "
                             "'none'       (A_ctrl):   canonical only.")
    args = parser.parse_args()

    if args.skip_first_round and args.min_round == 1:
        args.min_round = 2

    rationale_map = load_rationale_map(args.rationale_map) if args.rationale_map else None

    logger.info(f"Replay root: {args.replay_root}")
    logger.info(f"Dump root  : {args.dump_root}")
    logger.info(f"Runs       : {args.runs}")
    logger.info(f"Filters    : min_round={args.min_round}  max_dist={args.max_active_dist_cm}  "
                f"only_progress={args.only_progress_round}  progress_thr={args.progress_threshold_cm}cm  "
                f"include_failures={args.include_failures}")
    if rationale_map is not None:
        logger.info(f"Rationale  : {len(rationale_map)} eps have retrieved-lessons context")
    logger.info("")

    samples = build_samples(
        replay_root=args.replay_root,
        dump_root=args.dump_root,
        run_ids=args.runs,
        sim_steps_per_round=args.sim_steps_per_round,
        min_round=args.min_round,
        max_active_dist_cm=args.max_active_dist_cm,
        only_progress_round=args.only_progress_round,
        include_failures=args.include_failures,
        progress_threshold_cm=args.progress_threshold_cm,
        rationale_map=rationale_map,
        rationale_source=args.rationale_source,
        restrict_to_retrievable=args.restrict_to_retrievable,
    )

    # Amendment 7 §7.1 length-distribution audit — print histograms so
    # any cross-arm length skew is visible before training. Applies only
    # when rationale is attached.
    if args.rationale_source in ("retrieval", "native", "gist_only"):
        import statistics as _st
        wlens = []
        for s in samples:
            if s.get("has_rationale"):
                wlens.append(len(s["target_response"].split()))
        if wlens:
            logger.info("")
            logger.info(f"Rationale-attached target word count "
                        f"(rationale_source={args.rationale_source}, n={len(wlens)}):")
            logger.info(f"  min={min(wlens)} p25={sorted(wlens)[len(wlens)//4]} "
                        f"median={_st.median(wlens):.0f} "
                        f"p75={sorted(wlens)[3*len(wlens)//4]} max={max(wlens)}")
            logger.info(f"  mean={_st.mean(wlens):.0f} stdev={_st.stdev(wlens) if len(wlens)>1 else 0:.1f}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w") as fp:
        for s in samples:
            fp.write(json.dumps(s) + "\n")
    logger.info(f"Wrote {len(samples)} samples → {args.out}")
    _print_stats(samples)


if __name__ == "__main__":
    main()
