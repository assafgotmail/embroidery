"""Per-project workspace: project.json, directory layout, physical scale."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path

MM_PER_INCH = 25.4

# Fraction of the hoop diameter the design occupies, matching the
# original guides where the motif sits well inside the 5" hoop.
DEFAULT_DESIGN_FRACTION = 0.75


@dataclass
class Project:
    name: str
    title: str
    hoop_inches: float = 5.0
    design_fraction: float = DEFAULT_DESIGN_FRACTION
    source_image: str = ""
    # Minimum area a region must cover on fabric before it is merged
    # away or turned into french-knot dots. ~2mm x 2mm of stitching.
    min_region_mm2: float = 4.0
    root: Path = field(default=None, repr=False)

    # ---- paths ----------------------------------------------------------
    @property
    def input_dir(self) -> Path:
        return self.root / "input"

    @property
    def work_dir(self) -> Path:
        return self.root / "work"

    @property
    def output_dir(self) -> Path:
        return self.root / "output"

    @property
    def assets_dir(self) -> Path:
        return self.output_dir / "assets"

    @property
    def source_path(self) -> Path:
        return self.input_dir / self.source_image

    # ---- physical scale --------------------------------------------------
    @property
    def hoop_mm(self) -> float:
        return self.hoop_inches * MM_PER_INCH

    @property
    def design_mm(self) -> float:
        """Target width/height (longest side) of the design on fabric."""
        return self.hoop_mm * self.design_fraction

    def mm_per_px(self, img_w: int, img_h: int) -> float:
        """Physical size of one source-image pixel once traced on fabric."""
        return self.design_mm / max(img_w, img_h)

    # ---- persistence -----------------------------------------------------
    def save(self) -> None:
        d = asdict(self)
        d.pop("root")
        for sub in (self.input_dir, self.work_dir, self.assets_dir):
            sub.mkdir(parents=True, exist_ok=True)
        (self.root / "project.json").write_text(json.dumps(d, indent=2))

    @classmethod
    def load(cls, root: str | Path) -> "Project":
        root = Path(root)
        d = json.loads((root / "project.json").read_text())
        return cls(root=root, **d)

    @classmethod
    def create(
        cls,
        root: str | Path,
        title: str,
        source_image: str,
        hoop_inches: float = 5.0,
        **kw,
    ) -> "Project":
        root = Path(root)
        p = cls(
            name=root.name,
            title=title,
            hoop_inches=hoop_inches,
            source_image=source_image,
            root=root,
            **kw,
        )
        p.save()
        return p
