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
            self._embeddings = np.zeros((0, 576), dtype=np.float32)
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
        coarse_k: int = 20,
        fine_k: int = 3,
        success_only: bool = False,
        exclude_run_ids: Optional[set[str]] = None,
    ) -> list[tuple[RecapRecord, float]]:
        """Two-stage retrieval. Returns up to ``fine_k`` (record, cosine_sim) pairs.

        Args:
            query_init_L_EE: 3D init pose to KNN against.
            query_image_embedding: 576-d unit vector for cosine fine-rank.
            coarse_k: number of state-KNN candidates before image rerank.
            fine_k: final top-K returned.
            success_only: filter to is_success=True only.
            exclude_run_ids: skip recaps from these runs (used to avoid
                retrieving from the run currently being collected).
        """
        if not self._loaded:
            self.load()
        if not self._records:
            return []

        # Filter mask
        keep_idx = []
        for i, rec in enumerate(self._records):
            if success_only and not rec.is_success:
                continue
            if exclude_run_ids and rec.run_id in exclude_run_ids:
                continue
            keep_idx.append(i)
        if not keep_idx:
            return []

        keep_idx_arr = np.asarray(keep_idx, dtype=np.int64)
        pool_pos = self._init_pos[keep_idx_arr]
        pool_emb = self._embeddings[keep_idx_arr]

        # Coarse: L2 distance on init pose
        q_pos = np.asarray(query_init_L_EE, dtype=np.float32).reshape(1, 3)
        dists = np.linalg.norm(pool_pos - q_pos, axis=1)
        coarse_take = min(coarse_k, len(pool_pos))
        coarse_idx = np.argpartition(dists, coarse_take - 1)[:coarse_take]

        # Fine: cosine similarity on image embedding
        q_emb = np.asarray(query_image_embedding, dtype=np.float32)
        q_norm = np.linalg.norm(q_emb)
        if q_norm > 1e-8:
            q_emb = q_emb / q_norm
        cand_emb = pool_emb[coarse_idx]
        sims = cand_emb @ q_emb  # already unit-norm rows
        fine_take = min(fine_k, len(coarse_idx))
        # argsort descending
        order = np.argsort(-sims)[:fine_take]

        results: list[tuple[RecapRecord, float]] = []
        for j in order:
            global_idx = int(keep_idx_arr[int(coarse_idx[int(j)])])
            results.append((self._records[global_idx], float(sims[int(j)])))
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
