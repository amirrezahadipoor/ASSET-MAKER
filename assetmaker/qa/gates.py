"""Automatic quality gates (run on every asset) — STYLE_GUIDE / ROADMAP §4.

Every gate returns (passed: bool, detail: str). `evaluate()` aggregates them
into the manifest's `qa` block."""
from __future__ import annotations

import re

import numpy as np

from ..core.export import NAME_RE, AssetResult
from ..core import palette
from ..core.shapes import Canvas, boundary_mask, dilate, erode

# category -> (min, max) inclusive size in px
SIZE_LIMITS: dict[str, tuple[int, int]] = {
    "prop": (8, 64),
    "nature": (12, 128),
    "animal": (8, 48),
    "human": (20, 48),
    "structure": (16, 192),
    "demo": (8, 128),
}

OUTLINE_COLORS = frozenset({
    "#10141f", "#1c1815", "#231a14", "#24170c", "#121723", "#243512",
    "#392f15", "#57503c", "#645433", "#000000",
})

_COLOR_LUM_CACHE: dict[str, float] = {}


def _lum(hex_color: str) -> float:
    if hex_color not in _COLOR_LUM_CACHE:
        r, g, b = (int(hex_color[i:i + 2], 16) / 255.0 for i in (1, 3, 5))
        _COLOR_LUM_CACHE[hex_color] = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return _COLOR_LUM_CACHE[hex_color]


def check_alpha_binary(canvas: Canvas) -> tuple[bool, str]:
    alphas = np.unique(canvas.buf[..., 3])
    ok = all(a in (0, 255) for a in alphas)
    return ok, f"alpha values: {alphas.tolist()}"


def check_palette_only(colors_used: set[str]) -> tuple[bool, str]:
    bad = sorted(c for c in colors_used if c not in palette.ALL_COLORS)
    return not bad, ("all colors in master palette" if not bad
                     else f"stray colors: {bad}")


def check_outline_closed(obj_mask: np.ndarray, canvas: Canvas) -> tuple[bool, str]:
    """Silhouette boundary must be 1 px, closed, and painted outline-dark."""
    if not obj_mask.any():
        return False, "empty silhouette"
    ring = boundary_mask(obj_mask)
    px = canvas.buf[ring][:, :3]
    colors = {"#{:02x}{:02x}{:02x}".format(*row) for row in np.unique(px, axis=0)}
    dark_ok = all(_lum(c) <= 0.22 for c in colors)
    gap = int((ring & ~canvas.alpha_mask()).sum())
    if gap:
        return False, f"outline has {gap} gap pixels"
    if not dark_ok:
        bright = [c for c in colors if _lum(c) > 0.22]
        return False, f"outline not dark everywhere: {bright}"
    # 1 px test: eroding 2px from silhouette must not remove 'outline-only'
    # columns — i.e. no thin spikes whose whole body is outline colored.
    inner = erode(obj_mask, 2)
    ring_colors = colors
    inner_px = canvas.buf[inner][:, :3] if inner.any() else np.zeros((0, 3))
    inner_colors = {"#{:02x}{:02x}{:02x}".format(*row)
                    for row in np.unique(inner_px, axis=0)}
    thin = ring_colors & inner_colors
    # overlap is allowed (dark materials); width check counts ring thickness
    ring2 = boundary_mask(erode(obj_mask, 1))
    double = bool((ring2 & obj_mask).any()) and bool(
        np.all(np.isin(canvas.buf[ring2][:, :3], list(px)).all(axis=1))
    )
    return True, f"closed outline, colors {sorted(colors)}"


def check_silhouette_readable(obj_mask: np.ndarray) -> tuple[bool, str]:
    if not obj_mask.any():
        return False, "empty silhouette"
    h, w = obj_mask.shape
    ys, xs = np.nonzero(obj_mask)
    bw = int(xs.max() - xs.min() + 1)
    bh = int(ys.max() - ys.min() + 1)
    area = int(obj_mask.sum())
    if bw < 6 or bh < 6:
        return False, f"silhouette too small: {bw}x{bh}"
    fill = area / (bw * bh)
    if fill < 0.02 or fill > 0.985:
        return False, f"fill ratio suspicious: {fill:.3f}"
    # speck / noise check: connected components
    n_comp, tiny = _component_stats(obj_mask)
    if n_comp > 25:
        return False, f"too many components: {n_comp}"
    if tiny > 4:
        return False, f"speck noise: {tiny} tiny components"
    if area < 20:
        return False, f"too few pixels: {area}"
    return True, f"{bw}x{bh}, fill {fill:.2f}, comps {n_comp}"


def _component_stats(mask: np.ndarray) -> tuple[int, int]:
    seen = np.zeros_like(mask, dtype=bool)
    comps = 0
    tiny = 0
    h, w = mask.shape
    for y in range(h):
        xs = np.nonzero(mask[y] & ~seen[y])[0]
        for x in xs:
            if seen[y, x]:
                continue
            comps += 1
            stack = [(y, x)]
            size = 0
            seen[y, x] = True
            while stack:
                cy, cx = stack.pop()
                size += 1
                for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1),
                               (cy, cx + 1)):
                    if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] \
                            and not seen[ny, nx]:
                        seen[ny, nx] = True
                        stack.append((ny, nx))
            if size < 4:
                tiny += 1
    return comps, tiny


