"""Stage 8: assemble the full guide PDF and export the asset bundle."""

from __future__ import annotations

import csv
import json
import re
import shutil
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from .project import Project
from .render import html_to_pdf

TEMPLATES = Path(__file__).resolve().parent.parent / "templates"
STEPS_PER_PAGE = 4
MM2_PER_HOUR = 400.0  # calibrated so a 5" motif ~ the guides' 15-18h


def _step_html(step: dict) -> str:
    """Bold DMC codes and stitch names inside the step text."""
    text = step["text"]
    text = re.sub(r"\b(\d{3,4}|BLANC|ECRU|B5200)\b", r"<b>\1</b>", text)
    return text


def _time_estimate(project: Project, steps: dict) -> str:
    if steps.get("time_estimate"):
        return steps["time_estimate"]
    rj = json.loads((project.work_dir / "regions.json").read_text())
    area = sum(r["area_mm2"] for r in rj["regions"] if r["kind"] != "background")
    hours = area / MM2_PER_HOUR
    lo = max(round(hours * 0.85), 1)
    hi = max(round(hours * 1.15), lo + 1)
    return f"{lo}-{hi} hours"


def _hoop_display(project: Project) -> str:
    v = project.hoop_inches
    return f'{v:g}"'


def run(project: Project) -> dict:
    palette = json.loads((project.work_dir / "palette.json").read_text())
    steps = json.loads((project.work_dir / "steps.json").read_text())

    for t in palette["threads"]:
        r, g, b = t["rgb"]
        t["dark"] = (0.2126 * r + 0.7152 * g + 0.0722 * b) < 130

    step_items = []
    for s in steps["steps"]:
        step_items.append(
            {"n": s["n"], "html": _step_html(s), "png": f"step_{s['n']:02d}.png"}
        )
    step_pages = [
        step_items[i : i + STEPS_PER_PAGE]
        for i in range(0, len(step_items), STEPS_PER_PAGE)
    ]

    toc_titles = (
        ["Introduction", "Contents", "What you will need", "Tools explained",
         "How to trace and transfer", "Fill map & stitch direction",
         "Thread colour guide", "Stitch guide",
         "Stitch guide p.2", "Starting to stitch"]
        + [f"Step-by-step{'' if i == 0 else f' p.{i + 1}'}"
           for i in range(len(step_pages))]
        + ["How to finish your hoop"]
    )
    toc = [{"page": i + 2, "title": t} for i, t in enumerate(toc_titles)]

    env = Environment(loader=FileSystemLoader(TEMPLATES))
    html = env.get_template("guide.html.j2").render(
        project=project,
        palette=palette,
        assets={
            "color_mockup": "color_mockup.png",
            "color_guide": "color_guide.png",
            "zonemap": "zonemap.png",
        },
        toc=toc,
        step_pages=step_pages,
        time_estimate=_time_estimate(project, steps),
        hoop_display=_hoop_display(project),
        hoop_mm=project.hoop_mm,
    )
    html_path = project.work_dir / "guide.html"
    html_path.write_text(html)
    pdf_path = project.output_dir / f"{project.name}_guide.pdf"
    html_to_pdf(html_path, pdf_path, "11.111in", "8.333in")

    _export_assets(project, palette)
    return {"pdf": str(pdf_path), "pages": len(toc) + 1}


def _export_assets(project: Project, palette: dict) -> None:
    keep = [
        "lineart.svg", "color_mockup.png", "zonemap.svg", "zonemap.png",
        "color_guide.svg", "color_guide.png", "palette_card.png",
        "paths.json", "palette.json", "regions.json", "steps.json",
        "zones.json", "zone_order.json",
    ]
    for name in keep:
        src = project.work_dir / name
        if src.exists():
            shutil.copy2(src, project.assets_dir / name)
    for png in sorted(project.work_dir.glob("step_*.png")):
        shutil.copy2(png, project.assets_dir / png.name)

    with open(project.assets_dir / "palette.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["dmc_code", "name", "hex"])
        for t in palette["threads"]:
            w.writerow([t["code"], t["name"], t["hex"]])
