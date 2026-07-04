"""Stage 4: vectorize region boundaries into smooth closed paths.

Writes ``paths.json`` (region id -> list of closed polygons in image-pixel
coordinates) which every downstream renderer (pattern, mockup, steps)
shares, plus ``lineart.svg`` for review/cleanup.
"""

from __future__ import annotations

import json

import numpy as np
from shapely.geometry import Polygon
from skimage import measure

from .project import Project
from .svg import lineart_svg

SIMPLIFY_MM = 0.25  # positional tolerance on fabric; below pencil-line width
MIN_RING_MM2 = 0.5  # drop micro-rings that survive as noise


def _chaikin(pts: np.ndarray, iterations: int = 2) -> np.ndarray:
    """Corner-cutting smoothing for a closed polygon (N,2)."""
    for _ in range(iterations):
        p = pts
        q = np.roll(p, -1, axis=0)
        pts = np.empty((len(p) * 2, 2))
        pts[0::2] = 0.75 * p + 0.25 * q
        pts[1::2] = 0.25 * p + 0.75 * q
    return pts


def _region_rings(mask: np.ndarray, tol_px: float, min_area_px: float):
    padded = np.pad(mask.astype(float), 1)
    rings = []
    for contour in measure.find_contours(padded, 0.5):
        xy = contour[:, ::-1] - 1.0  # (row,col) -> (x,y), unpad
        if len(xy) < 4:
            continue
        poly = Polygon(xy)
        if not poly.is_valid:
            poly = poly.buffer(0)
        if poly.is_empty or poly.area < min_area_px:
            continue
        polys = poly.geoms if poly.geom_type == "MultiPolygon" else [poly]
        for p in polys:
            if p.area < min_area_px:
                continue
            simplified = p.exterior.simplify(tol_px, preserve_topology=True)
            pts = np.asarray(simplified.coords)[:-1]
            if len(pts) >= 3:
                rings.append(_chaikin(pts).round(2).tolist())
    return rings


def run(project: Project) -> dict:
    rj = json.loads((project.work_dir / "regions.json").read_text())
    labels = np.load(project.work_dir / "region_labels.npy")
    mm_per_px = rj["mm_per_px"]
    tol_px = SIMPLIFY_MM / mm_per_px
    min_area_px = MIN_RING_MM2 / (mm_per_px**2)

    paths: dict[str, dict] = {}
    for r in rj["regions"]:
        if r["kind"] == "background":
            continue
        rid = r["id"]
        if r["kind"] == "dot":
            # dots become circles in every renderer; store centre + radius
            area_px = r["area_mm2"] / (mm_per_px**2)
            radius = float(np.sqrt(area_px / np.pi))
            paths[str(rid)] = {
                "kind": "dot",
                "center": r["centroid"],
                "radius_px": round(radius, 2),
                "dmc": r.get("dmc"),
                "rgb": r["rgb"],
            }
            continue
        rings = _region_rings(labels == rid, tol_px, min_area_px)
        if not rings:
            continue
        paths[str(rid)] = {
            "kind": "fill",
            "rings": rings,
            "dmc": r.get("dmc"),
            "rgb": r["rgb"],
        }

    doc = {
        "image_size": rj["image_size"],
        "mm_per_px": mm_per_px,
        "paths": paths,
    }
    (project.work_dir / "paths.json").write_text(json.dumps(doc))

    svg = lineart_svg(doc)
    (project.work_dir / "lineart.svg").write_text(svg)
    return doc
