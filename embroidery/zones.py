"""Zone-based guide rendering.

A needle-painting guide isn't a per-pixel colour map: it's a set of
meaningful *zones* (feather groups, body parts) that each get filled with
one or two threads, worked in a particular stitch *direction*. Colour
clustering can't infer those zones, so they're authored by hand in
``work/zones.json`` (grouping the draft colour regions, adding stitch
directions and any fine hand-drawn details like the eye and beak).

This module turns that authored file into every zone-aware asset:

* ``lineart.svg``  — the trace pattern: clean zone outlines, faint
  stitch-direction guides, and hand-drawn detail lines (eye, beak).
* ``zonemap.svg``  — the fill map: each zone flat-filled in its DMC
  colour, labelled with the code, with blue stitch-direction arrows.
* per-zone masks + work order, consumed by ``steps.py``.

zones.json schema::

    {
      "details": [                         # hand-drawn fine features
        {"type": "circle", "cx", "cy", "r"},
        {"type": "path", "d": "M.. L.. Z"},
        {"type": "line", "x1","y1","x2","y2"}
      ],
      "zones": [
        {"id": "belly", "name": "Yellow belly",
         "regions": [39],                   # draft regions that compose it
         "dmc": "729", "blend": ["741"],    # primary + optional blend threads
         "stitch": "long and short",
         "direction": "rows curving down and around the breast",
         "arrows": [[x1,y1,x2,y2, ...], ...],  # polyline guides (image px)
         "order": 10}
      ]
    }
"""

from __future__ import annotations

import json
import math

import numpy as np

from . import dmc
from .project import Project
from .vectorize import _region_rings
from .svg import _d


def _load(project: Project):
    doc = json.loads((project.work_dir / "paths.json").read_text())
    zdoc = json.loads((project.work_dir / "zones.json").read_text())
    labels = np.load(project.work_dir / "region_labels.npy")
    return doc, zdoc, labels


def _zone_rings(mask, mm_per_px, project):
    tol_px = project.simplify_mm / mm_per_px
    return _region_rings(mask, tol_px, min_area_px=2.0 / (mm_per_px**2),
                         smooth_iterations=project.smooth_iterations)


def compute(project: Project):
    """Return ordered list of zones enriched with rings, centroid, hex."""
    doc, zdoc, labels = _load(project)
    mm_per_px = doc["mm_per_px"]
    zones = sorted(zdoc["zones"], key=lambda z: z["order"])
    for z in zones:
        mask = np.isin(labels, z["regions"])
        z["_mask"] = mask
        z["_rings"] = _zone_rings(mask, mm_per_px, project)
        ys, xs = np.nonzero(mask)
        if xs.size:
            z["_centroid"] = (float(xs.mean()), float(ys.mean()))
        elif z.get("label_at"):
            z["_centroid"] = tuple(z["label_at"])
        else:
            z["_centroid"] = None  # nothing to fill or label (e.g. drawn detail)
        z["_hex"] = dmc.by_code(z["dmc"]).hex
    return doc, zdoc, zones


# --------------------------------------------------------------------------- #
#  drawing helpers
# --------------------------------------------------------------------------- #
def _arrow(points, stroke, sw, head=9.0):
    """Polyline with an arrowhead on the final segment."""
    pts = list(zip(points[0::2], points[1::2]))
    d = "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in pts)
    (x0, y0), (x1, y1) = pts[-2], pts[-1]
    ang = math.atan2(y1 - y0, x1 - x0)
    a1, a2 = ang + math.radians(150), ang - math.radians(150)
    hx1, hy1 = x1 + head * math.cos(a1), y1 + head * math.sin(a1)
    hx2, hy2 = x1 + head * math.cos(a2), y1 + head * math.sin(a2)
    return (
        f'<path d="{d}" fill="none" stroke="{stroke}" stroke-width="{sw:.2f}" '
        f'stroke-linecap="round" stroke-linejoin="round"/>'
        f'<path d="M {hx1:.1f} {hy1:.1f} L {x1:.1f} {y1:.1f} L {hx2:.1f} {hy2:.1f}" '
        f'fill="none" stroke="{stroke}" stroke-width="{sw:.2f}" '
        'stroke-linecap="round" stroke-linejoin="round"/>'
    )


def _details_svg(details, stroke, sw):
    out = []
    for d in details:
        if d["type"] == "circle":
            fill = d.get("fill", "none")
            out.append(
                f'<circle cx="{d["cx"]}" cy="{d["cy"]}" r="{d["r"]}" '
                f'fill="{fill}" stroke="{stroke}" stroke-width="{sw:.2f}"/>'
            )
        elif d["type"] == "path":
            fill = d.get("fill", "none")
            out.append(
                f'<path d="{d["d"]}" fill="{fill}" stroke="{stroke}" '
                f'stroke-width="{sw:.2f}" stroke-linejoin="round"/>'
            )
        elif d["type"] == "line":
            out.append(
                f'<line x1="{d["x1"]}" y1="{d["y1"]}" x2="{d["x2"]}" '
                f'y2="{d["y2"]}" stroke="{stroke}" stroke-width="{sw:.2f}" '
                'stroke-linecap="round"/>'
            )
    return "".join(out)


