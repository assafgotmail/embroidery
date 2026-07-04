"""Stage 1: color analysis. Quantize the source image at several K so a
human (or Claude) can choose how many flat colors the design needs."""

from __future__ import annotations

import json

import numpy as np
from PIL import Image
from skimage.color import rgb2lab, lab2rgb
from sklearn.cluster import KMeans

from .imageio import load_for_project
from .project import Project

DEFAULT_KS = (8, 12, 16, 20)


def _quantize(rgb: np.ndarray, k: int, seed: int = 0):
    """K-means in CIELAB. Returns (labels HxW, centers_rgb Kx3 uint8)."""
    h, w, _ = rgb.shape
    lab = rgb2lab(rgb / 255.0).reshape(-1, 3)
    km = KMeans(n_clusters=k, n_init=4, random_state=seed).fit(lab)
    centers_rgb = np.clip(
        lab2rgb(km.cluster_centers_.reshape(1, -1, 3)).reshape(-1, 3) * 255,
        0,
        255,
    ).astype(np.uint8)
    return km.labels_.reshape(h, w), centers_rgb


def _swatch_strip(centers: np.ndarray, shares: np.ndarray, sw: int = 80) -> Image.Image:
    order = np.argsort(-shares)
    strip = np.zeros((sw, sw * len(centers), 3), dtype=np.uint8)
    for i, ci in enumerate(order):
        strip[:, i * sw : (i + 1) * sw] = centers[ci]
    return Image.fromarray(strip)


def run(project: Project, ks=DEFAULT_KS) -> dict:
    rgb = load_for_project(project)
    h, w, _ = rgb.shape
    report = {"image_size": [w, h], "candidates": {}}

    for k in ks:
        labels, centers = _quantize(rgb, k)
        shares = np.bincount(labels.ravel(), minlength=k) / labels.size
        quant = centers[labels]
        Image.fromarray(quant).save(project.work_dir / f"analyze_k{k}.png")
        _swatch_strip(centers, shares).save(
            project.work_dir / f"analyze_k{k}_swatches.png"
        )
        report["candidates"][str(k)] = [
            {"rgb": centers[i].tolist(), "share": round(float(shares[i]), 4)}
            for i in np.argsort(-shares)
        ]

    out = project.work_dir / "analyze.json"
    out.write_text(json.dumps(report, indent=2))
    return report
