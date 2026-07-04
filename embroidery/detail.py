"""Detail / stitch-direction line extraction.

Needle-painting patterns aren't just outlines of colour blocks: the
stitcher follows the *internal* structure of the subject — feather barbs,
wing flight-feather edges, the eye, leaf veins — both to trace and to know
which way the stitches should run. We recover those lines directly from
the artwork's own drawn strokes with edge detection, then vectorize them
into clean polylines that live alongside the region outlines in the trace
pattern.
"""

from __future__ import annotations

import numpy as np
from skimage.color import deltaE_ciede2000, rgb2gray, rgb2lab
from skimage.feature import canny
from skimage.morphology import remove_small_objects, skeletonize

from .imageio import load_for_project

# 8-neighbour offsets
_NB = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def _ink_mask(rgb: np.ndarray) -> np.ndarray:
    """True where the artwork sits (not paper)."""
    lab = rgb2lab(rgb / 255.0)
    border = np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]]).astype(float)
    paper = rgb2lab((np.median(border, 0) / 255.0).reshape(1, 1, 3)).reshape(3)
    de = deltaE_ciede2000(lab, np.broadcast_to(paper, lab.shape))
    return de > 10.0


def _trace_skeleton(skel: np.ndarray, min_len: int = 6):
    """Walk a 1-px skeleton into polylines. Chains run between endpoints and
    junctions; pure loops are broken at an arbitrary pixel."""
    H, W = skel.shape
    deg = np.zeros_like(skel, np.uint8)
    ys, xs = np.nonzero(skel)
    pts = set(zip(ys.tolist(), xs.tolist()))
    for (y, x) in pts:
        d = 0
        for dy, dx in _NB:
            if (y + dy, x + dx) in pts:
                d += 1
        deg[y, x] = d

    visited_edges: set = set()
    polylines: list[list[tuple[int, int]]] = []

    def neighbours(p):
        y, x = p
        for dy, dx in _NB:
            q = (y + dy, x + dx)
            if q in pts:
                yield q

    def walk(start, second):
        chain = [start, second]
        visited_edges.add(frozenset((start, second)))
        prev, cur = start, second
        while deg[cur] == 2:
            nxts = [q for q in neighbours(cur) if q != prev]
            if not nxts:
                break
            nxt = nxts[0]
            e = frozenset((cur, nxt))
            if e in visited_edges:
                break
            visited_edges.add(e)
            chain.append(nxt)
            prev, cur = cur, nxt
        return chain

    # chains starting from endpoints/junctions
    nodes = [p for p in pts if deg[p] != 2]
    for node in nodes:
        for nb in neighbours(node):
            if frozenset((node, nb)) not in visited_edges:
                polylines.append(walk(node, nb))

    # leftover pure loops (all degree 2)
    for p in pts:
        for nb in neighbours(p):
            e = frozenset((p, nb))
            if e not in visited_edges:
                polylines.append(walk(p, nb))

    return [c for c in polylines if len(c) >= min_len]


def run(project, sigma: float | None = None, min_len_mm: float = 0.8) -> dict:
    """Extract detail lines; returns {'lines': [[[x,y],...], ...]} in image px."""
    rgb = load_for_project(project)
    gray = rgb2gray(rgb)
    ink = _ink_mask(rgb)

    if sigma is None:
        sigma = 1.6 if getattr(project, "input_kind", "flat") == "scan" else 1.1

    edges = canny(gray, sigma=sigma) & ink
    edges = remove_small_objects(edges, min_size=6)
    skel = skeletonize(edges)

    mm_per_px = project.design_mm / max(rgb.shape[1], rgb.shape[0])
    min_len_px = max(int(min_len_mm / mm_per_px), 6)

    from shapely.geometry import LineString

    lines = []
    for chain in _trace_skeleton(skel, min_len=min_len_px):
        xy = [(float(x), float(y)) for (y, x) in chain]
        ls = LineString(xy)
        if ls.length < min_len_px:
            continue
        simp = ls.simplify(max(min_len_px * 0.12, 0.8), preserve_topology=False)
        coords = [[round(x, 2), round(y, 2)] for x, y in simp.coords]
        if len(coords) >= 2:
            lines.append(coords)

    return {"lines": lines, "sigma": sigma}
