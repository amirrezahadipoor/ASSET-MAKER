"""Recipe: barrel (prop) — bulging stave cylinder, iron hoops, lid.

Reference study: barrels are ~26x30 px, wood staves with 1 px vertical seams,
2-3 dark iron hoops with a light top edge, elliptical lid with plank lines,
cylindrical cross-light (bright left edge, dark right edge)."""
from __future__ import annotations

import numpy as np

from ..core import noise, primitives, shading, shadow, shapes
from ..core.export import AssetResult
from ..core.outline import outline_silhouette
from ..core.palette import RAMPS
from ..core.shapes import Canvas, line_mask
from .catalog import register

WOOD = RAMPS["wood"]
METAL = RAMPS["metal"]


def _barrel_mask(w: int, h: int, cx: float, y0: float, y1: float,
                 r0: float, r1: float) -> np.ndarray:
    """Bulging barrel silhouette: radius r0 at ends, r1 at the middle."""
    m = np.zeros((h, w), dtype=bool)
    for y in range(int(y0), int(y1) + 1):
        t = (y - y0) / max(1.0, (y1 - y0))
        r = r0 + (r1 - r0) * np.sin(np.pi * t) ** 0.8
        row = shapes.ellipse_mask(w, h, cx, y, r, 0.6)
        m[y] |= row[y]
    return m


@register("barrel", "prop", doc="wooden barrel with iron hoops, 2 sizes")
def make_barrel(seed: int, variant: int = 1) -> AssetResult:
    rng = noise.rng_for("barrel", variant, seed)
    v = (variant - 1) % 2
    w, h = 36, 42
    cx = w // 2
    y0, y1 = [12, 14][v], [33, 35][v]
    r0, r1 = [8.5, 9.5][v], [11.0, 12.5][v]

    body = Canvas(w, h)
    mask = _barrel_mask(w, h, cx, y0, y1, r0, r1)

    # cylindrical shading (light from the left), then outline
    t = shading.vertical_t(mask)
    t = shading.normalize_t(t, mask)
    t = primitives._modulate(t, mask, rng, 0.03, cell=6)
    shading.apply_shading(body, mask, t, WOOD)
    outline_silhouette(body, mask, WOOD.outline)

    # stave seams: 1 px vertical dark lines inside the silhouette
    xs = np.nonzero(mask.any(axis=0))[0]
    x0, x1 = int(xs[0]), int(xs[-1])
    span = x1 - x0
    for frac in (0.30, 0.55, 0.78):
        x = int(x0 + span * frac) + int(rng.integers(-1, 2))
        col = line_mask(w, h, x, y0, x, y1, 1) & mask
        body.fill_mask(col & shapes.erode(mask, 1), WOOD.steps[1])

    # iron hoops: 2-3 thin dark bands with a subtle light top edge
    hoops = [0.28, 0.55] if v == 0 else [0.24, 0.50, 0.76]
    for frac in hoops:
        y = int(y0 + (y1 - y0) * frac) + int(rng.integers(-1, 2))
        band = np.zeros((h, w), dtype=bool)
        band[y:y + 3] = True
        band &= mask
        body.fill_mask(band, METAL.steps[0])
        top_line = np.zeros((h, w), dtype=bool)
        top_line[y:y + 1] = True
        body.fill_mask(top_line & mask, METAL.steps[2])
        bot_line = np.zeros((h, w), dtype=bool)
        bot_line[y + 2:y + 3] = True
        body.fill_mask(bot_line & mask, WOOD.steps[0])

    # lid: elliptical top with planks + dark rim
    lid = shapes.ellipse_mask(w, h, cx, y0, r0 * 1.02, r0 * 0.62)
    t_lid = shading.radial_t(lid, cx - 1, y0 - 1, r0 * 1.3, r0 * 0.9)
    t_lid = shading.normalize_t(t_lid, lid)
    shading.apply_shading(body, lid, t_lid, WOOD)
    for dy in (-2, 1):
        pl = line_mask(w, h, cx - r0, y0 + dy, cx + r0, y0 + dy, 1) & lid
        body.fill_mask(pl & shapes.erode(lid, 1), WOOD.steps[1])
    # inner rim shadow ring
    rim = lid & ~shapes.ellipse_mask(w, h, cx, y0, r0 * 0.82, r0 * 0.46)
    body.fill_mask(rim, WOOD.steps[1])
    hi = np.zeros((h, w), dtype=bool)
    hi[int(y0 - r0 * 0.42):int(y0 - r0 * 0.42) + 1,
       int(cx - r0 * 0.5):int(cx + r0 * 0.5)] = True
    body.fill_mask(hi & lid, WOOD.steps[-1])
    outline_silhouette(body, lid, WOOD.outline)
    # re-outline the whole silhouette so the lid seam doesn't break it
    outline_silhouette(body, mask | lid, WOOD.outline)

    anchor = (int(cx), int(y1 + 1))
    sh = Canvas(w, h)
    smask = shadow.ground_shadow_mask(w, h, anchor, r1 * 1.05, r1 * 0.38)
    shadow.cast_shadow(sh, smask, soft=1)
    colors_used = body.colors_used() | sh.colors_used()
    return AssetResult(
        category="prop", kind="barrel", variant=variant, seed=seed,
        width=w, height=h, anchor=anchor, shadow=sh, parts={"body": body},
        rig=None, colors_used=colors_used,
    )
