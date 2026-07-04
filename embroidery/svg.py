"""SVG renderers built on paths.json — the shared geometry document."""

from __future__ import annotations


def _d(rings: list[list[list[float]]]) -> str:
    parts = []
    for ring in rings:
        pts = " L ".join(f"{x:.2f} {y:.2f}" for x, y in ring)
        parts.append(f"M {pts} Z")
    return " ".join(parts)


def _luma(rgb) -> float:
    r, g, b = rgb
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _sorted_items(doc: dict):
    """Large fills first so smaller details render on top."""

    def area(entry):
        if entry["kind"] == "dot":
            return entry["radius_px"] ** 2
        return sum(
            abs(
                sum(
                    x1 * y2 - x2 * y1
                    for (x1, y1), (x2, y2) in zip(ring, ring[1:] + ring[:1])
                )
            )
            / 2
            for ring in entry["rings"]
        )

    return sorted(doc["paths"].items(), key=lambda kv: -area(kv[1]))


def _svg_open(doc: dict, extra: str = "") -> str:
    w, h = doc["image_size"]
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
        f'width="{w}" height="{h}" {extra}>'
    )


def lineart_svg(doc: dict, stroke: str = "#1a1a1a", stroke_mm: float = 0.35) -> str:
    """Trace-pattern line art: every region outlined, dots as filled circles."""
    sw = stroke_mm / doc["mm_per_px"]
    out = [_svg_open(doc)]
    out.append(f'<g fill="none" stroke="{stroke}" stroke-width="{sw:.2f}" '
               'stroke-linejoin="round">')
    for rid, entry in _sorted_items(doc):
        if entry["kind"] == "dot":
            cx, cy = entry["center"]
            out.append(
                f'<circle data-region="{rid}" cx="{cx}" cy="{cy}" '
                f'r="{entry["radius_px"]}" fill="{stroke}" stroke="none"/>'
            )
        else:
            out.append(
                f'<path data-region="{rid}" d="{_d(entry["rings"])}" '
                'fill-rule="evenodd"/>'
            )
    out.append("</g></svg>")
    return "".join(out)


def color_svg(
    doc: dict,
    dmc_hex: dict[str, str],
    done_ids: set[str] | None = None,
    outline_undone: bool = True,
) -> str:
    """Flat-color render. With ``done_ids`` set, renders a step-progress
    illustration: completed regions in full color, the rest as gray trace
    lines on the 'fabric' — the same view as the guides' progress photos."""
    sw = 0.35 / doc["mm_per_px"]
    out = [_svg_open(doc)]
    out.append(f'<rect width="100%" height="100%" fill="#faf8f4"/>')
    for rid, entry in _sorted_items(doc):
        code = entry.get("dmc")
        hexc = dmc_hex.get(str(code), "#888888")
        done = done_ids is None or rid in done_ids
        if entry["kind"] == "dot":
            cx, cy = entry["center"]
            r = entry["radius_px"]
            if done:
                out.append(
                    f'<circle data-region="{rid}" cx="{cx}" cy="{cy}" r="{r}" '
                    f'fill="{hexc}"/>'
                )
            elif outline_undone:
                out.append(
                    f'<circle data-region="{rid}" cx="{cx}" cy="{cy}" r="{r}" '
                    f'fill="#b9b4ac"/>'
                )
            continue
        d = _d(entry["rings"])
        if done:
            edge = "#00000022" if _luma(entry["rgb"]) > 200 else hexc
            out.append(
                f'<path data-region="{rid}" d="{d}" fill="{hexc}" '
                f'fill-rule="evenodd" stroke="{edge}" stroke-width="{sw:.2f}"/>'
            )
        elif outline_undone:
            out.append(
                f'<path data-region="{rid}" d="{d}" fill="none" '
                f'fill-rule="evenodd" stroke="#b9b4ac" stroke-width="{sw:.2f}"/>'
            )
    out.append("</svg>")
    return "".join(out)
