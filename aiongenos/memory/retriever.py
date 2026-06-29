"""MemoryRetriever — high-level glue around RecapBuffer + ImageEmbedder.

Given an episode's R1 init RGB (raw PNG bytes) and init L-EE state, returns a
``MemoryPreamble`` that ``run_stage1`` can prepend to the very first user turn
of the episode. The preamble is composed of:

  - formatted text block describing each retrieved past episode's outcome,
    EE start/end, and lesson text
  - list of base64-encoded PNGs for those past episodes' init images

Retrieval policy (Phase 4):
  - top-K = 3 by default (Q11)
  - two-stage retrieval: KNN over init L-EE pose (coarse) + cosine on image
    embedding (fine) — implemented in RecapBuffer.retrieve()
  - by default we include BOTH success and failure recaps so the VLM sees
    "what went wrong before" as well as "what worked" (Q12)
  - exclude_run_ids guards against retrieving from the run currently being
    collected (avoid trivial self-retrieval)
"""

from __future__ import annotations

import base64
import io
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image

from aiongenos.memory.image_embedding import ImageEmbedder
from aiongenos.memory.recap_buffer import RecapBuffer, RecapRecord

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MemoryPreamble:
    """Result of one retrieval — text block + parallel list of past images."""

    prelude_text: str  # injected before the R1 user prompt
    past_image_base64_list: list[str]  # one entry per retrieved record
    retrieved_records: tuple[RecapRecord, ...]  # for logging / debugging
    similarities: tuple[float, ...]

    @property
    def is_empty(self) -> bool:
        return len(self.retrieved_records) == 0


class MemoryRetriever:
    """High-level memory retriever for collect-loop use.

    Phase 4-rev2 retrieval parameters (set at construction, surface to
    paper as hyperparameters):
      - image_weight       : α in score = α*img_cos + (1-α)*state_sim
      - state_scale_cm     : exp(-d/scale) state similarity decay
      - success_floor_frac : minimum success ratio in top-K (Q12)

    Runtime mode override:
      - success_only_flag_path : if this file exists and contains "success_only",
            retrieval temporarily filters to success ep only (Phase 4 R4 / L2).
    """

    def __init__(
        self,
        buffer: RecapBuffer,
        top_k: int = 3,
        success_only: bool = False,
        embedder_device: str = "cpu",
        image_weight: float = 0.4,
        state_scale_cm: float = 30.0,
        success_floor_frac: float = 2.0 / 3.0,
        success_only_flag_path: Optional[Path | str] = None,
    ) -> None:
        self.buffer = buffer
        self.top_k = top_k
        self.success_only_default = success_only
        self.embedder_device = embedder_device
        self.image_weight = image_weight
        self.state_scale_cm = state_scale_cm
        self.success_floor_frac = success_floor_frac
        self.success_only_flag_path = Path(success_only_flag_path) if success_only_flag_path else None
        # Lazy: only load buffer/embedder when first used
        if not buffer._loaded:
            buffer.load()
        logger.info(
            f"MemoryRetriever ready: {len(buffer)} recaps in buffer, "
            f"top_k={top_k}, image_weight={image_weight}, "
            f"state_scale_cm={state_scale_cm}, success_floor={success_floor_frac:.2f}"
        )

    def _resolve_success_only(self) -> bool:
        """Check the optional file flag for L2 mode override."""
        if self.success_only_default:
            return True
        if self.success_only_flag_path and self.success_only_flag_path.exists():
            try:
                val = self.success_only_flag_path.read_text().strip()
                return val == "success_only"
            except OSError:
                return False
        return False

    def retrieve_for_episode(
        self,
        init_rgb_bytes: bytes,
        init_L_EE: tuple[float, float, float],
        exclude_run_ids: Optional[set[str]] = None,
    ) -> MemoryPreamble:
        """Look up top-K past similar episodes and assemble a preamble."""
        if len(self.buffer) == 0:
            return _empty_preamble()

        # Embed query image
        emb = ImageEmbedder.get(device=self.embedder_device)
        q_image = Image.open(io.BytesIO(init_rgb_bytes)).convert("RGB")
        q_vec = emb.embed(q_image)

        success_only = self._resolve_success_only()
        hits = self.buffer.retrieve(
            query_init_L_EE=init_L_EE,
            query_image_embedding=q_vec,
            fine_k=self.top_k,
            success_only=success_only,
            exclude_run_ids=exclude_run_ids,
            image_weight=self.image_weight,
            state_scale_cm=self.state_scale_cm,
            success_floor_frac=self.success_floor_frac,
        )
        if not hits:
            return _empty_preamble()

        text_block = _format_preamble_text([h[0] for h in hits], [h[1] for h in hits])
        past_b64 = _load_past_image_b64_list([h[0] for h in hits])
        # If we lost images (file missing), trim records to match
        valid = [(rec, sim, b64) for (rec, sim), b64 in zip(hits, past_b64) if b64 is not None]
        if not valid:
            return _empty_preamble()
        kept_records = tuple(v[0] for v in valid)
        kept_sims = tuple(v[1] for v in valid)
        kept_b64 = [v[2] for v in valid]
        # Re-format text block with only kept records
        final_text = _format_preamble_text(list(kept_records), list(kept_sims))
        return MemoryPreamble(
            prelude_text=final_text,
            past_image_base64_list=kept_b64,
            retrieved_records=kept_records,
            similarities=kept_sims,
        )


