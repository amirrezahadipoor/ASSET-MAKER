"""Recipe: crate (prop) — front-facing plank box with corner posts + nails.

Reference study: crates read as front boxes at 3/4 with a shallow top face;
2-3 horizontal planks (light on top, dark at the bottom), dark corner posts,
nails at the corners, hard 1 px outline."""
from __future__ import annotations

import numpy as np

from ..core import noise, primitives, shading, shadow, shapes
from ..core.export import AssetResult
from ..core.outline import outline_silhouette
from ..core.palette import RAMPS
from ..core.shapes import Canvas, line_mask, poly_mask
from .catalog import register

WOOD = RAMPS["wood"]


@register("crate", "prop", doc="plank crate with corner posts, 2 sizes")
def make_crate(seed: int, variant: int = 1) -> AssetResult:
    rng = noise.rng_for("crate", variant, seed)
    v = (variant - 1) % 2
    w, h = 38, 38
    cx = w // 2
    top_y = [10, 12][v]
    hw = [11.0, 12.5][v]      # half width of the front face
    hd = [3.0, 3.5][v]        # top face depth (shallow)
    h_side = [14.0, 13.0][v]
    side_w = 5                # left side face visible width

    body = Canvas(w, h)
    # faces: shallow diamond top, front face, right side face
    top = poly_mask(w, h, [(cx - hw, top_y + hd), (cx, top_y),
                           (cx + hw, top_y + hd), (cx, top_y + 2 * hd)])
    front_x0, front_x1 = int(cx - hw), int(cx)
    front = shapes.rect_mask(w, h, front_x0, top_y + hd, front_x1 - 1,
                             int(top_y + hd + h_side))
    side_x0, side_x1 = int(cx), int(cx + hw)
    side = poly_mask(w, h, [(cx, top_y + 2 * hd), (cx + hw, top_y + hd),
                            (cx + hw, top_y + hd + h_side),
                            (cx, top_y + 2 * hd + h_side)])
    union = top | front | side

    # face shading: top light (left-bright gradient), front mid, side dark
    t = shading.box_t(union, top, front, side)
    t = primitives._modulate(t, union, rng, 0.10, cell=5)
    xs_all = np.arange(w)[None, :]
    top_grad = 0.72 + 0.26 * np.clip(1.0 - (xs_all - (cx - hw)) / max(1.0, 2 * hw), 0, 1)
    for face, base in ((top, top_grad), (front, 0.58), (side, 0.24)):
        ft = np.zeros_like(t)
        if np.isscalar(base):
            ft[face] = base
        else:
            ft[face] = np.broadcast_to(base, (h, w))[face]
        shading.apply_shading(body, face, ft, WOOD, dither=False)
    outline_silhouette(body, union, WOOD.outline)

    # horizontal planks on the front face (light top, dark bottom seams)
    rows = 3 if v == 0 else 2
    y_a, y_b = top_y + hd, top_y + hd + h_side
    row_h = (y_b - y_a) / rows
    jitter = int(rng.integers(-1, 2))
    for i in range(rows):
        yy = int(y_a + i * row_h) + (jitter if i else 0)
        seam = np.zeros((h, w), dtype=bool)
        seam[yy:yy + 1] = True
        body.fill_mask(seam & shapes.erode(front, 1), WOOD.steps[1])
        if i % 2 == 0:
            hl = np.zeros((h, w), dtype=bool)
            hl[yy + 1:yy + 2] = True
            body.fill_mask(hl & shapes.erode(front, 1), WOOD.steps[5])
    # plank seams on the side face (vertical)
    for x in (int(cx + hw * 0.5),):
        col = np.zeros((h, w), dtype=bool)
        col[:, x:x + 1] = True
        body.fill_mask(col & shapes.erode(side, 1), WOOD.steps[1])

    # corner posts: 2 px dark columns at the front face edges
    for x in (front_x0, front_x1 - 2):
        post = np.zeros((h, w), dtype=bool)
        post[:, x:x + 2] = True
        body.fill_mask(post & front, WOOD.steps[0])
    # nails at the post tops/bottoms
    nail_color = RAMPS["metal"].steps[1]
    for x in (front_x0 + 1 + int(rng.integers(-1, 2)),
              front_x1 - 1 + int(rng.integers(-1, 2))):
        for yy in (int(y_a + 1 + rng.integers(0, 2)),
                   int(y_b - 2 + rng.integers(0, 2))):
            nail = np.zeros((h, w), dtype=bool)
            nail[yy:yy + 1, x:x + 1] = True
            body.fill_mask(nail & front, nail_color)
    # top face plank seams
    for ox in (-hw * 0.5, hw * 0.5):
        sl = line_mask(w, h, cx + ox - hd, top_y + hd + ox * 0.5,
                       cx + ox + hd, top_y + hd - ox * 0.5, 1)
        body.fill_mask(sl & top & shapes.erode(union, 1), WOOD.steps[1])
    primitives.seed_nicks(body, union, WOOD, rng, count=3)
    outline_silhouette(body, union, WOOD.outline)

    anchor = (int(cx), int(top_y + 2 * hd + h_side))
    sh = Canvas(w, h)
    smask = shadow.ground_shadow_mask(w, h, anchor, hw * 1.0, hw * 0.34)
    shadow.cast_shadow(sh, smask, soft=1)
    colors_used = body.colors_used() | sh.colors_used()
    return AssetResult(
        category="prop", kind="crate", variant=variant, seed=seed,
        width=w, height=h, anchor=anchor, shadow=sh, parts={"body": body},
        rig=None, colors_used=colors_used,
    )
