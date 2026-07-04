"""Image loading helpers shared by pipeline stages."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

MAX_WORKING_PX = 1200


def load_rgb(path: str | Path, max_px: int = MAX_WORKING_PX) -> np.ndarray:
    """Load an image as RGB uint8 on a white background, downscaled so the
    longest side is at most ``max_px`` (keeps k-means and contours fast and
    matches the level of detail that is actually stitchable)."""
    img = Image.open(path)
    if img.mode in ("RGBA", "LA", "PA") or (
        img.mode == "P" and "transparency" in img.info
    ):
        img = img.convert("RGBA")
        bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
        img = Image.alpha_composite(bg, img)
    img = img.convert("RGB")
    w, h = img.size
    if max(w, h) > max_px:
        s = max_px / max(w, h)
        img = img.resize((round(w * s), round(h * s)), Image.LANCZOS)
    return np.asarray(img, dtype=np.uint8)
