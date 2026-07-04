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

Each step gets ``step_NN.svg/png`` in work/: regions completed so far in
full color, everything else as gray trace lines — the same view as the
progress photos in the original guides.
"""

from __future__ import annotations

import json

from .project import Project
from .render import svgs_to_pngs
from .svg import color_svg

STEP_PNG_W = 700


def run(project: Project) -> dict:
    doc = json.loads((project.work_dir / "paths.json").read_text())
    palette = json.loads((project.work_dir / "palette.json").read_text())
    steps = json.loads((project.work_dir / "steps.json").read_text())
    dmc_hex = {t["code"]: t["hex"] for t in palette["threads"]}

    jobs = []
    done: set[str] = set()
    for step in steps["steps"]:
        done |= {str(r) for r in step.get("regions", [])}
        svg = color_svg(doc, dmc_hex, done_ids=set(done))
        n = step["n"]
        svg_path = project.work_dir / f"step_{n:02d}.svg"
        svg_path.write_text(svg)
        jobs.append((svg_path, project.work_dir / f"step_{n:02d}.png", STEP_PNG_W))

    svgs_to_pngs(jobs)

    all_ids = {
        rid for rid, e in doc["paths"].items()
    }
    missing = sorted(all_ids - done, key=lambda s: int(s))
    return {"steps": len(steps["steps"]), "uncovered_regions": missing}
