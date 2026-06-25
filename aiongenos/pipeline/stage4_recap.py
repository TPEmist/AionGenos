"""Stage 4-R — Self-Recap Generation (post-episode reflection).

After each episode, the teacher VLM is shown a curated set of images from the
trajectory + ground-truth physical outcome (NOT the GT cube coordinates) and
asked to produce a ≤100-word visual lesson. The output is stored as a
``RecapRecord`` with image_anchors, state_anchor, text_lesson, and an image
embedding for retrieval (Phase 4 Q2/Q4).

Key invariants:
  - Ground-truth cube/target coordinates are NEVER given to the VLM
    (overfit risk). Only outcome + where the EE actually landed.
  - At least two images are anchored: init_pre and final_post. Depending on
    outcome type, a key-round image is also dumped (Q5).
  - Embedding is computed on the init_pre image — that's the retrieval key.
"""

from __future__ import annotations

import io
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import numpy as np
from PIL import Image

from aiongenos.memory.image_embedding import ImageEmbedder
from aiongenos.memory.recap_buffer import RecapBuffer, RecapRecord
from aiongenos.vlm.client import call_vlm_sync, encode_image_bytes_base64

logger = logging.getLogger(__name__)


# Outcome classification → key-round selection strategy (Q5)
_NEAR_MISS_THRESHOLD_CM = 10.0


@dataclass(frozen=True)
class _RoundInfo:
    """Lightweight per-round derived stats."""

    round_idx: int  # 1-based
    pre_png: Optional[Path]
    final_dist_cm: float  # active arm distance at end of round
    parsed_left_pos: Optional[list[int]]


# ─────────────────────────── public API ───────────────────────────


def generate_recap(
    *,
    ep_id: str,
    run_id: str,
    outcome: str,
    active_arm: Optional[str],
    instruction: str,
    init_L_EE: tuple[int, int, int],
    final_L_EE: tuple[int, int, int],
    init_R_EE: Optional[tuple[int, int, int]],
    final_R_EE: Optional[tuple[int, int, int]],
    rounds: list[_RoundInfo],
    ep_dump_dir: Optional[Path],
    rgb_start_bytes: Optional[bytes],
    rgb_end_bytes: Optional[bytes],
    teacher_url: str,
    buffer: RecapBuffer,
    embedder_device: str = "cpu",
    max_words: int = 100,
) -> Optional[RecapRecord]:
    """Build + persist a recap for one episode. Returns the saved record.

    Caller responsibilities (already done by collect.py end-of-ep hook):
      - Pass ``ep_dump_dir`` if per-round PNGs are available (preferred path
        for image_anchors). If None, the embedding falls back to in-memory
        ``rgb_start_bytes``.
      - Trajectory's per-round final distance comes from collect's
        ``round_meta`` — caller adapts that into ``rounds`` list.
    """
    is_success = outcome == "success"

    # Pick key-round image and outcome class
    key_round = _select_key_round(outcome, rounds)
    outcome_class = _classify_outcome(outcome, rounds)

    # Resolve image anchors (relative paths for cross-machine portability)
    anchors: dict[str, str] = {}
    if ep_dump_dir is not None:
        ep_dump_dir = Path(ep_dump_dir)
        init_png = ep_dump_dir / "round_01_pre.png"
        end_png = ep_dump_dir / "episode_end.png"
        if init_png.exists():
            anchors["init_pre"] = str(init_png.resolve())
        if end_png.exists():
            anchors["final_post"] = str(end_png.resolve())
        if key_round is not None and key_round.pre_png is not None:
            anchors["key_round_pre"] = str(key_round.pre_png.resolve())

    # Resolve image bytes for VLM call + embedding
    init_bytes = _read_bytes(anchors.get("init_pre")) or rgb_start_bytes
    final_bytes = _read_bytes(anchors.get("final_post")) or rgb_end_bytes
    key_bytes = _read_bytes(anchors.get("key_round_pre"))

    if init_bytes is None:
        logger.warning(f"recap({ep_id}): no init image, skip")
        return None

    # Embed init_pre for retrieval key
    embedder = ImageEmbedder.get(device=embedder_device)
    init_pil = Image.open(io.BytesIO(init_bytes)).convert("RGB")
    embedding = embedder.embed(init_pil).tolist()

    # Build VLM prompt and call teacher
    text_lesson = _request_vlm_recap(
        teacher_url=teacher_url,
        outcome=outcome,
        outcome_class=outcome_class,
        active_arm=active_arm or "left",
        instruction=instruction,
        init_L_EE=init_L_EE,
        final_L_EE=final_L_EE,
        init_R_EE=init_R_EE,
        final_R_EE=final_R_EE,
        rounds=rounds,
        key_round=key_round,
        init_bytes=init_bytes,
        final_bytes=final_bytes,
        key_bytes=key_bytes,
        max_words=max_words,
    )
    if not text_lesson:
        logger.warning(f"recap({ep_id}): VLM returned empty, skip")
        return None

    state_anchor: dict[str, Any] = {
        "init_L_EE": list(init_L_EE),
        "final_L_EE": list(final_L_EE),
        "final_L_dist_cm": rounds[-1].final_dist_cm if rounds else None,
        "round_count": len(rounds),
        "active_arm": active_arm,
        "outcome_class": outcome_class,
    }
    if init_R_EE is not None:
        state_anchor["init_R_EE"] = list(init_R_EE)
    if final_R_EE is not None:
        state_anchor["final_R_EE"] = list(final_R_EE)

    record = RecapRecord(
        ep_id=ep_id,
        run_id=run_id,
        outcome=outcome,
        is_success=is_success,
        image_anchors=anchors,
        state_anchor=state_anchor,
        text_lesson=text_lesson,
        image_embedding=embedding,
        metadata={"instruction": instruction, "key_round_idx": key_round.round_idx if key_round else None},
    )
    path = buffer.add(record)
    logger.info(f"recap({ep_id}): saved → {path}  ({len(text_lesson.split())} words, outcome_class={outcome_class})")
    return record


