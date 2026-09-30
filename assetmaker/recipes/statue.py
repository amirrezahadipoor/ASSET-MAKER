"""Recipe: statue (structure) — knight on a stepped plinth.

Reference study: gray-warm stone figure standing on a square pedestal,
~40x80 at 1x, hue-shifted stone ramp, hard 1 px outline, tall soft shadow
falling right. Static art + optional subtle rig (figure sway idle).
"""
from __future__ import annotations

import numpy as np

from ..core import noise, primitives, shading, shadow, shapes
from ..core.export import AssetResult
from ..core.outline import outline_silhouette
from ..core.palette import RAMPS
from ..core.shapes import Canvas, line_mask, poly_mask
from ..rig import anim, skeleton
from .catalog import register

STONE = RAMPS["stone_warm"]
METAL = RAMPS["metal"]


@register("statue", "structure", has_rig=True,
          doc="knight statue on stepped plinth, subtle sway rig")
def make_statue(seed: int, variant: int = 1) -> AssetResult:
    rng = noise.rng_for("statue", variant, seed)
    w, h = 52, 108
    cx = 26
    ground_y = 100

    parts: dict[str, Canvas] = {}

    # ---- plinth (static base part) ----
    plinth = Canvas(w, h)
    pmask = np.zeros((h, w), dtype=bool)
    # two stepped slabs
    pmask |= shapes.rect_mask(w, h, cx - 18, ground_y - 12, cx + 17, ground_y - 1)
    pmask |= shapes.rect_mask(w, h, cx - 14, ground_y - 22, cx + 13, ground_y - 12)
    # pedestal column
    pmask |= shapes.rect_mask(w, h, cx - 9, ground_y - 38, cx + 8, ground_y - 22)
    t = shading.box_t(pmask, shapes.rect_mask(w, h, cx - 18, ground_y - 14,
                                              cx + 17, ground_y - 12),
                      shapes.rect_mask(w, h, cx - 18, ground_y - 38,
                                       cx - 2, ground_y - 1),
                      shapes.rect_mask(w, h, cx + 1, ground_y - 38,
                                       cx + 17, ground_y - 1))
    t = primitives._modulate(t, pmask, rng, 0.05, cell=5)
    shading.apply_shading(plinth, pmask, t, STONE)
    # slab seams
    for yy in (ground_y - 12, ground_y - 22):
        seam = shapes.rect_mask(w, h, cx - 18, yy - 1, cx + 17, yy - 1)
        plinth.fill_mask(seam & pmask, STONE.steps[0])
    # left face lighter edge
    edge = shapes.rect_mask(w, h, cx - 18, ground_y - 12, cx - 17, ground_y - 1)
    plinth.fill_mask(edge & pmask, STONE.steps[-2])
    outline_silhouette(plinth, pmask, STONE.outline)
    parts["plinth"] = plinth

    # ---- figure (rig part) ----
    fig = Canvas(w, h)
    fmask = np.zeros((h, w), dtype=bool)
    fy = ground_y - 38  # top of plinth
    # legs + boots
    fmask |= shapes.capsule_mask(w, h, cx - 3, fy - 18, cx - 3, fy - 1, 2.2)
    fmask |= shapes.capsule_mask(w, h, cx + 3, fy - 18, cx + 3, fy - 1, 2.2)
    # torso (tabard)
    fmask |= poly_mask(w, h, [(cx - 6, fy - 18), (cx + 6, fy - 18),
                              (cx + 7, fy - 40), (cx - 7, fy - 40)])
    # shoulders + arms
    fmask |= shapes.capsule_mask(w, h, cx - 7, fy - 38, cx - 9, fy - 22, 2.0)
    fmask |= shapes.capsule_mask(w, h, cx + 7, fy - 38, cx + 10, fy - 26, 2.0)
    # head + helmet
    fmask |= shapes.ellipse_mask(w, h, cx, fy - 46, 4.2, 4.6)
    fmask |= poly_mask(w, h, [(cx - 4, fy - 48), (cx + 4, fy - 48),
                              (cx, fy - 55)])
    v = (variant - 1) % 3
    # plume (variant: side / none / other side)
    if v != 1:
        side = -1 if v == 0 else 1
        fmask |= shapes.capsule_mask(w, h, cx, fy - 54,
                                     cx + 3 * side, fy - 60, 1.4)
    # sword: at the side / raised / resting on the shoulder
    if v == 0:
        fmask |= shapes.capsule_mask(w, h, cx + 10, fy - 28, cx + 11, fy - 6,
                                     1.2)
        fmask |= shapes.capsule_mask(w, h, cx + 8, fy - 28, cx + 13, fy - 28,
                                     1.1)
    elif v == 1:
        # shield on the left arm + short sword raised
        fmask |= shapes.ellipse_mask(w, h, cx - 11, fy - 30, 3.6, 5.2)
        fmask |= shapes.capsule_mask(w, h, cx + 9, fy - 34, cx + 12, fy - 52,
                                     1.2)
        fmask |= shapes.capsule_mask(w, h, cx + 8, fy - 34, cx + 13, fy - 34,
                                     1.1)
    else:
        fmask |= shapes.capsule_mask(w, h, cx + 10, fy - 30, cx + 12, fy - 10,
                                     1.2)
        fmask |= shapes.capsule_mask(w, h, cx + 6, fy - 44, cx + 15, fy - 48,
                                     1.3)

    t = shading.box_t(
        fmask,
        shapes.rect_mask(w, h, cx - 8, fy - 55, cx + 8, fy - 48),
        shapes.rect_mask(w, h, cx - 9, fy - 55, cx - 1, fy - 1),
        shapes.rect_mask(w, h, cx + 1, fy - 55, cx + 13, fy - 1))
    t = primitives._modulate(t, fmask, rng, 0.06, cell=5)
    shading.apply_shading(fig, fmask, t, STONE)
    # tabard detail: belt + fold line
    belt = shapes.rect_mask(w, h, cx - 6, fy - 26, cx + 6, fy - 24)
    fig.fill_mask(belt & fmask, METAL.steps[1])
    fold = line_mask(w, h, cx, fy - 40, cx, fy - 19, 1)
    fig.fill_mask(fold & fmask & shapes.erode(fmask, 1), STONE.steps[1])
    # sword highlight edge
    sw_hi = line_mask(w, h, cx + 10, fy - 27, cx + 11, fy - 7, 1)
    fig.fill_mask(sw_hi & fmask & shapes.erode(fmask, 1), METAL.steps[-1])
    # plinth-facing highlight on the left shoulder
    outline_silhouette(fig, fmask, STONE.outline)
    parts["figure"] = fig

    # ---- shadow ----
    sh = Canvas(w, h)
    smask = shadow.ground_shadow_mask(w, h, (cx, ground_y), 22.0, 5.5)
    shadow.cast_shadow(sh, smask, soft=1)

    # ---- rig (subtle sway) ----
    rig = skeleton.Rig()
    rig.add_bone("base", None, (cx, ground_y - 12), length=26.0)
    rig.add_bone("figure", "base", (cx, fy), length=30.0)
    rig.add_part("plinth", "part-plinth.png", "base", (cx, ground_y - 12), z=10)
    rig.add_part("figure", "part-figure.png", "figure", (cx, fy), z=20)
    sway = anim.make_animation([
        anim.make_frame(bones={"figure": -1.2}),
        anim.make_frame(bones={"figure": 0.0}),
        anim.make_frame(bones={"figure": 1.2}),
        anim.make_frame(bones={"figure": 0.0}),
    ], fps=2)
    rig.animations = {"idle": sway}

    z_order = [p.name for p in rig.sorted_parts()]
    sheets = {
        "idle": anim.export_sheet(
            sway, parts, z_order,
            {p.name: p.bone for p in rig.parts},
            {p.name: p.pivot for p in rig.parts}, shadow=sh),
    }

    colors_used = set(sh.colors_used())
    for p in parts.values():
        colors_used |= p.colors_used()
    return AssetResult(
        category="structure", kind="statue", variant=variant, seed=seed,
        width=w, height=h, anchor=(cx, ground_y), shadow=sh, parts=parts,
        sheets=sheets, rig=rig.to_dict(), colors_used=colors_used,
    )