# ─────────────────────────── formatters ───────────────────────────


_PREAMBLE_HEADER = (
    "PAST SIMILAR EPISODES (image-anchored memory). For each one you can see "
    "what the scene looked like at start, the EE trajectory bounds, the outcome, "
    "and a one-paragraph lesson you wrote afterwards. Use these to calibrate "
    "your perception before predicting the current target.\n"
)


def _format_preamble_text(records: list[RecapRecord], similarities: list[float]) -> str:
    if not records:
        return ""
    parts: list[str] = [_PREAMBLE_HEADER]
    for i, (rec, sim) in enumerate(zip(records, similarities), start=1):
        sa = rec.state_anchor
        init_L = sa.get("init_L_EE")
        final_L = sa.get("final_L_EE")
        final_dist = sa.get("final_L_dist_cm")
        round_count = sa.get("round_count")
        outcome_class = sa.get("outcome_class", rec.outcome)
        parts.append("")
        parts.append(f"[PAST EPISODE {i}] (visual similarity={sim:.3f})")
        parts.append(f"  Image {i}: the scene at the start of that episode")
        if init_L is not None:
            parts.append(f"  init L_EE  = (X={init_L[0]}, Y={init_L[1]}, Z={init_L[2]})")
        if final_L is not None:
            parts.append(f"  final L_EE = (X={final_L[0]}, Y={final_L[1]}, Z={final_L[2]})")
        if final_dist is not None:
            try:
                parts.append(f"  final distance = {float(final_dist):.1f} cm")
            except (TypeError, ValueError):
                pass
        parts.append(f"  outcome    = {rec.outcome}  (class: {outcome_class})")
        if round_count is not None:
            parts.append(f"  rounds     = {round_count}")
        parts.append(f"  lesson     : {rec.text_lesson.strip()}")
    parts.append("")
    parts.append("─── END OF PAST EPISODES ───")
    parts.append("")
    parts.append(
        "The LAST image below is the CURRENT scene you must act on. Use the past "
        "lessons above to calibrate your perception of this current scene."
    )
    return "\n".join(parts)


def _load_past_image_b64_list(records: list[RecapRecord]) -> list[Optional[str]]:
    """Return the init_pre image of each record as base64 PNG, or None on miss."""
    out: list[Optional[str]] = []
    for rec in records:
        path = rec.image_anchors.get("init_pre")
        if not path:
            out.append(None)
            continue
        p = Path(path)
        if not p.exists():
            logger.warning(f"retriever: missing image for recap {rec.ep_id}: {path}")
            out.append(None)
            continue
        out.append(base64.b64encode(p.read_bytes()).decode("ascii"))
    return out


def _empty_preamble() -> MemoryPreamble:
    return MemoryPreamble(
        prelude_text="",
        past_image_base64_list=[],
        retrieved_records=tuple(),
        similarities=tuple(),
    )
