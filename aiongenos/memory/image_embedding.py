"""Image embedding extractor for episodic memory retrieval.

Strategy: cheap local CLIP-style embedding via torchvision's MobileNet-V3 small
penultimate layer (~3M params, ~50ms on CPU per image). We do NOT call mmproj
on the teacher endpoint because:
  1. mmproj weights are bundled in the GGUF and not exposed as a separate API.
  2. We need ~100s of embeddings (one per past ep), running them through the
     teacher would block production VLM calls.
  3. Generic image features are sufficient for "is this scene visually similar
     to a past scene" — we are not doing fine-grained semantic search.

The embedding lives in workspace/recaps/{run_id}/{ep_id}.json as a 576-dim
float32 list. Cosine similarity is used at retrieval time.
"""

from __future__ import annotations

import io
import logging
from typing import Optional

import numpy as np
import torch
import torchvision.models as tvm
import torchvision.transforms as T
from PIL import Image

logger = logging.getLogger(__name__)


class ImageEmbedder:
    """MobileNet-V3 small penultimate-layer embedder.

    Output dim = 576. Cached singleton per (device, weights). Eval mode only.
    """

    _instance: Optional["ImageEmbedder"] = None

    def __init__(self, device: str = "cpu") -> None:
        self.device = device
        weights = tvm.MobileNet_V3_Small_Weights.IMAGENET1K_V1
        net = tvm.mobilenet_v3_small(weights=weights)
        # Strip classifier head; keep up to the GAP layer (output 576-d).
        net.classifier = torch.nn.Identity()
        net.eval()
        net.to(device)
        self.net = net
        self.preprocess = weights.transforms()
        logger.info(f"ImageEmbedder ready on {device}, dim=576")

    @classmethod
    def get(cls, device: str = "cpu") -> "ImageEmbedder":
        if cls._instance is None or cls._instance.device != device:
            cls._instance = cls(device=device)
        return cls._instance

    @torch.no_grad()
    def embed(self, image: Image.Image) -> np.ndarray:
        """Encode a single PIL image to a unit-norm float32 vector of dim 576."""
        x = self.preprocess(image).unsqueeze(0).to(self.device)
        feat = self.net(x).squeeze(0).cpu().numpy().astype(np.float32)
        norm = np.linalg.norm(feat)
        if norm > 1e-8:
            feat = feat / norm
        return feat

    @torch.no_grad()
    def embed_batch(self, images: list[Image.Image]) -> np.ndarray:
        """Encode a list of PIL images. Returns (N, 576) unit-norm matrix."""
        if not images:
            return np.zeros((0, 576), dtype=np.float32)
        batch = torch.stack([self.preprocess(im) for im in images]).to(self.device)
        feats = self.net(batch).cpu().numpy().astype(np.float32)
        norms = np.linalg.norm(feats, axis=1, keepdims=True)
        norms = np.maximum(norms, 1e-8)
        return feats / norms


def embed_image_bytes(image_bytes: bytes, device: str = "cpu") -> np.ndarray:
    """Convenience: decode PNG/JPG bytes and return a 576-d unit vector."""
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    return ImageEmbedder.get(device).embed(image)


def embed_image_file(path: str, device: str = "cpu") -> np.ndarray:
    """Convenience: load image file and return a 576-d unit vector."""
    image = Image.open(path).convert("RGB")
    return ImageEmbedder.get(device).embed(image)