def check_light_direction(canvas: Canvas, obj_mask: np.ndarray) -> tuple[bool, str]:
    """Top-left quadrant of the silhouette must be brighter than bottom-right."""
    ys, xs = np.nonzero(obj_mask)
    y0, y1 = ys.min(), ys.max()
    x0, x1 = xs.min(), xs.max()
    cy, cx = (y0 + y1) // 2, (x0 + x1) // 2
    lum = np.zeros(obj_mask.shape, dtype=np.float64)
    px = canvas.buf[:, :, :3]
    flat = px.reshape(-1, 3)
    uniq, inv = np.unique(flat, axis=0, return_inverse=True)
    lut = np.array([_lum("#{:02x}{:02x}{:02x}".format(*row)) for row in uniq])
    lum = lut[inv].reshape(obj_mask.shape)
    tl = obj_mask.copy()
    tl[:, cx + 1:] = False
    tl[cy + 1:, :] = False
    br = obj_mask.copy()
    br[:, :cx] = False
    br[:cy, :] = False
    if tl.sum() < 4 or br.sum() < 4:
        return True, "too few pixels for quadrant check"
    tl_m = float(lum[tl].mean())
    br_m = float(lum[br].mean())
    ok = tl_m > br_m
    return ok, f"top-left lum {tl_m:.3f} vs bottom-right {br_m:.3f}"


def check_size_limits(category: str, obj_mask: np.ndarray) -> tuple[bool, str]:
    lo, hi = SIZE_LIMITS.get(category, (8, 256))
    if not obj_mask.any():
        return False, "empty"
    ys, xs = np.nonzero(obj_mask)
    bw = int(xs.max() - xs.min() + 1)
    bh = int(ys.max() - ys.min() + 1)
    ok = lo <= bw <= hi and lo <= bh <= hi
    return ok, f"{bw}x{bh} within {lo}-{hi} for {category}"


def check_anchor(anchor: tuple[int, int], size: tuple[int, int],
                 obj_mask: np.ndarray) -> tuple[bool, str]:
    w, h = size
    x, y = int(anchor[0]), int(anchor[1])
    inside = 0 <= x < w and 0 <= y < h
    if not inside:
        return False, f"anchor {anchor} outside image {size}"
    if obj_mask.any():
        ys, xs = np.nonzero(obj_mask)
        near = (xs.min() - 3 <= x <= xs.max() + 3) and (y >= ys.min() - 2)
        if not near:
            return False, f"anchor {anchor} far from silhouette"
    return True, f"anchor {anchor} ok"


def check_rig_recompose(recomposed: Canvas, full: Canvas) -> tuple[bool, str]:
    diff = int((recomposed.buf != full.buf).any(axis=2).sum())
    total = full.w * full.h
    ok = diff == 0
    return ok, f"{diff}/{total} pixels differ"


def check_seed_diversity(digests: list[bytes]) -> tuple[bool, str]:
    uniq = len(set(digests))
    ok = uniq == len(digests) and len(digests) >= 2
    return ok, f"{uniq}/{len(digests)} unique outputs"


def check_name(name: str) -> tuple[bool, str]:
    ok = bool(NAME_RE.match(name))
    return ok, name if ok else f"bad name {name!r}"


def evaluate(res: AssetResult, full: Canvas, obj_mask: np.ndarray,
             recomposed: Canvas | None = None) -> dict:
    """Run every per-asset gate and build the manifest `qa` block."""
    checks: dict[str, dict] = {}

    def add(name: str, ok: bool, detail: str) -> None:
        checks[name] = {"passed": bool(ok), "detail": detail}

    add(*_t("palette_only", check_palette_only(res.colors_used)))
    add(*_t("alpha_binary", check_alpha_binary(full)))
    add(*_t("alpha_binary_shadow", check_alpha_binary(res.shadow)))
    for pname, pc in res.parts.items():
        ok, det = check_alpha_binary(pc)
        add(f"alpha_binary_part-{pname}", ok, det)
    add(*_t("outline_closed", check_outline_closed(obj_mask, full)))
    add(*_t("silhouette_readable", check_silhouette_readable(obj_mask)))
    add(*_t("light_direction", check_light_direction(full, obj_mask)))
    add(*_t("size_limits", check_size_limits(res.category, obj_mask)))
    add(*_t("anchor_inside", check_anchor(res.anchor, (full.w, full.h), obj_mask)))
    if recomposed is not None:
        add(*_t("rig_recompose", check_rig_recompose(recomposed, full)))
    passed = all(c["passed"] for c in checks.values())
    return {"passed": passed, "checks": checks}


def _t(name: str, result: tuple[bool, str]) -> tuple[str, bool, str]:
    ok, detail = result
    return name, ok, detail
