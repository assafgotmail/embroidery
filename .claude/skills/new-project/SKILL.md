---
name: new-project
description: Turn an illustration or sketch into a complete needle-painting embroidery project — trace pattern PDF, DMC thread palette, and step-by-step guide. Use when the user wants to create a new embroidery project from an image.
---

# New embroidery project

Turn the user's image into the three deliverables: a printable trace
pattern, a DMC palette, and a full guide PDF. Read CLAUDE.md first — it
defines the judgment points and house stitching rules this skill relies on.

## 1. Gather inputs

Ask the user (AskUserQuestion) for anything not already provided:
- **The image** — it must exist as a file on disk. Images pasted inline in
  chat do NOT reach the filesystem: if the user pasted one, ask them to
  upload it as a file attachment instead. Never redraw the image from
  memory — shape accuracy comes from the pipeline tracing the real file
  (see "Input kinds" in CLAUDE.md). For scanned/photographed artwork use
  `--kind scan` and paint out captions first. If it's an uncolored
  sketch, tell the user you'll propose a palette and get their approval
  on colors before stitching order.
- **Project title** — e.g. "The Woodland Toadstool" (used on every page).
- **Hoop size in inches** — default 5. Anything from 3 to 10 works; the
  pattern sheet flips to landscape automatically for hoops over ~7.4".

Then: `embroider init projects/<slug> <image> --title "<title>" --hoop <N>`

## 2. Run the pipeline with judgment

Follow the stage order and judgment points in CLAUDE.md:

1. `embroider analyze` — **view** the `work/analyze_k*.png` previews and
   pick K yourself. Show the user your chosen quantization preview and
   confirm it keeps everything they care about.
2. `embroider regions --k <K>` — **view** `regions_preview.png`. Fix
   slivers/false regions by editing `work/regions.json` (see CLAUDE.md).
3. `embroider palette` — sanity-check the thread list; use `--overrides`
   for corrections. Show the user the palette card and ask if they want
   substitutions (they may own specific DMC colors already).
4. `embroider vectorize` — produces draft region outlines + detail lines.
5. **Author `work/zones.json`** — the heart of the work. Group the draft
   regions into meaningful named zones (feather groups, body parts), each
   with its DMC + blend threads, stitch, direction and `arrows`; add
   `details` for fine features (eye, beak). See CLAUDE.md "Zones are the
   unit". Author `arrows`/`details` against a 0.1 coordinate-grid overlay
   of the source so they land accurately.
6. `embroider zones` — **view** `work/lineart.png` (trace) and
   `work/zonemap.png` (fill map). Iterate on zones.json until the trace is
   clean and the fill map reads clearly.
7. `embroider pattern` — verify with pdftoppm that the sheet looks right.
8. `embroider mockup` — the colour reference page (real artwork + DMC
   callouts).
9. **Author `work/steps.json`** — one step per zone (or a couple grouped),
   in work order, each step's `regions` = exactly that zone's regions so
   the illustration matches the text. Follow the house voice/rules.
10. `embroider steps` — fix any "uncovered regions" warning; spot-check a
    couple of rendered `step_*.png` against their text.
11. `embroider guide` — render several pages with pdftoppm and view them.

## 3. Deliver

Send the user (SendUserFile):
- `projects/<slug>/output/<slug>_pattern_PRINT.pdf`
- `projects/<slug>/output/<slug>_guide.pdf`

Summarize the palette (codes + names) in chat so they can shop for floss,
and note the estimated stitching time. Remind them the step photos are
rendered illustrations — after test-stitching they can swap in real
photos. Offer to iterate on the guide design (templates/guide.html.j2).
