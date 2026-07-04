"""Stage 2: flat stitchable regions.

Quantizes at the chosen K, labels connected components, then enforces the
physical minimum region size for the chosen hoop: anything too small to
stitch is merged into its dominant neighbour, except small round spots
which become french-knot dots (a house-style feature of the guides).
"""

from __future__ import annotations

import json

import numpy as np
from PIL import Image
from scipy.ndimage import binary_dilation
from skimage import measure
from skimage.color import deltaE_ciede2000, rgb2lab
from skimage.segmentation import find_boundaries

from .analyze import _quantize
from .imageio import load_for_project
from .project import Project

DOT_MIN_MM2 = 0.4  # below this even a french knot won't read; always merge
DOT_ROUNDNESS = 0.55  # 4*pi*A/P^2 threshold for "this is a dot"
PAPER_DE_BG = 8.0  # region this close to the paper colour at the border = bg


def _dominant_neighbor(labels: np.ndarray, region_mask: np.ndarray, exclude: int) -> int:
    ring = binary_dilation(region_mask) & ~region_mask
    vals = labels[ring]
    vals = vals[vals != exclude]
    if vals.size == 0:
        return -1
    return int(np.bincount(vals).argmax())


def run(project: Project, k: int, seed: int = 0) -> dict:
    rgb = load_for_project(project)
    h, w, _ = rgb.shape
    mm_per_px = project.mm_per_px(w, h)
    mm2_per_px = mm_per_px**2

    color_idx, centers = _quantize(rgb, k, seed=seed)
    # background=-1 so cluster 0 is a real region, not dropped as background
    labels = measure.label(color_idx, connectivity=1, background=-1)
    region_color = {}  # label -> color index
    for p in measure.regionprops(labels):
        region_color[p.label] = int(color_idx[tuple(np.round(p.coords[0]).astype(int))])

    # --- classify & merge undersized regions -----------------------------
    dots: set[int] = set()
    for _ in range(4):  # a few passes; merges can create new small regions
        changed = False
        for p in measure.regionprops(labels):
            if p.label in dots:
                continue
            area_mm2 = p.area * mm2_per_px
            if area_mm2 >= project.min_region_mm2:
                continue
            roundness = 4 * np.pi * p.area / max(p.perimeter, 1) ** 2
            if area_mm2 >= DOT_MIN_MM2 and roundness >= DOT_ROUNDNESS:
                dots.add(p.label)
                continue
            mask = labels == p.label
            tgt = _dominant_neighbor(labels, mask, p.label)
            if tgt > 0:
                labels[mask] = tgt
                changed = True
        if not changed:
            break

    # merging may have fused separate blobs of one color; relabel cleanly
    labels = measure.label(
        _relabel_by_color(labels, region_color), connectivity=1, background=-1
    )
    # rebuild color mapping after merges
    region_color = {
        p.label: int(_mode(color_idx[labels == p.label]))
        for p in measure.regionprops(labels)
    }

    # --- background detection --------------------------------------------
    # The fabric/paper is whatever colour dominates the image border —
    # pure white for digital art, cream for a scanned plate. Any region of
    # (near-)that colour touching the border is unstitched background.
    lab_centers = rgb2lab(centers.reshape(1, -1, 3) / 255.0).reshape(-1, 3)
    border_px = np.concatenate(
        [rgb[0, :], rgb[-1, :], rgb[:, 0], rgb[:, -1]]
    ).astype(float)
    paper = rgb2lab((np.median(border_px, axis=0) / 255.0).reshape(1, 1, 3)).reshape(3)
    border = np.zeros_like(labels, bool)
    border[0, :] = border[-1, :] = border[:, 0] = border[:, -1] = True
    # In scan mode the paper often shows through enclosed gaps (between tail
    # feathers, sky holes) that never touch the image border, and a graded
    # scan splits the paper into several near-identical clusters. Treat any
    # near-paper region as unstitched background wherever it sits. For flat
    # art we keep the stricter border-touch test so a legitimately white
    # element in the middle of the design isn't dropped.
    scan_mode = getattr(project, "input_kind", "flat") == "scan"
    background: set[int] = set()
    for p in measure.regionprops(labels):
        ci = region_color[p.label]
        de = float(deltaE_ciede2000(lab_centers[ci], paper))
        if de < PAPER_DE_BG and (scan_mode or border[labels == p.label].any()):
            background.add(p.label)

    # --- dot re-detection on final labels ---------------------------------
    dots = set()
    for p in measure.regionprops(labels):
        if p.label in background:
            continue
        area_mm2 = p.area * mm2_per_px
        roundness = 4 * np.pi * p.area / max(p.perimeter, 1) ** 2
        if DOT_MIN_MM2 <= area_mm2 < project.min_region_mm2 and roundness >= DOT_ROUNDNESS:
            dots.add(p.label)

    # --- outputs -----------------------------------------------------------
    regions = []
    for p in measure.regionprops(labels):
        kind = (
            "background"
            if p.label in background
            else "dot"
            if p.label in dots
            else "fill"
        )
        regions.append(
            {
                "id": int(p.label),
                "rgb": centers[region_color[p.label]].tolist(),
                "area_mm2": round(float(p.area * mm2_per_px), 2),
                "centroid": [round(float(p.centroid[1]), 1), round(float(p.centroid[0]), 1)],
                "bbox": [int(v) for v in (p.bbox[1], p.bbox[0], p.bbox[3], p.bbox[2])],
                "kind": kind,
            }
        )

    np.save(project.work_dir / "region_labels.npy", labels)
    report = {
        "k": k,
        "image_size": [w, h],
        "mm_per_px": round(mm_per_px, 5),
        "design_mm": round(project.design_mm, 1),
        "regions": sorted(regions, key=lambda r: -r["area_mm2"]),
    }
    (project.work_dir / "regions.json").write_text(json.dumps(report, indent=2))

    # preview: flat colors + white boundaries
    color_lut = np.zeros(labels.max() + 1, dtype=np.intp)
    for lbl, ci in region_color.items():
        color_lut[lbl] = ci
    preview = centers[color_lut[labels]]
    preview[find_boundaries(labels, mode="thick")] = (255, 255, 255)
    Image.fromarray(preview.astype(np.uint8)).save(
        project.work_dir / "regions_preview.png"
    )
    return report


def _relabel_by_color(labels: np.ndarray, region_color: dict[int, int]) -> np.ndarray:
    size = max(max(region_color), int(labels.max())) + 1
    lut = np.zeros(size, dtype=np.int32)
    for lbl, ci in region_color.items():
        lut[lbl] = ci + 1
    return lut[labels]


def _mode(a: np.ndarray) -> int:
    return int(np.bincount(a.ravel()).argmax())
