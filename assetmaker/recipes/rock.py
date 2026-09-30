"""Recipe: rock (nature) — lumpy stone mass, crack facets, flat bottom.

Reference study (STYLE_GUIDE §8 + rock samples): irregular silhouette, clean
banding, compact top-left highlight, 2-3 facet cracks, sits flat on ground.
"""
from __future__ import annotations

import numpy as np

from ..core import noise, primitives, shading, shadow, shapes
from ..core.export import AssetResult
from ..core.outline import outline_silhouette
from ..core.palette import RAMPS
from ..core.shapes import Canvas
from .catalog import register

RAMP = RAMPS["stone_cool"]


@register("rock", "nature", doc="lumpy ground rock, 3 silhouettes")
def make_rock(seed: int, variant: int = 1) -> AssetResult:
    rng = noise.rng_for("rock", variant, seed)
    v = (variant - 1) % 3
    w, h = 34, 28
    cx = w // 2 + int(rng.integers(-1, 2))
    rx = [11.0, 13.0, 9.0][v]
    ry = [8.0, 7.5, 9.5][v]
    cy = 12 + (0 if v != 2 else -1)

    body = Canvas(w, h)
    radii = noise.radial_blob(rng, lobes=7 + v, ruggedness=0.20 + 0.04 * v)
    mask = shapes.blob_mask(w, h, cx, cy, rx, ry, radii)
    # flat ground contact: cut the bottom and square it off slightly
    ground_y = int(cy + ry * 0.82)
    mask[ground_y:, :] = False
    ys, xs = np.nonzero(mask)
    if len(ys):
        mask[ground_y - 1:ground_y, xs.min():xs.max() + 1] = True

    t = shading.radial_t(mask, cx, cy - 1, rx * 1.05, ry * 1.15)
    t = shading.normalize_t(t, mask)
    t = primitives._modulate(t, mask, rng, 0.05, cell=4)
    shading.apply_shading(body, mask, t, RAMP)
    primitives.crack_lines(body, mask, RAMP,
                           noise.rng_for("rock_crack", variant, seed),
                           count=2 + v % 2)
    outline_silhouette(body, mask, RAMP.outline)

    anchor = (int(cx), int(ground_y))
    sh = Canvas(w, h)
    smask = shadow.ground_shadow_mask(w, h, anchor, rx * 1.02, ry * 0.42)
    shadow.cast_shadow(sh, smask, soft=1)
    colors = body.colors_used() | sh.colors_used()
    return AssetResult(
        category="nature", kind="rock", variant=variant, seed=seed,
        width=w, height=h, anchor=anchor, shadow=sh, parts={"body": body},
        rig=None, colors_used=colors,
    )
