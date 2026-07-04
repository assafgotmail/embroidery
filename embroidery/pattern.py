"""Stage 5: the printable trace pattern ("PRINT" sheet).

A4 page with the line art at exact physical size for the chosen hoop, a
dotted cut circle the size of the hoop, four corner tack marks and a faint
FRONT label — the same sheet format as the original guides. Falls back to
A4 landscape when a large hoop's circle won't fit portrait width.
"""

from __future__ import annotations

import json

from .project import Project
from .render import html_to_pdf
from .svg import lineart_svg

A4 = (210.0, 297.0)
PAGE_MARGIN_MM = 10.0

PAGE_TMPL = """<!doctype html><html><head><meta charset="utf-8"><style>
  * {{ margin: 0; padding: 0; }}
  @page {{ size: {page_w}mm {page_h}mm; margin: 0; }}
  body {{ width: {page_w}mm; height: {page_h}mm; position: relative;
         font-family: Helvetica, Arial, sans-serif; }}
  .circle {{ position: absolute; left: {cx}mm; top: {cy}mm;
    width: {hoop}mm; height: {hoop}mm; margin-left: -{hoop_r}mm;
    margin-top: -{hoop_r}mm; border: 0.4mm dashed #555; border-radius: 50%; }}
  .art {{ position: absolute; left: {cx}mm; top: {cy}mm;
    width: {art_w}mm; height: {art_h}mm; margin-left: -{art_hw}mm;
    margin-top: -{art_hh}mm; }}
  .art svg {{ width: 100%; height: 100%; }}
  .front {{ position: absolute; left: {cx}mm; top: {front_y}mm;
    transform: translateX(-50%); color: #b9c4f2; font-size: 5mm;
    letter-spacing: 1mm; font-weight: bold; }}
  .tack {{ position: absolute; width: 6mm; height: 6mm;
    border-color: #999; border-style: solid; }}
  .title {{ position: absolute; left: 50%; transform: translateX(-50%);
    top: {title_y}mm; font-size: 3.5mm; color: #333; text-align: center; }}
  .note {{ position: absolute; left: 50%; transform: translateX(-50%);
    top: {note_y}mm; font-size: 2.8mm; color: #888; text-align: center; }}
</style></head><body>
  <div class="circle"></div>
  {tacks}
  <div class="front">FRONT</div>
  <div class="art">{svg}</div>
  <div class="title">{title} &mdash; trace pattern for a {hoop_in}&Prime; hoop</div>
  <div class="note">Print at 100% scale (no &ldquo;fit to page&rdquo;).
    The dashed circle should measure {hoop_mm}mm across.</div>
</body></html>"""

TACK = ('<div class="tack" style="left:{x}mm; top:{y}mm; '
        'border-width:{bw};"></div>')


def run(project: Project) -> dict:
    doc = json.loads((project.work_dir / "paths.json").read_text())
    img_w, img_h = doc["image_size"]
    mm_per_px = doc["mm_per_px"]
    art_w, art_h = img_w * mm_per_px, img_h * mm_per_px

    hoop = project.hoop_mm
    landscape = hoop + 2 * PAGE_MARGIN_MM > A4[0]
    page_w, page_h = (A4[1], A4[0]) if landscape else A4

    cx = page_w / 2
    cy = PAGE_MARGIN_MM + hoop / 2 + 8
    r = hoop / 2

    # tack corners: L-shaped marks on the circle's bounding square corners
    tacks = []
    for dx, dy, bw in (
        (-r, -r, "0.4mm 0 0 0.4mm"),
        (r - 6, -r, "0.4mm 0.4mm 0 0"),
        (-r, r - 6, "0 0 0.4mm 0.4mm"),
        (r - 6, r - 6, "0 0.4mm 0.4mm 0"),
    ):
        tacks.append(TACK.format(x=cx + dx, y=cy + dy, bw=bw))

    html = PAGE_TMPL.format(
        page_w=page_w,
        page_h=page_h,
        cx=cx,
        cy=cy,
        hoop=hoop,
        hoop_r=r,
        art_w=art_w,
        art_h=art_h,
        art_hw=art_w / 2,
        art_hh=art_h / 2,
        front_y=cy - r + 4,
        tacks="".join(tacks),
        svg=lineart_svg(doc),
        title=project.title,
        hoop_in=f"{project.hoop_inches:g}",
        hoop_mm=f"{hoop:.0f}",
        title_y=cy + r + 8,
        note_y=cy + r + 14,
    )
    html_path = project.work_dir / "pattern_PRINT.html"
    html_path.write_text(html)
    pdf_path = project.output_dir / f"{project.name}_pattern_PRINT.pdf"
    html_to_pdf(html_path, pdf_path, f"{page_w}mm", f"{page_h}mm")
    return {"pdf": str(pdf_path), "landscape": landscape, "hoop_mm": hoop}
