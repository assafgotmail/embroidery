"""Stage 3: DMC palette. Match region colors to threads, collapse
near-duplicates until the palette fits the thread budget, and annotate
regions.json with the chosen DMC code per region."""

from __future__ import annotations

import json

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from . import dmc
from .project import Project

DEFAULT_BUDGET = 16
MERGE_DE = 4.0  # threads closer than this are indistinguishable in floss

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]


def _font(size: int):
    for p in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()


def run(project: Project, budget: int = DEFAULT_BUDGET, overrides: dict | None = None) -> dict:
    """``overrides`` maps "r,g,b" region color -> DMC code, for Claude/user
    curation after reviewing the automatic match."""
    rj = json.loads((project.work_dir / "regions.json").read_text())
    stitch_regions = [r for r in rj["regions"] if r["kind"] != "background"]

    colors = sorted({tuple(r["rgb"]) for r in stitch_regions})
    area_by_color: dict[tuple, float] = {}
    for r in stitch_regions:
        c = tuple(r["rgb"])
        area_by_color[c] = area_by_color.get(c, 0.0) + r["area_mm2"]

    overrides = overrides or {}
    matches = dmc.nearest(np.array(colors), k=3)
    chosen: dict[tuple, dmc.Thread] = {}
    for c, cands in zip(colors, matches):
        key = ",".join(map(str, c))
        if key in overrides:
            chosen[c] = dmc.by_code(overrides[key])
        else:
            chosen[c] = cands[0][0]

    # --- collapse near-duplicate threads, then enforce the budget ---------
    def _merge_pass(max_de: float) -> bool:
        threads = sorted(set(chosen.values()), key=lambda t: t.code)
        best = None
        for i, a in enumerate(threads):
            for b in threads[i + 1 :]:
                de = dmc.delta_e(a.rgb, b.rgb)
                if de <= max_de and (best is None or de < best[0]):
                    best = (de, a, b)
        if best is None:
            return False
        _, a, b = best
        area_a = sum(v for c, v in area_by_color.items() if chosen[c] == a)
        area_b = sum(v for c, v in area_by_color.items() if chosen[c] == b)
        keep, drop = (a, b) if area_a >= area_b else (b, a)
        for c in chosen:
            if chosen[c] == drop:
                chosen[c] = keep
        return True

    while _merge_pass(MERGE_DE):
        pass
    while len(set(chosen.values())) > budget and _merge_pass(100.0):
        pass

    # --- annotate regions and write palette -------------------------------
    for r in rj["regions"]:
        c = tuple(r["rgb"])
        r["dmc"] = chosen[c].code if c in chosen else None
    (project.work_dir / "regions.json").write_text(json.dumps(rj, indent=2))

    threads = sorted(
        set(chosen.values()),
        key=lambda t: -sum(v for c, v in area_by_color.items() if chosen[c] == t),
    )
    palette = {
        "budget": budget,
        "threads": [
            {
                "code": t.code,
                "name": t.name,
                "hex": t.hex,
                "rgb": list(t.rgb),
                "area_mm2": round(
                    sum(v for c, v in area_by_color.items() if chosen[c] == t), 1
                ),
                "source_colors": [list(c) for c in colors if chosen[c] == t],
            }
            for t in threads
        ],
    }
    (project.work_dir / "palette.json").write_text(json.dumps(palette, indent=2))
    _palette_card(palette).save(project.work_dir / "palette_card.png")
    return palette


def _palette_card(palette: dict) -> Image.Image:
    rows = palette["threads"]
    rh, w = 56, 460
    img = Image.new("RGB", (w, rh * len(rows) + 16), "white")
    d = ImageDraw.Draw(img)
    f_big, f_small = _font(20), _font(14)
    for i, t in enumerate(rows):
        y = 8 + i * rh
        d.rectangle([16, y, 116, y + rh - 10], fill=tuple(t["rgb"]), outline="black")
        d.text((132, y + 4), f"DMC {t['code']}", font=f_big, fill="black")
        d.text((132, y + 28), t["name"], font=f_small, fill=(90, 90, 90))
    return img
