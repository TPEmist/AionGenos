"""Image embedding extractor for episodic memory retrieval.

Phase 4-rev2 (post-D10): switched from MobileNet-V3 small to DINOv2-base.

Why: In D10's 100 ep we observed all retrieved sims clustered >0.94 cosine,
indicating MobileNet ImageNet features could not distinguish "same task,
different init pose" scenes — the visual signal collapsed and retrieval
fell back to state-KNN behavior anyway.

DINOv2 (self-supervised on 142M raw images) is known to be much more
spatially discriminative on robotics scenes (see "DINOv2 features for
navigation / VPR", multiple 2024 papers). 768-d output. ~120ms / image
on CPU, ~15ms on GPU; we run it at most once per episode (embedding
the initial RGB), so the cost is dwarfed by VLM inference.

If transformers + DINOv2 cannot be loaded for any reason, the embedder
fails noisily — there is no graceful fallback to MobileNet because the
two have different dimensionalities and would corrupt the index. Keep
the dim choice explicit in RecapBuffer (576 → 768).
"""

from __future__ import annotations

import io
import logging
from typing import Optional

import numpy as np
import torch
from PIL import Image

logger = logging.getLogger(__name__)


_DINOV2_MODEL_ID = "facebook/dinov2-base"
_DINOV2_DIM = 768


class ImageEmbedder:
    """DINOv2-base CLS-token embedder.

    Output dim = 768. Singleton per device. Eval mode only.
    """

    _instance: Optional["ImageEmbedder"] = None

    def __init__(self, device: str = "cpu") -> None:
        self.device = device
        self.dim = _DINOV2_DIM
        # Imported lazily so this module can be imported in environments
        # without transformers (the orchestrator only imports the embedder
        # through stage4_recap, which is fenced).
        from transformers import AutoImageProcessor, AutoModel
        self.processor = AutoImageProcessor.from_pretrained(_DINOV2_MODEL_ID)
        self.model = AutoModel.from_pretrained(_DINOV2_MODEL_ID)
        self.model.eval()
        self.model.to(device)
        logger.info(f"ImageEmbedder ready: {_DINOV2_MODEL_ID} on {device}, dim={self.dim}")

    @classmethod
    def get(cls, device: str = "cpu") -> "ImageEmbedder":
        if cls._instance is None or cls._instance.device != device:
            cls._instance = cls(device=device)
        return cls._instance

    @torch.no_grad()
    def embed(self, image: Image.Image) -> np.ndarray:
        """Encode a single PIL image to a unit-norm float32 vector."""
        inputs = self.processor(images=image, return_tensors="pt").to(self.device)
        out = self.model(**inputs)
        # DINOv2 returns last_hidden_state shape (1, n_patches+1, dim).
        # Index 0 is the CLS token — global image representation.
        cls = out.last_hidden_state[:, 0, :].squeeze(0).cpu().numpy().astype(np.float32)
        norm = np.linalg.norm(cls)
        if norm > 1e-8:
            cls = cls / norm
        return cls

    @torch.no_grad()
    def embed_batch(self, images: list[Image.Image]) -> np.ndarray:
        """Encode a list of PIL images. Returns (N, dim) unit-norm matrix."""
        if not images:
            return np.zeros((0, self.dim), dtype=np.float32)
        inputs = self.processor(images=images, return_tensors="pt").to(self.device)
        out = self.model(**inputs)
        cls = out.last_hidden_state[:, 0, :].cpu().numpy().astype(np.float32)
        norms = np.linalg.norm(cls, axis=1, keepdims=True)
        norms = np.maximum(norms, 1e-8)
        return cls / norms


def embed_image_bytes(image_bytes: bytes, device: str = "cpu") -> np.ndarray:
    """Convenience: decode PNG/JPG bytes and return a unit-norm 768-d vector."""
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    return ImageEmbedder.get(device).embed(image)


def embed_image_file(path: str, device: str = "cpu") -> np.ndarray:
    """Convenience: load image file and return a unit-norm 768-d vector."""
    image = Image.open(path).convert("RGB")
    return ImageEmbedder.get(device).embed(image)
