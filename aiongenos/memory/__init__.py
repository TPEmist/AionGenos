"""Episodic memory subsystem — image-anchored recaps + retrieval.

Phase 4 design:
  - Each episode ends with a self-recap (stage4_recap.py) capturing
    (image_anchors, state_anchor, text_lesson, outcome).
  - Recaps are stored in workspace/recaps/{run_id}/{ep_id}.json by
    RecapBuffer (recap_buffer.py).
  - Image embeddings for retrieval come from image_embedding.py.
  - At R1 of a new ep, RecapBuffer.retrieve() returns top-3 visually
    similar past recaps to inject into Stage 1 teacher prompt.

Note: ``image_embedding`` imports torchvision which conflicts with some
torch installs in the IsaacLab venv. Import it lazily where you need it
(``from aiongenos.memory.image_embedding import ImageEmbedder``) rather
than top-level here.
"""

from aiongenos.memory.recap_buffer import RecapBuffer, RecapRecord

__all__ = [
    "RecapBuffer",
    "RecapRecord",
]
