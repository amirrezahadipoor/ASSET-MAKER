"""Reusable drawing primitives built on the core: masses with proper shading.

Everything here obeys STYLE_GUIDE: top-left light, hue-shifted ramps, 1 px
closed outlines, Bayer dithering only. Recipes compose these."""
from __future__ import annotations

import numpy as np

from . import noise, shading, shadow, shapes
from .dither import threshold_map
from .outline import outline_silhouette, seam_outline
from .palette import Ramp
from .shapes import Canvas, line_mask, poly_mask


def _modulate(t: np.ndarray, mask: np.ndarray, rng: np.random.Generator,
              amount: float, cell: int = 5) -> np.ndarray:
    """Subtle surface mottling (stone grain, bark, tile weathering)."""
    if amount <= 0:
        return t
    n = noise.value_noise_2d(t.shape[1], t.shape[0], cell, rng, octaves=2)
    return np.clip(t + (n - 0.5) * amount, 0.0, 1.0) * mask


def sphere_mass(canvas: Canvas, cx: float, cy: float, r: float, ramp: Ramp,
                rng: np.random.Generator | None = None,
                mottle: float = 0.10) -> np.ndarray:
    """A shaded sphere with top-left highlight island and closed outline."""
    mask = shapes.ellipse_mask(canvas.w, canvas.h, cx, cy, r, r)
    t = shading.radial_t(mask, cx, cy, r, r)
    if rng is not None:
        t = _modulate(t, mask, rng, mottle, cell=max(3, int(r * 0.45)))
    shading.apply_shading(canvas, mask, t, ramp)
    outline_silhouette(canvas, mask, ramp.outline)
    return mask


def dome_mass(canvas: Canvas, cx: float, cy: float, rx: float, ry: float,
              ramp: Ramp, rng: np.random.Generator,
              ruggedness: float = 0.16, lobes: int = 6,
              mottle: float = 0.12, dither: bool = False,
              outline: bool = True, t_boost: float = 0.0,
              t_span: float = 1.0) -> np.ndarray:
    """An organic lobe (foliage cluster unit, bush lobe, rock mass).

    t_span < 1 compresses the lobe's own ramp range so several lobes can
    share one canopy light field (position via t_boost) without each lobe
    reinventing a full highlight/shadow cycle — the reference canopy look."""
    radii = noise.radial_blob(rng, lobes=lobes, ruggedness=ruggedness)
    mask = shapes.blob_mask(canvas.w, canvas.h, cx, cy, rx, ry, radii)
    t = shading.radial_t(mask, cx, cy, rx, ry)
    t = 0.5 + (t - 0.5) * t_span + t_boost
    t = np.clip(t, 0, 1)
    t = _modulate(t, mask, rng, mottle, cell=max(3, int(min(rx, ry) * 0.6)))
    shading.apply_shading(canvas, mask, t, ramp, dither=dither)
    if outline:
        outline_silhouette(canvas, mask, ramp.outline)
    return mask


def cylinder_mass(canvas: Canvas, x0: float, y0: float, x1: float, y1: float,
                  r: float, ramp: Ramp, cap_top: bool = True,
                  cap_bottom: bool = False,
                  rng: np.random.Generator | None = None,
                  mottle: float = 0.06) -> np.ndarray:
    """A vertical-ish cylinder (trunks, posts, barrels, legs)."""
    mask = shapes.capsule_mask(canvas.w, canvas.h, x0, y0, x1, y1, r)
    t = shading.vertical_t(mask)
    if rng is not None:
        t = _modulate(t, mask, rng, mottle, cell=max(3, int(r * 1.2)))
    shading.apply_shading(canvas, mask, t, ramp)
    outline_silhouette(canvas, mask, ramp.outline)
    if cap_top:
        cap = shapes.ellipse_mask(canvas.w, canvas.h, x0, y0, r * 0.98,
                                  r * 0.55)
        cap_t = shading.radial_t(cap, x0 - r * 0.15, y0 - r * 0.1,
                                 r * 1.1, r * 0.7)
        shading.apply_shading(canvas, cap, cap_t, ramp)
        rim = cap & shapes.ellipse_mask(canvas.w, canvas.h, x0, y0,
                                        r * 0.98, r * 0.55)
        outline_silhouette(canvas, rim, ramp.outline)
    return mask


def box_top_mask(w: int, h: int, cx: float, y_top: float, hw: float,
                 hd: float) -> np.ndarray:
    pts = [(cx, y_top), (cx + hw, y_top + hd), (cx, y_top + 2 * hd),
           (cx - hw, y_top + hd)]
    return poly_mask(w, h, pts)


