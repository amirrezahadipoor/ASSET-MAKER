"""Shading: pseudo-3D lambert fields quantized to palette ramps.

Light direction is fixed: top-left (STYLE_GUIDE §2). In image coords
(x right, y down, z toward viewer) the light vector points up-left-forward."""
from __future__ import annotations

import numpy as np

from .dither import dither_pick
from .palette import Ramp
from .shapes import grid

# Fixed light: from top-left, above the surface. Normalized.
LIGHT = np.array([-0.52, -0.66, 0.54])
LIGHT = LIGHT / np.linalg.norm(LIGHT)


def dome_height(mask: np.ndarray, cx: float, cy: float,
                rx: float, ry: float) -> np.ndarray:
    """z in [0,1] over a spherical dome footprint (canopies, barrels, heads)."""
    xs, ys = grid(mask.shape[1], mask.shape[0])
    d2 = ((xs - cx) / max(rx, 0.5)) ** 2 + ((ys - cy) / max(ry, 0.5)) ** 2
    z = np.sqrt(np.clip(1.0 - d2, 0.0, 1.0))
    return z * mask


def height_normals(z: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Normals from a height field via central differences (x, y, z)."""
    dzdx = np.zeros_like(z)
    dzdy = np.zeros_like(z)
    dzdx[:, 1:-1] = (z[:, 2:] - z[:, :-2]) * 0.5
    dzdy[1:-1, :] = (z[2:, :] - z[:-2, :]) * 0.5
    nx, ny, nz = -dzdx, -dzdy, np.ones_like(z)
    norm = np.sqrt(nx * nx + ny * ny + nz * nz)
    return nx / norm, ny / norm, nz / norm


def lambert_t(z: np.ndarray, ambient: float = 0.22,
              spread: float = 1.18) -> np.ndarray:
    """Lambert term remapped to t in [0,1] (0 = darkest ramp step).

    `spread` widens the ramp usage so mid-tones land in the middle of the
    ramp like the reference (never washed out, never crushed).
    """
    nx, ny, nz = height_normals(z)
    lam = nx * LIGHT[0] + ny * LIGHT[1] + nz * LIGHT[2]
    t = ambient + (1.0 - ambient) * np.clip(lam, 0.0, 1.0) ** 0.85
    return np.clip((t - 0.5) * spread + 0.5, 0.0, 1.0)


def normalize_t(t: np.ndarray, mask: np.ndarray,
                lo: float = 0.02, hi: float = 0.98) -> np.ndarray:
    """Stretch t to fill [lo, hi] over the mask so every mass uses its ramp."""
    vals = t[mask]
    if len(vals) == 0:
        return t
    tmin, tmax = float(vals.min()), float(vals.max())
    if tmax - tmin < 1e-6:
        return np.full_like(t, (lo + hi) / 2) * mask
    out = lo + (hi - lo) * (t - tmin) / (tmax - tmin)
    return np.clip(out, 0.0, 1.0) * mask


def planar_light_t(mask: np.ndarray, cx: float, cy: float,
                   rx: float, ry: float, scale: float = 0.95) -> np.ndarray:
    """2D planar light: 1 toward the light (top-left), 0 away (bottom-right).

    The reference rocks/lobes read as lit FACES, not just curved normals —
    this term gives those clean large bands; radial_t blends it with the
    dome lambert for roundness."""
    xs, ys = grid(mask.shape[1], mask.shape[0])
    u = (xs - cx) / max(rx, 0.5)
    v = (ys - cy) / max(ry, 0.5)
    l2 = LIGHT[:2] / np.linalg.norm(LIGHT[:2])
    # pos toward the light (top-left) => u*l2[0]+v*l2[1] > 0 => bright
    bright = np.clip((u * l2[0] + v * l2[1]) * scale, -1.0, 1.0) * 0.5 + 0.5
    return bright * mask


def radial_t(mask: np.ndarray, cx: float, cy: float,
             rx: float, ry: float) -> np.ndarray:
    """Shade t for a dome-shaped mass with top-left highlight."""
    z = dome_height(mask, cx, cy, rx, ry)
    lam = lambert_t(z)
    planar = planar_light_t(mask, cx, cy, rx, ry)
    t = 0.62 * planar + 0.38 * lam
    t = normalize_t(t, mask)
    # mild S-curve: clean large bands like the reference
    t = np.clip(0.5 + (t - 0.5) * 1.1 + 0.05, 0.0, 1.0)
    return t * mask


def box_t(mask: np.ndarray, top_face: np.ndarray, left_face: np.ndarray,
          right_face: np.ndarray) -> np.ndarray:
    """Three-face box shading (STYLE_GUIDE §6): top light, left mid, right dark.

    Faces may overlap; priority is top > left > right."""
    t = np.zeros(mask.shape, dtype=np.float64)
    t[mask] = 0.38  # front fallback
    t[right_face] = 0.30
    t[left_face] = 0.62
    t[top_face] = 0.86
    return t * mask


def vertical_t(mask: np.ndarray, tilt: float = 0.18) -> np.ndarray:
    """Cylindrical shading (trunks, posts): lighter on the left edge.

    Cross-section lambert: z = sqrt(1 - u^2) where u is horizontal position
    within the mask's per-row extent, light from the left.
    """
    h, w = mask.shape
    t = np.zeros((h, w), dtype=np.float64)
    xs = np.arange(w)
    for y in range(h):
        row = mask[y]
        if not row.any():
            continue
        idx = np.nonzero(row)[0]
        x0, x1 = idx[0], idx[-1]
        span = max(1, x1 - x0)
        u = np.clip((xs[x0:x1 + 1] - x0) / span * 2 - 1, -1, 1)
        z = np.sqrt(np.clip(1 - u * u, 0, 1))
        # outward normal is (u, 0, z); light from the left => bright at u<0
        lam = u * LIGHT[0] + z * LIGHT[2] + LIGHT[1] * 0.25
        t[y, x0:x1 + 1] = np.clip(0.20 + 0.85 * np.clip(lam, 0, 1) + tilt * (u < 0),
                                  0.0, 1.0)
    return t * mask


def quantize(t: np.ndarray, mask: np.ndarray, ramp: Ramp,
             dither: bool = False) -> np.ndarray:
    """t in [0,1] -> (h, w) object array of palette hex strings.

    Clean bands by default (the reference dithers only in a few places);
    dither=True gives ordered Bayer mixing between adjacent steps."""
    n = len(ramp.steps)
    field = t * (n - 1)
    frac = field - np.floor(field)
    if dither:
        idx = dither_pick(field, frac)
    else:
        idx = np.round(field).astype(np.int32)
    idx = np.clip(idx, 0, n - 1)
    out = np.empty(t.shape, dtype=object)
    out[mask] = [ramp.steps[i] for i in idx[mask]]
    return out


def apply_shading(canvas, mask: np.ndarray, t: np.ndarray, ramp: Ramp,
                  dither: bool = False) -> None:
    """Paint a shaded ramp surface onto a canvas (fill only where mask)."""
    colors = quantize(t, mask, ramp, dither=dither)
    canvas.paint_where(mask, colors)


def shift_t(t: np.ndarray, mask: np.ndarray, dx: float, dy: float,
            falloff: float = 1.0) -> np.ndarray:
    """Shift a t-field's highlight center (used when a mass leans right)."""
    h, w = t.shape
    xs, ys = grid(w, h)
    bump = np.exp(-(((xs - (w / 2 - dx)) ** 2 + (ys - (h / 2 - dy)) ** 2)
                    / (max(w, h) * falloff) ** 2))
    return np.clip(t + bump * 0.12, 0, 1) * mask
