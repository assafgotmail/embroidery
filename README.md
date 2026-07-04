# Paint with Thread — embroidery project generator

Turns any flat illustration or sketch into a complete needle-painting
embroidery project:

1. **Trace pattern** — printable PDF at exact physical scale for your hoop,
   with a dashed cut circle and white-tack corner marks.
2. **DMC thread palette** — region colors matched perceptually (CIEDE2000)
   to DMC stranded cotton, curated to a 10–16 thread budget.
3. **Step-by-step guide** — a full PDF in the "Paint with Thread" style:
   materials, trace & transfer, stitch guide, thread colour guide with DMC
   callouts, and numbered steps with progress illustrations.

## Quick start

```bash
pip install -e .
embroider init projects/fox fox.png --title "The Clever Fox" --hoop 6
embroider analyze projects/fox          # pick K from the previews
embroider regions projects/fox --k 12
embroider palette projects/fox
embroider vectorize projects/fox
embroider pattern projects/fox
embroider mockup projects/fox
# write projects/fox/work/steps.json (see embroidery/steps.py for schema)
embroider steps projects/fox
embroider guide projects/fox
```

Outputs land in `projects/fox/output/`: the pattern PDF, the guide PDF, and
an `assets/` folder with every individual piece (SVG line art, color
mockups, palette CSV, step renders) for use in InDesign or elsewhere.

The pipeline is designed to be driven by Claude Code with artistic judgment
applied between stages — see `CLAUDE.md` and the `/new-project` skill.

## Example

`projects/toadstool/` is a complete generated example (5" hoop, 10 DMC
colors, 12 steps).