# ─────────────────────────── helpers ───────────────────────────


def _read_bytes(path: Optional[str]) -> Optional[bytes]:
    if not path:
        return None
    p = Path(path)
    if not p.exists():
        return None
    return p.read_bytes()


def _classify_outcome(outcome: str, rounds: list[_RoundInfo]) -> str:
    """Map (outcome, trajectory) into a recap-relevant class label (Q5)."""
    if outcome == "success":
        return "success"
    if not rounds:
        return outcome
    best_dist = min(r.final_dist_cm for r in rounds if r.final_dist_cm is not None)
    final_dist = rounds[-1].final_dist_cm
    # Near-miss: best ever <10cm but didn't close
    if best_dist < _NEAR_MISS_THRESHOLD_CM and final_dist > _NEAR_MISS_THRESHOLD_CM:
        return "near_miss"
    # Wrong-direction: final dist significantly worse than starting dist
    if rounds and rounds[0].final_dist_cm and final_dist > rounds[0].final_dist_cm + 5.0:
        return "wrong_direction"
    return outcome  # fallback (timeout / vlm_stop_premature / etc.)


def _select_key_round(outcome: str, rounds: list[_RoundInfo]) -> Optional[_RoundInfo]:
    """Pick one mid-trajectory round whose image is most useful for the recap (Q5)."""
    if not rounds:
        return None
    outcome_class = _classify_outcome(outcome, rounds)
    if outcome_class == "success":
        return None  # final_post already covers success
    if outcome_class == "near_miss":
        # Show the round where EE got closest — what did the scene look like then?
        return min(rounds, key=lambda r: r.final_dist_cm if r.final_dist_cm is not None else 1e9)
    if outcome_class == "wrong_direction":
        # Show the round where EE was furthest — visual of "going wrong way"
        return max(rounds, key=lambda r: r.final_dist_cm if r.final_dist_cm is not None else -1e9)
    # Default: middle round
    return rounds[len(rounds) // 2]


def _request_vlm_recap(
    *,
    teacher_url: str,
    outcome: str,
    outcome_class: str,
    active_arm: str,
    instruction: str,
    init_L_EE: tuple[int, int, int],
    final_L_EE: tuple[int, int, int],
    init_R_EE: Optional[tuple[int, int, int]],
    final_R_EE: Optional[tuple[int, int, int]],
    rounds: list[_RoundInfo],
    key_round: Optional[_RoundInfo],
    init_bytes: bytes,
    final_bytes: Optional[bytes],
    key_bytes: Optional[bytes],
    max_words: int,
) -> Optional[str]:
    """Build the recap prompt + call teacher VLM. Returns the lesson text or None."""
    system_prompt = _build_recap_system_prompt(max_words=max_words)
    user_prompt = _build_recap_user_prompt(
        outcome=outcome,
        outcome_class=outcome_class,
        active_arm=active_arm,
        instruction=instruction,
        init_L_EE=init_L_EE,
        final_L_EE=final_L_EE,
        init_R_EE=init_R_EE,
        final_R_EE=final_R_EE,
        rounds=rounds,
        key_round=key_round,
        has_final_image=final_bytes is not None,
        has_key_image=key_bytes is not None,
        max_words=max_words,
    )

    image_list = [encode_image_bytes_base64(init_bytes)]
    if final_bytes is not None:
        image_list.append(encode_image_bytes_base64(final_bytes))
    if key_bytes is not None:
        image_list.append(encode_image_bytes_base64(key_bytes))

    try:
        raw = call_vlm_sync(
            url=teacher_url,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            image_base64_list=image_list,
            temperature=0.4,
            max_tokens=400,  # ~100 words ≈ 150-200 tokens; budget room for slack
            timeout=180.0,
        )
        return _trim_to_word_limit(raw.strip(), max_words)
    except Exception as e:
        logger.warning(f"recap VLM call failed: {e}")
        return None


def _build_recap_system_prompt(max_words: int) -> str:
    return (
        "You are a bimanual robot reviewing your own past episode. "
        "You will see images from the start (and end, plus optionally a key mid-round) "
        "of an attempted reach task, along with the physical outcome.\n"
        "\n"
        "Your goal is to write a short visual lesson — a takeaway you can give to a "
        "future-you facing a visually similar scene. Focus on perception, not on "
        "ground-truth coordinates (which you do not have).\n"
        "\n"
        f"STRICT RULES:\n"
        f"  - Output {max_words} words MAX, plain prose, single paragraph.\n"
        f"  - Do NOT output target coordinates, predicted positions, or any new\n"
        f"    'LEFT_TARGET_POS' line. This is a reflection, not a plan.\n"
        f"  - Describe what visual cue in the image was misleading (if failure)\n"
        f"    or trustworthy (if success). Examples: 'cube looked left of EE but\n"
        f"    was actually right', 'the X-axis appeared to point the other way',\n"
        f"    'when EE Y was high, the cube was further forward than it looked'.\n"
        f"  - You MAY reference your own EE start/end coordinates and the\n"
        f"    distance values you observed. Those are physical facts.\n"
        f"  - One concrete lesson is better than three vague ones.\n"
    )


def _build_recap_user_prompt(
    *,
    outcome: str,
    outcome_class: str,
    active_arm: str,
    instruction: str,
    init_L_EE: tuple[int, int, int],
    final_L_EE: tuple[int, int, int],
    init_R_EE: Optional[tuple[int, int, int]],
    final_R_EE: Optional[tuple[int, int, int]],
    rounds: list[_RoundInfo],
    key_round: Optional[_RoundInfo],
    has_final_image: bool,
    has_key_image: bool,
    max_words: int,
) -> str:
    n = len(rounds)
    parts: list[str] = []
    parts.append(f"TASK: {instruction}")
    parts.append(f"ACTIVE_ARM: {active_arm}")
    parts.append(f"OUTCOME: {outcome}  (class: {outcome_class})")
    parts.append(f"ROUND_COUNT: {n}")
    parts.append("")
    parts.append("INITIAL STATE (Image 1):")
    parts.append(f"  LEFT_EE_POS  = (X={init_L_EE[0]}, Y={init_L_EE[1]}, Z={init_L_EE[2]})")
    if init_R_EE is not None:
        parts.append(f"  RIGHT_EE_POS = (X={init_R_EE[0]}, Y={init_R_EE[1]}, Z={init_R_EE[2]})")
    if has_final_image:
        parts.append("")
        parts.append("FINAL STATE (Image 2):")
        parts.append(f"  LEFT_EE_POS  = (X={final_L_EE[0]}, Y={final_L_EE[1]}, Z={final_L_EE[2]})")
        if final_R_EE is not None:
            parts.append(f"  RIGHT_EE_POS = (X={final_R_EE[0]}, Y={final_R_EE[1]}, Z={final_R_EE[2]})")
        if rounds and rounds[-1].final_dist_cm is not None:
            parts.append(f"  FINAL_DIST   = {rounds[-1].final_dist_cm:.1f} cm")
    if has_key_image and key_round is not None:
        parts.append("")
        parts.append(f"KEY ROUND IMAGE (Image 3, round {key_round.round_idx}):")
        if key_round.final_dist_cm is not None:
            parts.append(f"  EE distance at this round end = {key_round.final_dist_cm:.1f} cm")
        if key_round.parsed_left_pos is not None:
            kx, ky, kz = key_round.parsed_left_pos
            parts.append(f"  LEFT_TARGET predicted that round = (X={kx}, Y={ky}, Z={kz})")
    parts.append("")
    parts.append("YOUR R1 PREDICTION vs WHERE YOU ACTUALLY LANDED:")
    if rounds and rounds[0].parsed_left_pos is not None:
        r1x, r1y, r1z = rounds[0].parsed_left_pos
        parts.append(f"  R1 target predicted: (X={r1x}, Y={r1y}, Z={r1z})")
    parts.append(f"  Actually landed at:  (X={final_L_EE[0]}, Y={final_L_EE[1]}, Z={final_L_EE[2]})")
    parts.append("")
    parts.append(
        f"Now write your ≤{max_words}-word visual lesson for future-you. "
        f"What perception cue should future-you trust or distrust in a similar scene?"
    )
    return "\n".join(parts)


def _trim_to_word_limit(text: str, max_words: int) -> str:
    """Hard cap on word count — soft guidance in prompt is not always honored."""
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]) + " …"


