"""embroider — CLI for the Paint with Thread pipeline.

Each stage is a subcommand so the run can be inspected and re-run with
different parameters between stages (that's where the artistic judgment
happens — see CLAUDE.md).
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from .project import Project


def _load(args) -> Project:
    return Project.load(args.project)


def cmd_init(args):
    root = Path(args.project)
    src = Path(args.image)
    if not src.exists():
        sys.exit(f"image not found: {src}")
    kw = {}
    if args.kind == "scan":
        # scanned artwork: keep contours as true to the source as possible
        kw = {"input_kind": "scan", "simplify_mm": 0.18, "smooth_iterations": 1}
    p = Project.create(
        root,
        title=args.title or root.name.replace("-", " ").replace("_", " ").title(),
        source_image=src.name,
        hoop_inches=args.hoop,
        **kw,
    )
    shutil.copy2(src, p.input_dir / src.name)
    print(f"created {root}/project.json  (hoop: {p.hoop_inches:g}\", "
          f"design ~{p.design_mm:.0f}mm, kind: {p.input_kind})")


def cmd_analyze(args):
    from . import analyze

    ks = tuple(int(k) for k in args.k.split(",")) if args.k else analyze.DEFAULT_KS
    report = analyze.run(_load(args), ks=ks)
    for k, colors in report["candidates"].items():
        top = ", ".join(
            f"{tuple(c['rgb'])} {c['share']:.0%}" for c in colors[:5]
        )
        print(f"K={k}: {top} ...")
    print(f"previews in work/: analyze_k*.png")


def cmd_regions(args):
    from . import regions

    report = regions.run(_load(args), k=args.k)
    kinds = {}
    for r in report["regions"]:
        kinds[r["kind"]] = kinds.get(r["kind"], 0) + 1
    print(f"{len(report['regions'])} regions: {kinds}")
    print("review work/regions_preview.png and work/regions.json")


def cmd_palette(args):
    from . import palette

    overrides = json.loads(Path(args.overrides).read_text()) if args.overrides else None
    result = palette.run(_load(args), budget=args.budget, overrides=overrides)
    for t in result["threads"]:
        print(f"  DMC {t['code']:>6}  {t['name']:<28} {t['area_mm2']:>8.0f} mm2")
    print("review work/palette_card.png; re-run with --overrides to curate")


def cmd_vectorize(args):
    from . import vectorize

    doc = vectorize.run(_load(args))
    print(f"{len(doc['paths'])} paths -> work/lineart.svg (review/clean up)")


def cmd_pattern(args):
    from . import pattern

    info = pattern.run(_load(args))
    print(f"wrote {info['pdf']} "
          f"({'landscape' if info['landscape'] else 'portrait'}, "
          f"cut circle {info['hoop_mm']:.0f}mm)")


def cmd_mockup(args):
    from . import mockup

    mockup.run(_load(args))
    print("wrote work/color_mockup.{svg,png} and work/color_guide.{svg,png}")


def cmd_steps(args):
    from . import steps

    info = steps.run(_load(args))
    print(f"rendered {info['steps']} step illustrations")
    if info["uncovered_regions"]:
        print(f"WARNING: regions never stitched by any step: "
              f"{info['uncovered_regions']}")


def cmd_guide(args):
    from . import guide

    info = guide.run(_load(args))
    print(f"wrote {info['pdf']} ({info['pages']} pages) + output/assets/")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="embroider")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init", help="create a project workspace")
    p.add_argument("project", help="project directory (e.g. projects/fox)")
    p.add_argument("image", help="source illustration")
    p.add_argument("--title", default=None)
    p.add_argument("--hoop", type=float, default=5.0,
                   help='hoop diameter in inches (default 5)')
    p.add_argument("--kind", choices=["flat", "scan"], default="flat",
                   help="'scan' for photographed/scanned artwork: smooths "
                        "washes before quantization, detects the paper "
                        "colour as background, keeps contours truer")
    p.set_defaults(fn=cmd_init)

    for name, fn, extra in [
        ("analyze", cmd_analyze, [("--k", str, None, "comma-separated Ks")]),
        ("regions", cmd_regions, [("--k", int, 12, "number of colors")]),
        ("palette", cmd_palette, [("--budget", int, 16, "max threads"),
                                  ("--overrides", str, None,
                                   "JSON file: {'r,g,b': 'dmc_code'}")]),
        ("vectorize", cmd_vectorize, []),
        ("pattern", cmd_pattern, []),
        ("mockup", cmd_mockup, []),
        ("steps", cmd_steps, []),
        ("guide", cmd_guide, []),
    ]:
        p = sub.add_parser(name)
        p.add_argument("project")
        for flag, typ, default, hlp in extra:
            p.add_argument(flag, type=typ, default=default, help=hlp)
        p.set_defaults(fn=fn)

    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
