"""Stage 6: Thread Colour Guide assets.

* ``color_mockup.svg`` — plain flat-color render of the finished design
* ``color_guide.svg`` — the same render with a swatch legend and leader
  lines from each thread's largest region to its swatch, like the
  "Thread Colour guide" page of the original PDFs.
"""

from __future__ import annotations

import json

from .project import Project
from .render import svgs_to_pngs
from .svg import color_svg, _sorted_items

LEGEND_W_FRAC = 0.42  # legend column width relative to image width


def run(project: Project) -> dict:
    doc = json.loads((project.work_dir / "paths.json").read_text())
    palette = json.loads((project.work_dir / "palette.json").read_text())
    dmc_hex = {t["code"]: t["hex"] for t in palette["threads"]}

    mockup = color_svg(doc, dmc_hex)
    (project.work_dir / "color_mockup.svg").write_text(mockup)

    guide = _guide_with_legend(doc, palette, dmc_hex)
    (project.work_dir / "color_guide.svg").write_text(guide)

    svgs_to_pngs(
        [
            (project.work_dir / "color_mockup.svg",
             project.work_dir / "color_mockup.png", 1400),
            (project.work_dir / "color_guide.svg",
             project.work_dir / "color_guide.png", 1800),
        ]
    )
    return {"threads": len(palette["threads"])}


def _largest_region_per_thread(doc: dict) -> dict[str, tuple[float, float]]:
    """thread code -> centroid (image px) of its largest region."""
    best: dict[str, tuple[float, float]] = {}
    for rid, entry in _sorted_items(doc):
        code = str(entry.get("dmc"))
        if code in best:
            continue  # _sorted_items is largest-first
        if entry["kind"] == "dot":
            cx, cy = entry["center"]
        else:
            ring = entry["rings"][0]
            cx = sum(p[0] for p in ring) / len(ring)
            cy = sum(p[1] for p in ring) / len(ring)
        best[code] = (cx, cy)
    return best


def _guide_with_legend(doc: dict, palette: dict, dmc_hex: dict) -> str:
    img_w, img_h = doc["image_size"]
    legend_w = img_w * LEGEND_W_FRAC
    total_w = img_w + legend_w
    threads = palette["threads"]
    anchors = _largest_region_per_thread(doc)

    # order legend rows by the vertical position of their anchor region to
    # keep leader lines from crossing too much
    threads = sorted(threads, key=lambda t: anchors.get(t["code"], (0, 0))[1])

    row_h = img_h / max(len(threads), 1)
    sw_h = min(row_h * 0.62, img_h * 0.05)
    font = max(img_w * 0.018, 12)

    # color_svg emits a full <svg>; nest it as an inner viewport
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {total_w:.0f} {img_h}" width="{total_w:.0f}" '
        f'height="{img_h}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<svg x="0" y="0" width="{img_w}" height="{img_h}" '
        f'viewBox="0 0 {img_w} {img_h}">{color_svg(doc, dmc_hex)}</svg>',
    ]
    lx = img_w + legend_w * 0.28
    for i, t in enumerate(threads):
        y = (i + 0.5) * row_h
        if t["code"] in anchors:
            ax, ay = anchors[t["code"]]
            out.append(
                f'<line x1="{ax:.0f}" y1="{ay:.0f}" x2="{lx:.0f}" '
                f'y2="{y:.0f}" stroke="#2b48c8" stroke-width="{img_w*0.0016:.1f}"/>'
            )
            out.append(
                f'<circle cx="{ax:.0f}" cy="{ay:.0f}" r="{img_w*0.004:.1f}" '
                'fill="#2b48c8"/>'
            )
        out.append(
            f'<rect x="{lx:.0f}" y="{y - sw_h / 2:.0f}" '
            f'width="{legend_w*0.3:.0f}" height="{sw_h:.0f}" fill="{t["hex"]}" '
            'stroke="#333" stroke-width="1"/>'
        )
        out.append(
            f'<text x="{lx + legend_w*0.36:.0f}" y="{y + font*0.35:.0f}" '
            f'font-family="Helvetica,Arial" font-size="{font:.0f}" '
            f'fill="#111">{t["code"]}</text>'
        )
    out.append("</svg>")
    return "".join(out)
