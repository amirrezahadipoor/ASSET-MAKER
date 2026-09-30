"""Rasterizer: a palette-only RGBA canvas + boolean mask generators.

No anti-aliasing anywhere: masks are hard-edged, colors are palette hexes,
alpha is 0 or 255."""
from __future__ import annotations

import math

import numpy as np

from .palette import rgba


class Canvas:
    """H x W x 4 uint8 buffer with palette-validated plotting."""

    def __init__(self, w: int, h: int) -> None:
        self.w = int(w)
        self.h = int(h)
        self.buf = np.zeros((self.h, self.w, 4), dtype=np.uint8)

    # -- painting ---------------------------------------------------------
    def fill_mask(self, mask: np.ndarray, color: str) -> None:
        """Paint every True pixel of mask with a flat palette color."""
        if mask.shape != (self.h, self.w):
            raise ValueError("mask shape mismatch")
        self.buf[mask] = rgba(color)

    def paint_where(self, mask: np.ndarray, colors: np.ndarray) -> None:
        """Paint mask pixels from an (h, w) array of palette hex strings."""
        if mask.shape != (self.h, self.w):
            raise ValueError("mask shape mismatch")
        self.buf[mask] = np.array([rgba(c) for c in colors[mask].ravel()],
                                  dtype=np.uint8).reshape((-1, 4))

    def composite(self, other: "Canvas") -> None:
        """Alpha-over composite of `other` on top (alpha is 0/255)."""
        src = other.buf
        m = src[..., 3] > 0
        self.buf[m] = src[m]

    def copy(self) -> "Canvas":
        c = Canvas(self.w, self.h)
        c.buf = self.buf.copy()
        return c

    # -- queries ----------------------------------------------------------
    def alpha_mask(self) -> np.ndarray:
        return self.buf[..., 3] > 0

    def colors_used(self) -> set[str]:
        px = self.buf[self.alpha_mask()][:, :3]
        if len(px) == 0:
            return set()
        uniq = np.unique(px, axis=0)
        return {"#{:02x}{:02x}{:02x}".format(*row) for row in uniq}

    def bbox(self) -> tuple[int, int, int, int] | None:
        m = self.alpha_mask()
        if not m.any():
            return None
        ys, xs = np.nonzero(m)
        return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())

    def to_pil(self):
        from PIL import Image

        return Image.fromarray(self.buf, "RGBA")


# --------------------------------------------------------------------------
# Mask generators (bool arrays on a (h, w) grid)
# --------------------------------------------------------------------------

def grid(w: int, h: int):
    ys, xs = np.mgrid[0:h, 0:w]
    return xs.astype(np.float64), ys.astype(np.float64)


def ellipse_mask(w: int, h: int, cx: float, cy: float,
                 rx: float, ry: float) -> np.ndarray:
    xs, ys = grid(w, h)
    rx = max(rx, 0.5)
    ry = max(ry, 0.5)
    return ((xs - cx) / rx) ** 2 + ((ys - cy) / ry) ** 2 <= 1.0


def ellipse_ring_mask(w: int, h: int, cx: float, cy: float,
                      rx: float, ry: float, inner: float = 0.72) -> np.ndarray:
    outer = ellipse_mask(w, h, cx, cy, rx, ry)
    inner_m = ellipse_mask(w, h, cx, cy, rx * inner, ry * inner)
    return outer & ~inner_m


def rect_mask(w: int, h: int, x0: int, y0: int, x1: int, y1: int) -> np.ndarray:
    m = np.zeros((h, w), dtype=bool)
    x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
    m[max(0, y0):min(h, y1 + 1), max(0, x0):min(w, x1 + 1)] = True
    return m


