"""Recipe: tree (nature) — the hardest static quality test (ROADMAP M3).

Composition (STYLE_GUIDE §8): tapered trunk with root flares + 2-3 branches
entering a canopy of 8-12 overlapping lobes. Canopy shares ONE light field
(top-left bright yellow-green -> teal shadow pockets bottom-right) with
1 px dark lobe seams. Draw order: back lobes -> trunk/branches -> front lobes.
"""
from __future__ import annotations

import numpy as np

from ..core import noise, primitives, shading, shadow, shapes
from ..core.export import AssetResult
from ..core.outline import outline_silhouette
from ..core.palette import RAMPS
from ..core.shapes import Canvas
from .catalog import register

LEAF = RAMPS["leaf"]
BARK = RAMPS["bark"]


def green_preview(body: Canvas) -> np.ndarray:
    """Mask of already-painted leaf-colored pixels (for branch weaving)."""
    m = np.zeros((body.h, body.w), dtype=bool)
    px = body.buf
    for c in LEAF.all_colors:
        m |= (px[..., 0] == int(c[1:3], 16)) & \
             (px[..., 1] == int(c[3:5], 16)) & \
             (px[..., 2] == int(c[5:7], 16)) & (px[..., 3] > 0)
    return m


def _canopy_layout(rng: np.random.Generator, cx: float, cy: float,
                   rx: float, ry: float, n: int):
    """Solid canopy: center lobe + a ring of lobes (no holes), silhouette
    irregularity from jittered angles/radii. Back (high) first, front last."""
    lobes = []
    jx = rng.uniform(-0.06, 0.06) * rx
    jy = rng.uniform(-0.06, 0.06) * ry
    lobes.append((cx + jx, cy + jy, rx * 0.44, ry * 0.48))
    ring = max(1, n - 1)
    start = rng.uniform(0, 6.283)
    for i in range(ring):
        ang = start + 6.283 * i / ring + rng.uniform(-0.22, 0.22)
        rad = rng.uniform(0.52, 0.74)
        lx = cx + np.cos(ang) * rx * rad
        ly = cy + np.sin(ang) * ry * rad
        lrx = rx * rng.uniform(0.40, 0.52)
        lry = ry * rng.uniform(0.42, 0.55)
        lobes.append((lx, ly, lrx, lry))
    return lobes


