"""DMC stranded-cotton color table and perceptual matching (CIEDE2000)."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
from skimage.color import rgb2lab, deltaE_ciede2000

DATA_CSV = Path(__file__).resolve().parent.parent / "data" / "dmc_colors.csv"


@dataclass(frozen=True)
class Thread:
    code: str
    name: str
    rgb: tuple[int, int, int]
    hex: str


@lru_cache(maxsize=1)
def load_threads() -> tuple[Thread, ...]:
    threads = []
    with open(DATA_CSV) as f:
        for row in csv.DictReader(f):
            threads.append(
                Thread(
                    code=row["code"],
                    name=row["name"],
                    rgb=(int(row["r"]), int(row["g"]), int(row["b"])),
                    hex="#" + row["hex"],
                )
            )
    return tuple(threads)


@lru_cache(maxsize=1)
def _thread_lab() -> np.ndarray:
    rgb = np.array([t.rgb for t in load_threads()], dtype=float) / 255.0
    return rgb2lab(rgb.reshape(1, -1, 3)).reshape(-1, 3)


def _to_lab(colors: np.ndarray) -> np.ndarray:
    arr = np.asarray(colors, dtype=float) / 255.0
    return rgb2lab(arr.reshape(1, -1, 3)).reshape(-1, 3)


def nearest(colors: np.ndarray, k: int = 1) -> list[list[tuple[Thread, float]]]:
    """For each RGB color (N,3 uint8), the k nearest DMC threads with dE2000."""
    threads = load_threads()
    lab = _to_lab(colors)
    tlab = _thread_lab()
    out = []
    for c in lab:
        de = deltaE_ciede2000(np.broadcast_to(c, tlab.shape), tlab)
        idx = np.argsort(de)[:k]
        out.append([(threads[i], float(de[i])) for i in idx])
    return out


def by_code(code: str) -> Thread:
    for t in load_threads():
        if t.code == str(code):
            return t
    raise KeyError(f"unknown DMC code: {code}")


def delta_e(rgb_a, rgb_b) -> float:
    a = _to_lab(np.array([rgb_a]))[0]
    b = _to_lab(np.array([rgb_b]))[0]
    return float(deltaE_ciede2000(a, b))