def poly_mask(w: int, h: int, pts: list[tuple[float, float]]) -> np.ndarray:
    """Even-odd scanline polygon fill (hard edges, no AA)."""
    m = np.zeros((h, w), dtype=bool)
    if len(pts) < 3:
        return m
    ys = np.arange(h)
    for y in ys:
        xs_int: list[float] = []
        n = len(pts)
        for i in range(n):
            x1, y1 = pts[i]
            x2, y2 = pts[(i + 1) % n]
            if y1 == y2:
                continue
            if (y1 <= y < y2) or (y2 <= y < y1):
                t = (y - y1) / (y2 - y1)
                xs_int.append(x1 + t * (x2 - x1))
        if not xs_int:
            continue
        xs_int.sort()
        for i in range(0, len(xs_int) - 1, 2):
            a = int(math.ceil(xs_int[i] - 1e-9))
            b = int(math.floor(xs_int[i + 1] + 1e-9))
            if b >= a:
                m[y, max(0, a):min(w, b + 1)] = True
    return m


def line_mask(w: int, h: int, x0: float, y0: float, x1: float, y1: float,
              thickness: int = 1) -> np.ndarray:
    """Bresenham-ish line via sampled points; thickness expands the stamp."""
    m = np.zeros((h, w), dtype=bool)
    n = int(max(abs(x1 - x0), abs(y1 - y0)) * 2) + 1
    ts = np.linspace(0.0, 1.0, n)
    xs = np.round(x0 + (x1 - x0) * ts).astype(int)
    ys = np.round(y0 + (y1 - y0) * ts).astype(int)
    r = max(0, thickness // 2)
    for x, y in zip(xs, ys):
        m[max(0, y - r):min(h, y + r + 1), max(0, x - r):min(w, x + r + 1)] = True
    return m


def capsule_mask(w: int, h: int, x0: float, y0: float, x1: float, y1: float,
                 r: float) -> np.ndarray:
    """Thick line with round caps (stems, trunks, legs)."""
    xs, ys = grid(w, h)
    dx, dy = x1 - x0, y1 - y0
    L2 = dx * dx + dy * dy
    if L2 < 1e-9:
        return ellipse_mask(w, h, x0, y0, r, r)
    t = ((xs - x0) * dx + (ys - y0) * dy) / L2
    t = np.clip(t, 0.0, 1.0)
    px = x0 + t * dx
    py = y0 + t * dy
    return (xs - px) ** 2 + (ys - py) ** 2 <= r * r


def blob_mask(w: int, h: int, cx: float, cy: float, rx: float, ry: float,
              radii: np.ndarray) -> np.ndarray:
    """Irregular organic blob: ellipse with per-angle radius from `radii`."""
    xs, ys = grid(w, h)
    dx = (xs - cx) / max(rx, 0.5)
    dy = (ys - cy) / max(ry, 0.5)
    dist = np.sqrt(dx * dx + dy * dy)
    ang = np.arctan2(dy, dx)
    idx = ((ang + math.pi) / (2 * math.pi) * (len(radii) - 1)).astype(int)
    return dist <= radii[idx]


def cluster_mask(w: int, h: int, lobes: list[tuple[float, float, float, float,
                                                   np.ndarray]]) -> np.ndarray:
    """Union of blobs: [(cx, cy, rx, ry, radii_array), ...]."""
    m = np.zeros((h, w), dtype=bool)
    for cx, cy, rx, ry, radii in lobes:
        m |= blob_mask(w, h, cx, cy, rx, ry, radii)
    return m


def dilate(mask: np.ndarray, n: int = 1) -> np.ndarray:
    m = mask.copy()
    for _ in range(n):
        d = m.copy()
        d[1:, :] |= m[:-1, :]
        d[:-1, :] |= m[1:, :]
        d[:, 1:] |= m[:, :-1]
        d[:, :-1] |= m[:, 1:]
        m = d
    return m


def erode(mask: np.ndarray, n: int = 1) -> np.ndarray:
    return ~dilate(~mask, n)


def boundary_mask(mask: np.ndarray) -> np.ndarray:
    """1 px inner boundary of a mask (outermost ring of the silhouette)."""
    return mask & ~erode(mask, 1)