def _svg_open(doc, extra=""):
    w, h = doc["image_size"]
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
        f'width="{w}" height="{h}" {extra}>'
    )


# --------------------------------------------------------------------------- #
#  renderers
# --------------------------------------------------------------------------- #
def trace_svg(doc, zdoc, zones):
    """The trace pattern: zone outlines + faint direction guides + details."""
    mm_per_px = doc["mm_per_px"]
    sw = 0.35 / mm_per_px
    guide_sw = 0.22 / mm_per_px
    out = [_svg_open(doc), '<rect width="100%" height="100%" fill="#ffffff"/>']

    # faint stitch-direction guides first (under the outlines)
    out.append('<g opacity="0.35">')
    for z in zones:
        for arr in z.get("arrows", []):
            out.append(_arrow(arr, "#555", guide_sw))
    out.append("</g>")

    # zone outlines
    out.append(f'<g fill="none" stroke="#1a1a1a" stroke-width="{sw:.2f}" '
               'stroke-linejoin="round">')
    for z in zones:
        if z["_rings"]:
            out.append(f'<path data-zone="{z["id"]}" d="{_d(z["_rings"])}" '
                       'fill-rule="evenodd"/>')
    out.append("</g>")

    # hand-drawn detail features (eye, beak, ...)
    out.append(_details_svg(zdoc.get("details", []), "#1a1a1a", sw))
    out.append("</svg>")
    return "".join(out)


def zonemap_svg(doc, zdoc, zones):
    """The fill map: flat DMC fills, code labels, blue direction arrows."""
    w, h = doc["image_size"]
    mm_per_px = doc["mm_per_px"]
    sw = 0.3 / mm_per_px
    arrow_sw = 0.4 / mm_per_px
    font = max(w * 0.022, 13)
    out = [_svg_open(doc), '<rect width="100%" height="100%" fill="#faf8f4"/>']

    # fills
    for z in zones:
        if not z["_rings"]:
            continue
        out.append(
            f'<path data-zone="{z["id"]}" d="{_d(z["_rings"])}" '
            f'fill="{z["_hex"]}" fill-rule="evenodd" stroke="#00000030" '
            f'stroke-width="{sw:.2f}"/>'
        )

    # direction arrows (blue, like the originals' stitch guidelines)
    out.append('<g>')
    for z in zones:
        for arr in z.get("arrows", []):
            out.append(_arrow(arr, "#2b48c8", arrow_sw))
    out.append("</g>")

    # detail features
    out.append(_details_svg(zdoc.get("details", []), "#1a1a1a", sw))

    # code labels on a small chip at each zone centroid
    for z in zones:
        if z["_centroid"] is None:
            continue
        cx, cy = z["_centroid"]
        code = z["dmc"]
        tw = len(code) * font * 0.62 + 10
        out.append(
            f'<g><rect x="{cx - tw/2:.0f}" y="{cy - font*0.75:.0f}" '
            f'width="{tw:.0f}" height="{font*1.5:.0f}" rx="3" '
            f'fill="#ffffffcc" stroke="#333" stroke-width="1"/>'
            f'<text x="{cx:.0f}" y="{cy + font*0.35:.0f}" text-anchor="middle" '
            f'font-family="Helvetica,Arial" font-weight="bold" '
            f'font-size="{font:.0f}" fill="#111">{code}</text></g>'
        )
    out.append("</svg>")
    return "".join(out)


def run(project: Project) -> dict:
    doc, zdoc, zones = compute(project)
    (project.work_dir / "lineart.svg").write_text(trace_svg(doc, zdoc, zones))
    (project.work_dir / "zonemap.svg").write_text(zonemap_svg(doc, zdoc, zones))

    # persist a lightweight zone order + mask index for steps.py
    order = [
        {"id": z["id"], "name": z["name"], "dmc": z["dmc"],
         "blend": z.get("blend", []), "stitch": z["stitch"],
         "regions": z["regions"], "order": z["order"]}
        for z in zones
    ]
    (project.work_dir / "zone_order.json").write_text(json.dumps(order, indent=2))

    from .render import svgs_to_pngs
    svgs_to_pngs([
        (project.work_dir / "lineart.svg", project.work_dir / "lineart.png", 900),
        (project.work_dir / "zonemap.svg", project.work_dir / "zonemap.png", 1100),
    ])
    return {"zones": len(zones)}
