"""M1 style-proof recipes: a sphere and a cube rendered in the reference style.

Gate (ROADMAP M1): both must look like they belong in reference/village.png —
hue-shifted ramps, top-left light, closed 1 px outline, soft ground shadow."""
from __future__ import annotations

import numpy as np

from ..core import noise, primitives, shadow
from ..core.export import AssetResult
from ..core.palette import RAMPS
from ..core.shapes import Canvas
from .catalog import register


def _finish(kind: str, category: str, variant: int, seed: int, w: int, h: int,
            body: Canvas, obj_mask: np.ndarray, anchor: tuple[int, int],
            base_rx: float) -> AssetResult:
    sh = Canvas(w, h)
    smask = shadow.ground_shadow_mask(w, h, anchor, base_rx,
                                      max(2.0, base_rx * 0.36))
    shadow.cast_shadow(sh, smask, soft=2)
    colors = body.colors_used() | sh.colors_used()
    return AssetResult(
        category=category, kind=kind, variant=variant, seed=seed,
        width=w, height=h, anchor=anchor, shadow=sh,
        parts={"body": body}, rig=None, colors_used=colors,
    )


@register("sphere", "demo", doc="M1 gate: shaded sphere in the reference style")
def make_sphere(seed: int, variant: int = 1) -> AssetResult:
    rng = noise.rng_for("demo_sphere", variant, seed)
    w, h = 38, 38
    body = Canvas(w, h)
    cx, cy, r = w // 2, h // 2 - 3, 13.0
    ramp = RAMPS["stone_cool"]
    mask = primitives.sphere_mass(body, cx, cy, r, ramp, rng=rng, mottle=0.05)
    primitives.crack_lines(body, mask, ramp,
                           noise.rng_for("demo_sphere_crack", variant, seed),
                           count=2)
    anchor = (int(cx), int(cy + r))
    return _finish("sphere", "demo", variant, seed, w, h, body, mask, anchor,
                   r * 0.92)


@register("cube", "demo", doc="M1 gate: 3/4 box in the reference style")
def make_cube(seed: int, variant: int = 1) -> AssetResult:
    rng = noise.rng_for("demo_cube", variant, seed)
    w, h = 40, 42
    body = Canvas(w, h)
    cx, y_top, hw, hd, h_side = w // 2, 6.0, 15.0, 7.5, 17.0
    ramp = RAMPS["wood"]
    mask = primitives.box_mass(body, cx, y_top, hw, hd, h_side, ramp,
                               rng=rng, plank_step=0.05)
    # iron corner nails (reference crates have dark corner studs)
    for sx, sy in ((cx - hw + 2, y_top + hd + 3), (cx + hw - 3, y_top + hd + 3),
                   (cx - 3, y_top + 2 * hd + 3)):
        nail = np.zeros((h, w), dtype=bool)
        nail[int(sy):int(sy) + 2, int(sx):int(sx) + 2] = True
        body.fill_mask(nail & mask, ramp.steps[0])
    anchor = (int(cx), int(y_top + 2 * hd + h_side))
    return _finish("cube", "demo", variant, seed, w, h, body, mask, anchor,
                   hw * 0.95)