def box_left_mask(w: int, h: int, cx: float, y_top: float, hw: float,
                  hd: float, h_side: float) -> np.ndarray:
    pts = [(cx - hw, y_top + hd), (cx, y_top + 2 * hd),
           (cx, y_top + 2 * hd + h_side), (cx - hw, y_top + hd + h_side)]
    return poly_mask(w, h, pts)


def box_right_mask(w: int, h: int, cx: float, y_top: float, hw: float,
                   hd: float, h_side: float) -> np.ndarray:
    pts = [(cx, y_top + 2 * hd), (cx + hw, y_top + hd),
           (cx + hw, y_top + hd + h_side), (cx, y_top + 2 * hd + h_side)]
    return poly_mask(w, h, pts)


def box_mass(canvas: Canvas, cx: float, y_top: float, hw: float, hd: float,
             h_side: float, ramp: Ramp, rng: np.random.Generator | None = None,
             plank_step: float = 0.05, mottle: float = 0.05) -> np.ndarray:
    """3/4-view box: diamond top + two side faces, 3-level face shading.

    Returns the union mask. Face borders get 1 px dark seams."""
    w, h = canvas.w, canvas.h
    top = box_top_mask(w, h, cx, y_top, hw, hd)
    left = box_left_mask(w, h, cx, y_top, hw, hd, h_side)
    right = box_right_mask(w, h, cx, y_top, hw, hd, h_side)
    union = top | left | right

    t = shading.box_t(union, top, left, right)
    # plank bands: subtle per-row step variation on the side faces
    for face, base in ((left, 0.62), (right, 0.30)):
        ys = np.nonzero(face.any(axis=1))[0]
        if len(ys) == 0:
            continue
        band = 4
        for i, y in enumerate(range(ys[0], ys[-1] + 1, band)):
            seg = np.zeros_like(face)
            seg[y:y + band] = face[y:y + band]
            t[seg] = base + (plank_step if i % 2 == 0 else -plank_step)
    if rng is not None:
        t = _modulate(t, union, rng, mottle, cell=5)

    # paint each face separately so internal seams stay crisp
    for face in (top, left, right):
        shading.apply_shading(canvas, face, t, ramp, dither=False)
    outline_silhouette(canvas, union, ramp.outline)

    # plank seams: vertical on side faces, parallel on the top face
    inner = union & ~shapes.boundary_mask(union)
    for face in (left, right):
        fx = np.nonzero(face.any(axis=0))[0]
        if len(fx) > 2:
            for x in (fx[0] + max(3, (fx[-1] - fx[0]) // 2),):
                seam_col = np.zeros_like(face)
                seam_col[:, x] = True
                canvas.fill_mask(seam_col & face & inner, ramp.steps[1])
    for off in (-hw * 0.5, hw * 0.5):
        slant = line_mask(w, h, cx + off - hd, y_top + hd + off * 0.5,
                          cx + off + hd, y_top + hd - off * 0.5, 1)
        canvas.fill_mask(slant & top & inner, ramp.steps[-2])
        edge = (line_mask(w, h, cx + off - hd, y_top + hd + off * 0.5 - 1,
                          cx + off + hd, y_top + hd - off * 0.5 - 1, 1))
        canvas.fill_mask(edge & top & inner, ramp.steps[0])

    # internal edges: top-left edges catch light, bottom-right fall dark.
    # Highlight lines sit INSIDE the silhouette ring so the outline stays dark.
    inner = union & ~shapes.boundary_mask(union)
    edge_light = line_mask(w, h, cx - hw, y_top + hd, cx, y_top, 1) & union
    canvas.fill_mask(edge_light & top & inner, ramp.steps[-1])
    edge_mid = (line_mask(w, h, cx, y_top + 2 * hd, cx - hw, y_top + hd, 1)
                | line_mask(w, h, cx, y_top + 2 * hd, cx + hw, y_top + hd, 1))
    canvas.fill_mask(edge_mid & union & inner, ramp.outline)
    seam = (top & left) | (top & right) | (left & right)
    seam_outline(canvas, top, left, ramp.outline)
    seam_outline(canvas, top, right, ramp.outline)
    seam_outline(canvas, left, right, ramp.outline)
    return union


def seed_nicks(canvas: Canvas, mask: np.ndarray, ramp: Ramp,
               rng: np.random.Generator, count: int = 2) -> None:
    """Tiny 1 px weathering nicks/scratches at rng positions inside a mask.

    Also guarantees per-seed uniqueness of quantized output."""
    h, w = mask.shape
    inner = shapes.erode(mask, 1)
    ys, xs = np.nonzero(inner)
    if len(ys) < 8:
        return
    dark = ramp.steps[0]
    mid = ramp.steps[1]
    for _ in range(count):
        i = int(rng.integers(0, len(ys)))
        y, x = int(ys[i]), int(xs[i])
        length = int(rng.integers(2, 5))
        horizontal = bool(rng.integers(0, 2))
        nick = np.zeros((h, w), dtype=bool)
        if horizontal:
            nick[y:y + 1, x:min(w, x + length)] = True
        else:
            nick[y:min(h, y + length), x:x + 1] = True
        canvas.fill_mask(nick & inner, mid if rng.random() < 0.5 else dark)


def crack_lines(canvas: Canvas, mask: np.ndarray, ramp: Ramp,
                rng: np.random.Generator, count: int = 2) -> None:
    """Thin irregular facet cracks inside a rock/mass (reference rock style).

    1 px dark lines that start at the silhouette edge and die inside."""
    h, w = mask.shape
    ys, xs = np.nonzero(mask)
    if len(ys) < 20:
        return
    y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
    dark = ramp.steps[0]
    for _ in range(count):
        # start on the lower-right half of the boundary, walk inward-upward
        by = int(rng.integers(y0 + (y1 - y0) // 2, y1 + 1))
        bx = int(rng.integers(x0, x1 + 1))
        if not mask[by, bx]:
            continue
        px, py = float(bx), float(by)
        vx = float(rng.uniform(-0.7, -0.1)) * 1.4
        vy = float(rng.uniform(-1.0, -0.4))
        line = np.zeros((h, w), dtype=bool)
        for _step in range(2, 9):
            ix, iy = int(round(px)), int(round(py))
            if not (0 <= ix < w and 0 <= iy < h) or not mask[iy, ix]:
                break
            line[iy, ix] = True
            px += vx + rng.uniform(-0.35, 0.35)
            py += vy + rng.uniform(-0.25, 0.25)
        canvas.fill_mask(line & mask, dark)


def plank_texture(canvas: Canvas, mask: np.ndarray, ramp: Ramp,
                  direction: str = "h", spacing: int = 5) -> np.ndarray:
    """1 px separation lines across a wooden face (crates, walls, fences)."""
    dark = ramp.steps[1] if len(ramp.steps) > 1 else ramp.outline
    lines = np.zeros_like(mask)
    ys = np.nonzero(mask.any(axis=1))[0]
    xs = np.nonzero(mask.any(axis=0))[0]
    if direction == "h":
        for y in range(ys[0], ys[-1] + 1, spacing):
            lines[y, :] = True
    else:
        for x in range(xs[0], xs[-1] + 1, spacing):
            lines[:, x] = True
    band = lines & mask
    canvas.fill_mask(band, dark)
    return band


def tile_rows(canvas: Canvas, mask: np.ndarray, ramp: Ramp, rows: int = 4,
              slope: float = 0.55) -> None:
    """Roof tile rows: curved horizontal bands with per-tile highlights.

    Each row: a 1 px dark seam under it, and small highlight dashes on the
    top-left of each tile — the reference roof signature."""
    h, w = mask.shape
    ys = np.nonzero(mask.any(axis=1))[0]
    if len(ys) == 0:
        return
    y0, y1 = ys[0], ys[-1]
    row_h = max(3, (y1 - y0 + 1) // rows)
    dark = ramp.steps[0]
    hi = ramp.steps[-1]
    mid_hi = ramp.steps[-2] if len(ramp.steps) >= 2 else hi
    for r_i in range(rows):
        y_a = y0 + r_i * row_h
        y_b = min(y1 + 1, y_a + row_h)
        band = np.zeros((h, w), dtype=bool)
        band[y_a:y_b] = True
        band &= mask
        if not band.any():
            continue
        # seam under the row
        seam = np.zeros((h, w), dtype=bool)
        seam[max(0, y_b - 1):y_b] = True
        canvas.fill_mask(seam & mask, dark)
        # tile highlight dashes, staggered per row
        xs = np.nonzero(band.any(axis=0))[0]
        if len(xs) == 0:
            continue
        step = 4 + (r_i % 2)
        for i, x in enumerate(range(xs[0], xs[-1], step)):
            if (i + r_i) % 2 == 0:
                hi_m = np.zeros((h, w), dtype=bool)
                hi_m[y_a:min(y_b, y_a + 2), x:x + 2] = True
                canvas.fill_mask(hi_m & mask, mid_hi)
            else:
                sh_m = np.zeros((h, w), dtype=bool)
                sh_m[max(y_a, y_b - 2):y_b, x:x + 2] = True
                canvas.fill_mask(sh_m & mask, dark)
