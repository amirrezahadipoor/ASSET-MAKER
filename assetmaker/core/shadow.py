"""Ground contact shadows (STYLE_GUIDE §7): soft, bottom-right, palette-pure."""
from __future__ import annotations

import numpy as np

from .dither import dither_edge
from .palette import SHADOW_COLOR
from .shapes import dilate, ellipse_mask


def ground_shadow_mask(w: int, h: int, anchor: tuple[int, int],
                       base_rx: float, base_ry: float | None = None,
                       offset_k: float = 0.16) -> np.ndarray:
    """Soft ellipse under an object, pushed to the bottom-right.

    anchor: ground contact point (x, y). Shadow is wider than the base and
    offset toward bottom-right because the light is top-left.
    """
    ax, ay = anchor
    ry = base_ry if base_ry is not None else max(2.0, base_rx * 0.42)
    rx = max(2.0, base_rx)
    dx = rx * offset_k
    dy = ry * (offset_k * 0.9)
    cx, cy = ax + dx, ay + dy * 0.8
    m = ellipse_mask(w, h, cx, cy, rx, ry)
    return m


def render_shadow(mask: np.ndarray, soft: int = 1) -> np.ndarray:
    """Shadow with a thin Bayer-dithered rim (alpha stays 0/255).

    The reference shadows are mostly solid dark green with a slightly eaten
    rim — soft, but not noisy."""
    m = dither_edge(mask, band=soft, strength=0.92)
    return m


def cast_shadow(canvas, mask: np.ndarray, color: str = SHADOW_COLOR,
                soft: int = 2) -> np.ndarray:
    """Paint the shadow mask onto a canvas layer."""
    m = render_shadow(mask, soft=soft)
    canvas.fill_mask(m, color)
    return m


def blob_shadow_mask(w: int, h: int, mask: np.ndarray,
                     push: tuple[float, float] = (2.0, 1.5)) -> np.ndarray:
    """Shadow derived from the silhouette itself (for sprawling art like
    trees): dilate + offset toward bottom-right."""
    dx, dy = int(push[0]), int(push[1])
    m = np.zeros_like(mask)
    src = dilate(mask, 1)
    m[max(0, dy):, max(0, dx):] = src[:mask.shape[0] - dy or None,
                                      :mask.shape[1] - dx or None]
    return m
