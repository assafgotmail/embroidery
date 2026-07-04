"""Stage 7: render progress illustrations for a Claude-authored steps.json.

steps.json schema::

    {
      "time_estimate": "10-12 hours",          # optional, else computed
      "steps": [
        {"n": 1,
         "text": "Outline the lower left petal with split stitch ...",
         "dmc": "3821",
         "stitch": "split stitch",
         "regions": [4, 7]},
        ...
      ]
    }

Each step reveals the *real artwork* within the regions completed so far,
laid over the grey trace lines on the 'fabric' — so the shading and
blending build up exactly as they will on the hoop, rather than as flat
colour blocks.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import binary_dilation

from .imageio import load_for_project
from .project import Project
from .render import svgs_to_pngs

STEP_PNG_W = 760
FABRIC = (250, 248, 244)


def _lineart_base(project: Project, size) -> Image.Image:
    """Grey trace lines on fabric, at pixel ``size`` (w, h)."""
    svg = project.work_dir / "lineart.svg"
    png = project.work_dir / "_lineart_base.png"
    svgs_to_pngs([(svg, png, size[0])])
    la = Image.open(png).convert("RGBA").resize(size)
    # recolour black strokes to soft grey, drop pure white to transparent
    arr = np.asarray(la).astype(float)
    lum = arr[..., :3].mean(2)
    out = np.zeros((size[1], size[0], 4), np.uint8)
    ink = lum < 160
    out[..., :3] = (120, 120, 120)
    out[..., 3] = np.where(ink, 210, 0)
    return Image.fromarray(out)


def run(project: Project) -> dict:
    doc = json.loads((project.work_dir / "paths.json").read_text())
    steps = json.loads((project.work_dir / "steps.json").read_text())
    img_w, img_h = doc["image_size"]
    scale = STEP_PNG_W / img_w
    size = (STEP_PNG_W, round(img_h * scale))

    art = Image.fromarray(load_for_project(project)).resize(size)
    labels = np.load(project.work_dir / "region_labels.npy")
    labels_img = np.asarray(
        Image.fromarray(labels.astype(np.int32), mode="I").resize(
            size, Image.NEAREST
        )
    )
    base = _lineart_base(project, size)

    all_ids = {rid for rid in doc["paths"]}
    done: set[str] = set()
    jobs_done = []
    for step in steps["steps"]:
        done |= {str(r) for r in step.get("regions", [])}
        done_int = {int(r) for r in done}
        mask = np.isin(labels_img, list(done_int))
        # soften the reveal edge so partially-stitched areas don't look cut out
        mask = binary_dilation(mask, iterations=1)

        canvas = Image.new("RGB", size, FABRIC)
        canvas.paste(art, (0, 0), Image.fromarray((mask * 255).astype(np.uint8)))
        canvas = canvas.convert("RGBA")
        canvas.alpha_composite(base)
        n = step["n"]
        out = project.work_dir / f"step_{n:02d}.png"
        canvas.convert("RGB").save(out)
        jobs_done.append(n)

    missing = sorted(all_ids - done, key=lambda s: int(s))
    return {"steps": len(steps["steps"]), "uncovered_regions": missing}
