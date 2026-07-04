# Paint with Thread — embroidery project generator

This repo turns an illustration or sketch into a complete needle-painting
embroidery project: a printable trace pattern, a DMC thread palette, and a
beginner-friendly step-by-step guide, in the style of the "Paint with
Thread" guides (Butterfly, Bumblebee, Moth, Mushroom).

## Pipeline

Every stage is an `embroider` subcommand operating on a project directory.
Run them in order; between stages, review the outputs in `work/` and apply
judgment (that's your job — the scripts are deliberately dumb about
aesthetics).

```
embroider init projects/<name> <image> --title "The ..." --hoop <inches>
embroider analyze  projects/<name>            # K candidates -> pick K
embroider regions  projects/<name> --k <K>    # segmentation -> curate
embroider palette  projects/<name> [--budget N] [--overrides file.json]
embroider vectorize projects/<name>           # -> work/lineart.svg, clean up
embroider pattern  projects/<name>            # -> output/<name>_pattern_PRINT.pdf
embroider mockup   projects/<name>            # -> colour guide assets
# author work/steps.json yourself (see below), then:
embroider steps    projects/<name>            # renders progress illustrations
embroider guide    projects/<name>            # -> output/<name>_guide.pdf + assets/
```

Use the `/new-project` skill to run the whole flow interactively.

## Input kinds: flat vs scan

`embroider init --kind scan` is for photographed/scanned artwork
(watercolour plates, painted or printed pages). It enables
edge-preserving smoothing before quantization, detects the *paper*
colour (not just white) as unstitched background, and defaults to
higher contour fidelity (`simplify_mm 0.18`, one smoothing pass).
Default `--kind flat` is for clean digital illustrations.

Scan workflow, in order:
1. The image must exist **as a file**. Images pasted inline in chat never
   reach the filesystem — ask the user to upload the file if needed.
2. **Never redraw the source from memory.** Shape accuracy comes from the
   pipeline tracing the actual image; a hand redraw loses the authentic
   contours. Redrawing is allowed only when the user explicitly asks for
   a stylized reinterpretation.
3. Paint out captions/plate numbers with the surrounding paper colour
   (PIL: sample the median colour next to the text box, fill the box)
   before `init`. Prefer painting-over to cropping — crops can clip art.
4. Expect more regions and a noisier palette than flat art: blurred edges
   soften blacks (310 may match to 3799 etc.) and split washes into
   bands. Curate harder: use `--overrides` to snap colors back to what
   the artwork means, not what the scan faded them to.

## Judgment points (do these, don't skip)

1. **Pick K** (after `analyze`): view `work/analyze_k*.png`. Choose the
   smallest K where every meaningful element of the design keeps its own
   color. Flat illustrations usually want K 10–14.
2. **Curate regions** (after `regions`): view `work/regions_preview.png`
   and `work/regions.json`. Watch for: quantization slivers along edges
   (merge or mark `"kind": "background"` by editing regions.json);
   enclosed white areas that are really unstitched fabric (mark
   background); tiny features that should be french-knot dots. Re-run
   downstream stages after editing.
3. **Curate the palette** (after `palette`): the matcher is perceptual but
   not artistic. Check value contrast between adjacent regions, prefer
   colors from DMC lines the user already owns when known, and pass
   `--overrides overrides.json` (`{"r,g,b": "dmc_code"}`) to fix any
   mismatch. 10–16 threads is the house norm.
4. **Clean the line art** (after `vectorize`): open `work/lineart.svg`.
   Every closed shape must be traceable with a pencil: merge noisy paths,
   delete micro-detail, smooth jagged curves. Edit the SVG directly (paths
   carry `data-region` ids) or adjust `SIMPLIFY_MM` in vectorize.py.
5. **Author `work/steps.json`**: you write this by hand — it's the soul of
   the guide. See the schema in `embroidery/steps.py` and the house rules
   below. `embroider steps` warns about regions no step covers.

## House stitching rules (distilled from the four original guides)

- **Order of work**: background/secondary elements first (flora, ground,
  sparkles), then the main subject. Within the subject: outlines first,
  then fills, dark before light where colors blend. Focal details (eyes,
  head, antennae) come last.
- **Stitches**: long and short stitch for every fill; split stitch for
  outlines and thin lines (also stitched *around* region edges before
  filling, to keep edges crisp); satin stitch for small neat shapes
  (spots, leaves); french knots for dots (two strands, wound twice).
- **Strands**: one strand default; two allowed for speedy large dark
  areas and french knots. Warn that >1 strand can look 'lumpy'.
- **Direction**: stitch rows follow the natural curve of the element
  (fur, petals, wing veins). Mention direction explicitly in steps for
  curved or rounded elements.
- **Voice**: warm, encouraging, first person, British spelling
  ("colour"). Steps name the DMC code and stitch every time. Sprinkle
  practical tips (eye breaks, washing hands, pegs for thread storage).
- **Step granularity**: one step ≈ one color in one area (like "fill the
  flower with 3821 halfway down each petal"). 12–32 steps is the norm.

## Physical scale

Hoop size is set at `init` (default 5") and drives everything: the design
occupies ~75% of the hoop diameter; regions smaller than
`min_region_mm2` (default 4 mm²) on fabric get merged or knotted; the
PRINT pattern's dashed cut circle is exactly the hoop diameter and must be
printed at 100% scale. Hoops wider than ~7.4" flip the pattern sheet to
A4 landscape automatically.

## Environment notes

- Playwright renders all PDFs/PNGs; Chromium is preinstalled — never run
  `playwright install` (render.py already falls back to
  `/opt/pw-browsers/chromium`).
- `data/dmc_colors.csv` is the DMC↔RGB table (454 colors). DMC codes are
  strings — some are non-numeric (BLANC, ECRU, B5200).
- `projects/*/work/` is gitignored scratch; `projects/*/output/` is the
  deliverable and is committed.
