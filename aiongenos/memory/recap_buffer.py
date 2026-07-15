"""Recap buffer: persistent store + two-stage retrieval.

Storage layout (workspace/recaps/ at repo root by default):
    workspace/recaps/
      INDEX.json                       ← lightweight index for fast load
      {run_id}/
        {ep_id}.json                   ← one recap per ep

Retrieval (two-stage, cheap → expensive):
  1. Coarse: KNN over init_L_EE_pos (L2 distance on 3D state).
     Returns up to ``coarse_k`` candidates (default 20).
  2. Fine:   cosine similarity on init_pre image embedding.
     Returns top ``fine_k`` (default 3).

Index is rebuilt on first load by scanning all run_id/*.json files. After
that, ``add()`` updates both disk + in-memory index incrementally.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class RecapRecord:
    """One self-recap entry. Mirrors workspace/recaps/{run}/{ep}.json on disk."""

    ep_id: str
    run_id: str
    outcome: str  # "success" | "timeout" | "vlm_stop_premature" | ...
    is_success: bool
    image_anchors: dict[str, str]  # name → relative path
    state_anchor: dict[str, Any]   # init_L_EE, final_L_EE, etc.
    text_lesson: str
    image_embedding: list[float]   # 576-dim, unit-norm
    metadata: dict[str, Any] = field(default_factory=dict)
    # L2 Amendment 1a: per-arm success labels (None on L0a/D10 buffers,
    # which never scored per-arm). When present, an arm-aligned
    # success-floor can use these instead of the joint is_success.
    left_reached: Optional[bool] = None
    right_reached: Optional[bool] = None

    def success_label(self, arm: Optional[str] = None) -> bool:
        """Arm-aligned success label. arm='left'/'right' reads the
        per-arm label if it exists (L2 Amendment 1a); arm=None or a
        buffer without per-arm labels falls back to joint is_success —
        so L0a/D10 behaviour is unchanged."""
        if arm == "left" and self.left_reached is not None:
            return self.left_reached
        if arm == "right" and self.right_reached is not None:
            return self.right_reached
        return self.is_success

    def to_json(self) -> dict[str, Any]:
        d = asdict(self)
        return d

    @classmethod
    def from_json(cls, d: dict[str, Any]) -> "RecapRecord":
        return cls(
            ep_id=d["ep_id"],
            run_id=d["run_id"],
            outcome=d["outcome"],
            is_success=d["is_success"],
            image_anchors=d["image_anchors"],
            state_anchor=d["state_anchor"],
            text_lesson=d["text_lesson"],
            image_embedding=d["image_embedding"],
            metadata=d.get("metadata", {}),
            left_reached=d.get("left_reached"),
            right_reached=d.get("right_reached"),
        )


class RecapBuffer:
    """File-backed recap store with cached retrieval index."""

    def __init__(self, root: Path | str = "workspace/recaps") -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._records: list[RecapRecord] = []
        self._init_pos: Optional[np.ndarray] = None  # (N, 3)
        self._embeddings: Optional[np.ndarray] = None  # (N, 576)
        self._loaded = False

    def load(self) -> None:
        """Scan all run_id/*.json files and rebuild the in-memory index."""
        self._records = []
        for run_dir in sorted(self.root.iterdir()):
            if not run_dir.is_dir():
                continue
            for ep_file in sorted(run_dir.glob("*.json")):
                try:
                    rec = RecapRecord.from_json(json.loads(ep_file.read_text()))
                    self._records.append(rec)
                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning(f"  skip malformed recap {ep_file}: {e}")
        self._rebuild_index()
        self._loaded = True
        logger.info(f"RecapBuffer loaded {len(self._records)} records from {self.root}")

    def _rebuild_index(self) -> None:
        if not self._records:
            self._init_pos = np.zeros((0, 3), dtype=np.float32)
            # Dim inferred at retrieval time from the query — empty index has
            # no records to rank against, so the empty shape doesn't matter.
            self._embeddings = np.zeros((0, 0), dtype=np.float32)
            return
        positions: list[list[float]] = []
        embeddings: list[list[float]] = []
        for rec in self._records:
            init = rec.state_anchor.get("init_L_EE") or [0, 0, 0]
            positions.append([float(v) for v in init])
            embeddings.append(rec.image_embedding)
        self._init_pos = np.asarray(positions, dtype=np.float32)
        self._embeddings = np.asarray(embeddings, dtype=np.float32)

    def add(self, record: RecapRecord) -> Path:
        """Persist a new recap and update in-memory index. Returns file path."""
        if not self._loaded:
            self.load()
        out_dir = self.root / record.run_id
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{record.ep_id}.json"
        out_path.write_text(json.dumps(record.to_json(), indent=2))
        self._records.append(record)
        self._rebuild_index()
        return out_path

    def __len__(self) -> int:
        if not self._loaded:
            self.load()
        return len(self._records)

    def all(self) -> list[RecapRecord]:
        if not self._loaded:
            self.load()
        return list(self._records)

    def retrieve(
        self,
        query_init_L_EE: tuple[float, float, float],
        query_image_embedding: np.ndarray,
        fine_k: int = 3,
        success_only: bool = False,
        exclude_run_ids: Optional[set[str]] = None,
        image_weight: float = 0.4,
        state_scale_cm: float = 30.0,
        success_floor_frac: float = 2.0 / 3.0,
        coarse_k: Optional[int] = None,  # kept for back-compat, ignored
        success_label_arm: Optional[str] = None,  # L2-1a: 'left'/'right' → arm-aligned floor
    ) -> list[tuple[RecapRecord, float]]:
        """Combined-score retrieval. Returns up to ``fine_k`` (record, score) pairs.

        Phase 4-rev2 (post-D10) — instead of state-KNN coarse + image cosine
        fine, we now compute one combined score for every candidate and
        rank globally:

            score = image_weight * image_cos_sim
                  + (1 - image_weight) * state_sim

            state_sim = exp(-state_distance_cm / state_scale_cm)

        Rationale: D10 showed image cosine collapsed (all sims >0.94) on
        the low-diversity L0a scene. State distance is a physical
        ground-truth signal that doesn't depend on pretrained-feature
        quality. Combining them is more robust than two-stage filtering
        (which would still inherit image collapse if it dominated
        ranking).

        Args:
            query_init_L_EE: 3D init pose to compute state similarity against.
            query_image_embedding: unit vector for image cosine.
            fine_k: final top-K returned.
            success_only: if True, filter to is_success=True records only.
            exclude_run_ids: skip recaps from these runs.
            image_weight: weight for image cosine in [0,1]. 0.4 default —
                state is treated as the more reliable signal.
            state_scale_cm: state_sim falls to 1/e at this distance. 30cm
                roughly matches the workspace diameter.
            success_floor_frac: at least ceil(success_floor_frac * fine_k)
                of the returned records must be from success episodes
                (Phase 4 Q12). If the buffer has fewer successes available,
                returns what it can plus failures to fill to fine_k.
            coarse_k: deprecated, ignored. Kept in signature so existing
                callers don't break.
        """
        if not self._loaded:
            self.load()
        if not self._records:
            return []

        # Filter mask
        keep_idx = []
        for i, rec in enumerate(self._records):
            if success_only and not rec.success_label(success_label_arm):
                continue
            if exclude_run_ids and rec.run_id in exclude_run_ids:
                continue
            keep_idx.append(i)
        if not keep_idx:
            return []

        keep_idx_arr = np.asarray(keep_idx, dtype=np.int64)
        pool_pos = self._init_pos[keep_idx_arr]
        pool_emb = self._embeddings[keep_idx_arr]

        # State similarity: exp(-d_cm / state_scale_cm), in [0, 1]
        q_pos = np.asarray(query_init_L_EE, dtype=np.float32).reshape(1, 3)
        dists_cm = np.linalg.norm(pool_pos - q_pos, axis=1)
        state_sims = np.exp(-dists_cm / float(state_scale_cm))

        # Image cosine: in [-1, 1] usually [0, 1] for unit-norm features
        q_emb = np.asarray(query_image_embedding, dtype=np.float32)
        q_norm = np.linalg.norm(q_emb)
        if q_norm > 1e-8:
            q_emb = q_emb / q_norm
        # Defensive: if dim mismatch (e.g. mixed old/new buffers), drop image term
        if pool_emb.ndim == 2 and pool_emb.shape[1] == q_emb.shape[0]:
            img_sims = pool_emb @ q_emb
        else:
            logger.warning(
                f"retrieve: image dim mismatch (buffer={pool_emb.shape}, "
                f"query={q_emb.shape}), falling back to pure state ranking"
            )
            img_sims = np.zeros_like(state_sims)
            image_weight = 0.0

        scores = image_weight * img_sims + (1.0 - image_weight) * state_sims

        # Sort all candidates by score descending
        order = np.argsort(-scores)

        # Success-floor logic (Phase 4 Q12): aim for at least
        # ceil(success_floor_frac * fine_k) success-class records.
        min_success = int(np.ceil(success_floor_frac * fine_k))
        success_picks: list[int] = []
        failure_picks: list[int] = []
        for j in order:
            global_idx = int(keep_idx_arr[int(j)])
            rec = self._records[global_idx]
            if rec.success_label(success_label_arm):
                success_picks.append(int(j))
            else:
                failure_picks.append(int(j))

        chosen: list[int] = []
        chosen.extend(success_picks[:min_success])
        remaining = fine_k - len(chosen)
        if remaining > 0:
            # Fill the rest from the highest-scoring remaining candidates,
            # mixing failures and any extra successes.
            taken = set(chosen)
            for j in order:
                if int(j) in taken:
                    continue
                chosen.append(int(j))
                taken.add(int(j))
                if len(chosen) >= fine_k:
                    break

        # Re-sort the final chosen set by score descending
        chosen.sort(key=lambda j: -scores[j])

        results: list[tuple[RecapRecord, float]] = []
        for j in chosen:
            global_idx = int(keep_idx_arr[int(j)])
            results.append((self._records[global_idx], float(scores[int(j)])))
        return results

    def stats(self) -> dict[str, Any]:
        """Quick aggregate stats for debugging."""
        if not self._loaded:
            self.load()
        n = len(self._records)
        n_succ = sum(1 for r in self._records if r.is_success)
        runs = {r.run_id for r in self._records}
        return {
            "n_records": n,
            "n_success": n_succ,
            "n_failure": n - n_succ,
            "n_runs": len(runs),
            "runs": sorted(runs),
        }
