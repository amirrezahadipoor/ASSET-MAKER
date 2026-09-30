"""Ordered (Bayer) dithering — the only dithering style allowed (STYLE_GUIDE §6).

No random dithering anywhere; determinism matters."""
from __future__ import annotations

import numpy as np

# Bayer 4x4 normalized to [0,1).
BAYER4 = np.array(
    [[0, 8, 2, 10],
     [12, 4, 14, 6],
     [3, 11, 1, 9],
     [15, 7, 13, 5]],
    dtype=np.float64,
) / 16.0


def threshold_map(h: int, w: int) -> np.ndarray:
    """Tile the Bayer matrix to (h, w) in [0,1)."""
    ty = (np.arange(h) % 4)[:, None]
    tx = (np.arange(w) % 4)[None, :]
    return BAYER4[ty, tx]


def dither_pick(field: np.ndarray, frac: np.ndarray) -> np.ndarray:
    """Pick floor(field)+1 where frac >= bayer threshold, else floor(field).

    field: float ramp position; frac: field - floor(field).
    Returns int index array.
    """
    h, w = field.shape
    base = np.floor(field).astype(np.int32)
    bump = (frac >= threshold_map(h, w)).astype(np.int32)
    return base + bump


def dither_edge(mask: np.ndarray, band: int = 2,
                strength: float = 0.55) -> np.ndarray:
    """Carve a Bayer-dithered soft rim around a filled mask.

    Erodes the outer `band` px of the mask into a checker dropout so the edge
    reads soft at 1x while staying palette/alpha clean. mask: bool (h, w).
    """
    m = mask.copy()
    if band <= 0:
        return m
    h, w = m.shape
    th = threshold_map(h, w)
    eroded = m.copy()
    for _ in range(band):
        e = eroded.copy()
        e[1:, :] &= eroded[:-1, :]
        e[:-1, :] &= eroded[1:, :]
        e[:, 1:] &= eroded[:, :-1]
        e[:, :-1] &= eroded[:, 1:]
        rim = eroded & ~e
        keep = th < strength
        m[rim] = eroded[rim] & keep[rim]
        eroded = e
    return m