# ─────────────────────────── round-info adapter ───────────────────────────


def rounds_from_meta_and_interactions(
    round_meta_list: list[dict[str, Any]],
    vlm_interactions: list[Any],
    ep_dump_dir: Optional[Path],
    active_arm: Optional[str],
) -> list[_RoundInfo]:
    """Adapt collect.py's ``round_meta`` + ``vlm_interactions`` into RoundInfo.

    The two lists are 1:1 by round_idx. Only stage1 interactions matter.
    """
    rounds: list[_RoundInfo] = []
    stage1s = [i for i in vlm_interactions if getattr(i, "stage", None) == "stage1"]
    n = min(len(round_meta_list), len(stage1s))
    for i in range(n):
        meta = round_meta_list[i]
        s1 = stage1s[i]
        pre_png: Optional[Path] = None
        if ep_dump_dir is not None:
            cand = Path(ep_dump_dir) / f"round_{i + 1:02d}_pre.png"
            if cand.exists():
                pre_png = cand
        # Active-arm distance
        if active_arm == "right":
            dist = meta.get("final_dist_r_cm")
        else:
            dist = meta.get("final_dist_l_cm")
        parsed_l = list(getattr(s1, "parsed_left_pos", None) or [])
        rounds.append(
            _RoundInfo(
                round_idx=i + 1,
                pre_png=pre_png,
                final_dist_cm=float(dist) if dist is not None else float("nan"),
                parsed_left_pos=parsed_l or None,
            )
        )
    return rounds
