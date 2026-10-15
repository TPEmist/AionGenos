"""Human-eye-gate GIF frames (PI only, never a model input).

The PI convention (2026-10-15) is front | top side by side. Each panel is
labelled with whether that view is FED to the model this run or is a
PI-only view. The strip below the panels carries the round and GT tags.
"""
from __future__ import annotations

import io
from typing import Optional

import numpy as np
from PIL import Image, ImageDraw

STRIP_PX = 14
LABEL_PX = 12
FED = "FED TO MODEL"
NOT_FED = "PI VIEW ONLY (not fed)"
_FED_RGB = (0, 255, 0)
_NOT_FED_RGB = (255, 80, 80)


def _panel(png: bytes, title: str, fed: bool, size: Optional[tuple[int, int]] = None) -> Image.Image:
    img = Image.open(io.BytesIO(png)).convert("RGB")
    if size is not None and img.size != size:
        img = img.resize(size)
    out = Image.new("RGB", (img.width, img.height + LABEL_PX))
    out.paste(img, (0, LABEL_PX))
    ImageDraw.Draw(out).text((2, 0), f"{title}: {FED if fed else NOT_FED}",
                             fill=_FED_RGB if fed else _NOT_FED_RGB)
    return out


def compose_frame(front_png: bytes, top_png: Optional[bytes], tag: str,
                  front_fed: bool = True, top_fed: bool = False) -> np.ndarray:
    """One GIF frame: [front | top] panels, each labelled fed / not fed, plus a tag strip."""
    panels = [_panel(front_png, "FRONT", front_fed)]
    if top_png:
        panels.append(_panel(top_png, "TOP", top_fed, size=(panels[0].width, panels[0].height - LABEL_PX)))
    w = sum(p.width for p in panels)
    h = max(p.height for p in panels)
    im = Image.new("RGB", (w, h + STRIP_PX))
    x = 0
    for p in panels:
        im.paste(p, (x, 0))
        x += p.width
    ImageDraw.Draw(im).text((2, h + 2), tag, fill=(255, 255, 0))
    return np.asarray(im)