@register("tree", "nature", doc="cluster-canopy tree, 3 silhouettes")
def make_tree(seed: int, variant: int = 1) -> AssetResult:
    rng = noise.rng_for("tree", variant, seed)
    v = (variant - 1) % 3
    w, h = 92, 108
    cx = 46
    ground_y = 98

    # geometry per variant: (trunk_top, canopy_cy, canopy_rx, canopy_ry, n_lobes)
    trunk_top, can_cy, can_rx, can_ry, n_lobes = [
        (56, 40, 32, 26, 11),
        (50, 34, 35, 30, 12),
        (62, 48, 27, 21, 9),
    ][v]

    body = Canvas(w, h)

    # ---- back canopy lobes (drawn first, they sit behind the trunk) ----
    all_lobes = _canopy_layout(rng, cx, can_cy, can_rx, can_ry, n_lobes)
    # sort into back (upper) and front (lower) bands for the trunk sandwich
    all_lobes.sort(key=lambda L: L[1])
    n_back = max(3, n_lobes // 3)
    back, front = all_lobes[:n_back], all_lobes[n_back:]
    for (lx, ly, lrx, lry) in back:
        depth = np.clip((ly - (can_cy - can_ry)) / (2 * can_ry), 0, 1)
        primitives.dome_mass(
            body, lx, ly, lrx, lry, LEAF, rng,
            ruggedness=0.20, lobes=6, mottle=0.07,
            t_boost=0.12 - 0.32 * depth - 0.004 * (lx - cx), t_span=0.58)

    # ---- trunk + roots + branches ----
    trunk_mask = shapes.capsule_mask(w, h, cx, ground_y - 6, cx, trunk_top,
                                     3.2)
    taper = shapes.capsule_mask(w, h, cx, trunk_top + 10, cx, trunk_top, 2.2)
    trunk_mask |= taper
    # root flares
    for rx_off, ry_off, rr in ((-7, 2.5, 2.2), (7, 2.5, 2.2), (-3, 3.5, 1.8),
                               (3.5, 3.5, 1.8)):
        trunk_mask |= shapes.capsule_mask(w, h, cx, ground_y - 7,
                                          cx + rx_off, ground_y - 4 + ry_off,
                                          rr)
    # branches into the canopy
    branch_pts = [(-13, -12), (13, -14), (-7, -18), (8, -19)]
    n_br = 2 + (v % 2) + 1
    for bx, by in branch_pts[:n_br]:
        trunk_mask |= shapes.capsule_mask(
            w, h, cx, trunk_top + 12, cx + bx, trunk_top + by, 1.7)

    t = shading.vertical_t(trunk_mask)
    t = primitives._modulate(t, trunk_mask, rng, 0.06, cell=5)
    shading.apply_shading(body, trunk_mask, t, BARK)
    # bark texture: 2-3 vertical dark streaks
    for frac in (-2.2, 0.4, 2.4):
        streak = shapes.capsule_mask(w, h, cx + frac, ground_y - 8,
                                     cx + frac * 0.6, trunk_top + 6, 0.6)
        body.fill_mask(streak & trunk_mask & shapes.erode(trunk_mask, 1),
                       BARK.steps[1])
    outline_silhouette(body, trunk_mask, BARK.outline)

    # ---- front canopy lobes (cover the branch tips) ----
    for (lx, ly, lrx, lry) in front:
        depth = np.clip((ly - (can_cy - can_ry)) / (2 * can_ry), 0, 1)
        primitives.dome_mass(
            body, lx, ly, lrx, lry, LEAF, rng,
            ruggedness=0.20, lobes=6, mottle=0.07,
            t_boost=0.12 - 0.32 * depth - 0.004 * (lx - cx), t_span=0.58)

    # visible branch forks peeking through the canopy's lower edge — the
    # reference trees show short dark wood splits against the foliage
    band_limit = np.zeros((h, w), dtype=bool)
    band_limit[trunk_top + 2:trunk_top + 24] = True
    for bx, by in branch_pts[:2]:
        fork = shapes.capsule_mask(w, h, cx, trunk_top + 16,
                                   cx + bx * 0.55, trunk_top + by * 0.55, 1.5)
        band = fork & green_preview(body) & band_limit
        body.fill_mask(band, BARK.steps[2])
        body.fill_mask(shapes.boundary_mask(band), BARK.outline)

    # outer canopy silhouette: closed outline over everything green
    green_mask = np.zeros((h, w), dtype=bool)
    px = body.buf
    for c in LEAF.all_colors:
        green_mask |= (px[..., 0] == int(c[1:3], 16)) & \
                      (px[..., 1] == int(c[3:5], 16)) & \
                      (px[..., 2] == int(c[5:7], 16)) & (px[..., 3] > 0)
    outline_silhouette(body, green_mask, LEAF.outline)

    anchor = (int(cx), ground_y - 2)
    sh = Canvas(w, h)
    smask = shadow.ground_shadow_mask(w, h, anchor, can_rx * 0.85,
                                      can_ry * 0.22)
    # tree shadows are large and cast to the right of the trunk
    smask = smask | shapes.ellipse_mask(w, h, cx + 10, ground_y + 1,
                                        can_rx * 0.62, can_ry * 0.17)
    shadow.cast_shadow(sh, smask, soft=1)
    colors_used = body.colors_used() | sh.colors_used()
    return AssetResult(
        category="nature", kind="tree", variant=variant, seed=seed,
        width=w, height=h, anchor=anchor, shadow=sh, parts={"body": body},
        rig=None, colors_used=colors_used,
    )
