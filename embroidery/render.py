"""HTML/SVG -> PDF/PNG via the preinstalled Chromium (Playwright)."""

from __future__ import annotations

import os
from pathlib import Path

from playwright.sync_api import sync_playwright


def _chromium_path() -> str | None:
    """The environment may pin a Chromium that doesn't match the installed
    playwright package revision; prefer the stable /opt/pw-browsers/chromium
    symlink (or CHROMIUM_PATH) when the default launch would fail."""
    for cand in (os.environ.get("CHROMIUM_PATH"), "/opt/pw-browsers/chromium"):
        if cand and Path(cand).exists():
            return cand
    return None


def _launch(pw):
    exe = _chromium_path()
    if exe:
        return pw.chromium.launch(executable_path=exe)
    return pw.chromium.launch()


def html_to_pdf(html_path: Path, pdf_path: Path, width: str, height: str) -> None:
    with sync_playwright() as pw:
        browser = _launch(pw)
        page = browser.new_page()
        page.goto(html_path.resolve().as_uri())
        page.wait_for_load_state("networkidle")
        page.pdf(
            path=str(pdf_path),
            width=width,
            height=height,
            print_background=True,
            margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
        )
        browser.close()


def svgs_to_pngs(jobs: list[tuple[Path, Path, int]]) -> None:
    """Render (svg_path, png_path, px_width) jobs in one browser session."""
    with sync_playwright() as pw:
        browser = _launch(pw)
        for svg_path, png_path, px_w in jobs:
            page = browser.new_page(viewport={"width": px_w, "height": px_w})
            page.goto(svg_path.resolve().as_uri())
            # the document element itself; inner <svg> viewports don't count
            svg = page.locator("svg").first
            svg.evaluate(
                "(el, w) => { const vb = el.viewBox.baseVal;"
                " el.setAttribute('width', w);"
                " el.setAttribute('height', Math.round(w * vb.height / vb.width)); }",
                px_w,
            )
            svg.screenshot(path=str(png_path))
            page.close()
        browser.close()
