"""Recipe: bush (nature) — foliage lobe cluster with rich hue-shifted shading.

Reference study: bushes are small canopy clusters (3-6 overlapping lobes),
bright yellow-green highlights top-left, deep teal shadow pockets bottom-right,
1 px dark seams where lobes overlap. Optional flower accents (variants).
"""
from __future__ import annotations

import numpy as np

from ..core import noise, primitives, shadow
from ..core.export import AssetResult
from ..core.outline import outline_silhouette
from ..core.palette import ACCENTS, RAMPS
from ..core.shapes import Canvas
from .catalog import register


@register("bush", "nature", doc="foliage cluster bush, 3 silhouettes + flowers")
def make_bush(seed: int, variant: int = 1) -> AssetResult:
    rng = noise.rng_for("bush", variant, seed)
    v = (variant - 1) % 4
    w, h = 50, 45
    cx, base_y = w // 2, 31

    # lobe layout per variant: (cx_off, cy_off, rx, ry, depth)
    layouts = [
        [(-11, -6, 9, 7), (0, -11, 11, 8.5), (11, -5, 9, 7),
         (-5, -2, 10, 7.5), (6, -1, 10, 7.5)],
        [(-8, -10, 8.5, 8), (8, -9, 8.5, 8), (-13, -2, 8, 6.5),
         (0, -3, 12, 8), (12, -1, 8, 6.5)],
        [(-10, -8, 9, 7.5), (2, -12, 9, 7), (11, -6, 8.5, 7),
         (-4, -1, 11, 7)],
        [(-12, -4, 8, 6), (-3, -10, 9.5, 8), (8, -10, 9, 7.5),
         (13, -3, 8, 6), (0, -2, 11, 7)],
    ][v]

    body = Canvas(w, h)
    all_masks = []
    # back-to-front: upper lobes first (they sit behind), lower lobes front.
    # Light is top-left: upper-left lobes catch light, lower-right lobes sink
    # into the teal shadow pocket (t_boost follows POSITION, not draw order).
    order = sorted(range(len(layouts)), key=lambda i: layouts[i][1])
    for i in order:
        ox, oy, rx, ry = layouts[i]
        depth = (oy + 12) / 12.0  # 0 back/top .. 1 front/bottom
        t_boost = 0.14 - 0.34 * depth - 0.006 * ox
        m = primitives.dome_mass(
            body, cx + ox, base_y + oy, rx, ry, RAMPS["leaf"], rng,
            ruggedness=0.18, lobes=6, mottle=0.07, t_boost=t_boost,
            t_span=0.62)
        all_masks.append(m)

    # deep shadow pockets where the cluster meets the ground
    union = np.zeros((h, w), dtype=bool)
    for m in all_masks:
        union |= m

    # flower accents (variants 3-4)
    if v >= 2:
        frng = noise.rng_for("bush_flowers", variant, seed)
        colors = [ACCENTS["flower_red"], ACCENTS["flower_blue"],
                  ACCENTS["flower_yellow"]]
        for _ in range(2 + v % 2):
            fx = int(cx + frng.uniform(-12, 12))
            fy = int(base_y + frng.uniform(-14, -3))
            petal = np.zeros((h, w), dtype=bool)
            petal[fy:fy + 2, fx:fx + 2] = True
            petal &= union
            body.fill_mask(petal, colors[int(frng.integers(0, len(colors)))])
            core = np.zeros((h, w), dtype=bool)
            core[fy:fy + 1, fx + 1:fx + 2] = True
            body.fill_mask(core & union, RAMPS["straw"].steps[1])

    # final outer silhouette outline keeps the whole cluster closed
    outline_silhouette(body, union, RAMPS["leaf"].outline)

    anchor = (int(cx), int(base_y + 4))
    sh = Canvas(w, h)
    smask = shadow.ground_shadow_mask(w, h, anchor, 15.0, 5.0)
    shadow.cast_shadow(sh, smask, soft=1)
    colors_used = body.colors_used() | sh.colors_used()
    return AssetResult(
        category="nature", kind="bush", variant=variant, seed=seed,
        width=w, height=h, anchor=anchor, shadow=sh, parts={"body": body},
        rig=None, colors_used=colors_used,
    )
