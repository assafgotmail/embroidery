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


def smooth_scan(rgb: np.ndarray) -> np.ndarray:
    """Edge-preserving smoothing for scanned/painted artwork: flattens
    watercolour washes and paper grain into coherent colour areas while
    keeping the true contours crisp, so segmentation follows the actual
    shapes of the artwork."""
    from skimage.restoration import denoise_bilateral

    out = denoise_bilateral(
        rgb.astype(np.float64) / 255.0,
        sigma_color=0.09,
        sigma_spatial=4,
        channel_axis=-1,
    )
    return (np.clip(out, 0, 1) * 255).astype(np.uint8)


def load_for_project(project) -> np.ndarray:
    """Load the project's source image with kind-appropriate preprocessing."""
    rgb = load_rgb(project.source_path)
    if getattr(project, "input_kind", "flat") == "scan":
        rgb = smooth_scan(rgb)
    return rgb
