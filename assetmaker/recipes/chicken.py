"""Recipe: chicken (animal) — rigged, with idle / walk / peck sheets.

Reference study: tiny white bird (~18x16 at 1x), cream plumage with darker
cream shade, red comb + wattle, straw beak and legs, 1 px dark outline,
soft ground shadow. Rig: root/neck/head/wing/legs with real pivots; parts
recompose to the full image exactly (M4 gate).
"""
from __future__ import annotations

import numpy as np

from ..core import noise, primitives, shading, shadow, shapes
from ..core.export import AssetResult
from ..core.outline import outline_silhouette
from ..core.palette import RAMPS, make_ramp, register_ramp
from ..core.shapes import Canvas, line_mask, poly_mask
from ..rig import anim, skeleton
from .catalog import register

CREAM = RAMPS["cream"]
RED = RAMPS["cloth_red"]
STRAW = RAMPS["straw"]
DARK = "#10141f"

# deterministic variant body colors
HEN_BROWN = register_ramp(make_ramp("hen_brown", "#8a5a30"))
BODY_RAMPS = [CREAM, HEN_BROWN, CREAM]


def _draw_head(head: Canvas, hx: float, hy: float, ramp) -> np.ndarray:
    w, h = head.w, head.h
    mask = shapes.ellipse_mask(w, h, hx, hy, 5.0, 4.6)
    t = shading.radial_t(mask, hx, hy, 5.0, 4.6)
    shading.apply_shading(head, mask, t, ramp)
    # comb: 3 bumps on top
    for dx, dy, r in ((-2.6, -4.2, 1.8), (0, -5.0, 1.9), (2.6, -4.2, 1.8)):
        bump = shapes.ellipse_mask(w, h, hx + dx, hy + dy, r, r * 0.9)
        head.fill_mask(bump, RED.steps[2])
        head.fill_mask(shapes.boundary_mask(bump), RED.outline)
        mask |= bump
    # beak: straw triangle pointing right
    beak = poly_mask(w, h, [(hx + 4.2, hy - 0.8), (hx + 8.0, hy + 0.6),
                            (hx + 4.2, hy + 2.0)])
    head.fill_mask(beak, STRAW.steps[3])
    head.fill_mask(shapes.boundary_mask(beak), STRAW.outline)
    mask |= beak
    # wattle: red drop under the beak
    wat = shapes.ellipse_mask(w, h, hx + 3.4, hy + 3.2, 1.6, 2.0)
    head.fill_mask(wat, RED.steps[2])
    head.fill_mask(shapes.boundary_mask(wat), RED.outline)
    mask |= wat
    # eye: dark pixel + glint
    eye = np.zeros((h, w), dtype=bool)
    eye[int(hy - 1):int(hy) + 1, int(hx + 1):int(hx) + 2] = True
    head.fill_mask(eye, DARK)
    glint = np.zeros((h, w), dtype=bool)
    glint[int(hy - 1):int(hy), int(hx + 1):int(hx) + 2] = True
    head.fill_mask(glint, "#efe7c3")
    outline_silhouette(head, mask, ramp.outline)
    return mask


@register("chicken", "animal", has_rig=True,
          doc="rigged chicken: idle/walk/peck sheets, 3 colorways")
def make_chicken(seed: int, variant: int = 1) -> AssetResult:
    rng = noise.rng_for("chicken", variant, seed)
    ramp = BODY_RAMPS[(variant - 1) % 3]
    w, h = 40, 38
    ground_y = 32

    # ---------- geometry ----------
    bx, by = 17.0, 21.0           # body center
    hx, hy = 27.0, 12.5           # head center
    leg_top_y = 27.0

    parts: dict[str, Canvas] = {}

    # legs (back leg drawn first, darker)
    for name, lx, dark in (("leg-back", 14.0, True), ("leg-front", 20.0, False)):
        c = Canvas(w, h)
        leg = shapes.capsule_mask(w, h, lx, leg_top_y, lx - 1.0, ground_y - 1.0,
                                  1.3)
        foot = shapes.capsule_mask(w, h, lx - 1.0, ground_y - 1.0,
                                   lx + 2.6, ground_y - 1.0, 1.0)
        toe = shapes.capsule_mask(w, h, lx - 1.0, ground_y - 1.0,
                                  lx - 3.2, ground_y - 1.0, 0.9)
        m = leg | foot | toe
        color = STRAW.steps[1] if dark else STRAW.steps[3]
        c.fill_mask(m, color)
        outline_silhouette(c, m, STRAW.outline)
        parts[name] = c

    # tail: three feather spikes, back-left
    tail = Canvas(w, h)
    tmask = np.zeros((h, w), dtype=bool)
    for (px0, py0, px1, py1, px2, py2) in (
            (10.0, 17.0, 2.0, 12.0, 9.0, 21.0),
            (11.0, 16.0, 5.0, 9.5, 10.5, 19.5),
            (12.0, 15.5, 8.5, 8.0, 12.5, 18.5)):
        feather = poly_mask(w, h, [(px0, py0), (px1, py1), (px2, py2)])
        tmask |= feather
    t = shading.radial_t(tmask, 8.0, 13.0, 6.0, 6.0)
    shading.apply_shading(tail, tmask, t, ramp)
    outline_silhouette(tail, tmask, ramp.outline)
    parts["tail"] = tail

    # body: egg mass
    body = Canvas(w, h)
    bmask = shapes.ellipse_mask(w, h, bx, by, 9.5, 8.0)
    t = shading.radial_t(bmask, bx, by, 9.5, 8.0)
    # reference birds have a distinct shade crescent on the lower-right
    planar = shading.planar_light_t(bmask, bx, by, 9.5, 8.0)
    t = np.clip(t - 0.16 * (planar < 0.45), 0.0, 1.0)
    t = primitives._modulate(t, bmask, rng, 0.05, cell=6)
    shading.apply_shading(body, bmask, t, ramp)
    primitives.seed_nicks(body, bmask, ramp, rng, count=3)  # feather texture
    outline_silhouette(body, bmask, ramp.outline)
    parts["body"] = body

    # wing: overlapping ellipse with feather lines
    wing = Canvas(w, h)
    wmask = shapes.ellipse_mask(w, h, bx - 1.5, by + 0.5, 6.2, 5.0)
    t = shading.radial_t(wmask, bx - 1.5, by + 0.5, 6.2, 5.0)
    t = np.clip(t * 0.72 + 0.02, 0, 1)   # wing sits in the body's shade side
    shading.apply_shading(wing, wmask, t, ramp)
    for dy in (-1.0, 1.4):
        fl = line_mask(w, h, bx - 5.5, by + dy, bx + 3.2, by + dy + 0.8, 1)
        wing.fill_mask(fl & wmask & shapes.erode(wmask, 1), ramp.steps[1])
    outline_silhouette(wing, wmask, ramp.outline)
    parts["wing"] = wing

    # head part
    head = Canvas(w, h)
    _draw_head(head, hx, hy, ramp)
    parts["head"] = head

    # ---------- shadow ----------
    sh = Canvas(w, h)
    smask = shadow.ground_shadow_mask(w, h, (int(bx), ground_y), 11.0, 3.6)
    shadow.cast_shadow(sh, smask, soft=1)

    # ---------- rig ----------
    rig = skeleton.Rig()
    rig.add_bone("root", None, (int(bx), int(by)), length=8.0)
    rig.add_bone("tail", "root", (11, 17), length=6.0)
    rig.add_bone("neck", "root", (21, 15), length=5.0)
    rig.add_bone("head", "neck", (int(hx), int(hy)), length=5.0)
    rig.add_bone("wing", "root", (int(bx), int(by)), length=6.0)
    rig.add_bone("leg-back", "root", (14, int(leg_top_y)), length=5.0)
    rig.add_bone("leg-front", "root", (20, int(leg_top_y)), length=5.0)

    files_hint = {
        "leg-back": ("leg-back", 12), "tail": ("tail", 15),
        "body": ("body", 20), "leg-front": ("leg-front", 18),
        "wing": ("wing", 25), "head": ("head", 30),
    }
    pivots = {
        "leg-back": (14, int(leg_top_y)), "leg-front": (20, int(leg_top_y)),
        "tail": (11, 17), "body": (int(bx), int(by)),
        "wing": (int(bx), int(by)), "head": (22, 15),
    }
    bones_for = {
        "leg-back": "leg-back", "leg-front": "leg-front", "tail": "tail",
        "body": "root", "wing": "wing", "head": "head",
    }
    for pname, (_bone, z) in files_hint.items():
        rig.add_part(pname, f"part-{pname}.png", bones_for[pname],
                     pivots[pname], z)

    # ---------- animations ----------
    n = 6
    idle = anim.make_animation([
        anim.make_frame(bones={"neck": -3.0, "head": 2.0}, duration=1),
        anim.make_frame(root=(0, -1), bones={"neck": 0.0, "head": 0.0}),
        anim.make_frame(bones={"neck": 3.0, "head": -2.0}),
        anim.make_frame(root=(0, -1), bones={"neck": 0.0, "head": 0.0}),
    ], fps=5)
    walk = anim.make_animation([
        anim.make_frame(root=(0, -1), bones={"leg-front": 18.0,
                                             "leg-back": -18.0,
                                             "neck": -4.0, "tail": 4.0}),
        anim.make_frame(root=(0, 0), bones={"leg-front": 6.0,
                                            "leg-back": -6.0,
                                            "neck": -2.0, "tail": 2.0}),
        anim.make_frame(root=(0, -1), bones={"leg-front": -18.0,
                                             "leg-back": 18.0,
                                             "neck": 0.0, "tail": -2.0}),
        anim.make_frame(root=(0, 0), bones={"leg-front": -18.0,
                                            "leg-back": 18.0,
                                            "neck": -4.0, "tail": -4.0}),
        anim.make_frame(root=(0, -1), bones={"leg-front": 6.0,
                                             "leg-back": -6.0,
                                             "neck": -2.0, "tail": -2.0}),
        anim.make_frame(root=(0, 0), bones={"leg-front": 18.0,
                                            "leg-back": -18.0,
                                            "neck": 0.0, "tail": 2.0}),
    ], fps=8)
    peck = anim.make_animation([
        anim.make_frame(bones={"neck": 4.0, "head": -2.0}),
        anim.make_frame(bones={"neck": 28.0, "head": 14.0}),
        anim.make_frame(root=(0, 1), bones={"neck": 36.0, "head": 18.0}),
        anim.make_frame(bones={"neck": 12.0, "head": 4.0}),
    ], fps=6, loop=False)
    rig.animations = {"idle": idle, "walk": walk, "peck": peck}

    z_order = [p.name for p in rig.sorted_parts()]
    part_bone = {p.name: p.bone for p in rig.parts}
    part_pivot = {p.name: p.pivot for p in rig.parts}
    sheets = {
        "idle": anim.export_sheet(idle, parts, z_order, part_bone, part_pivot,
                                  shadow=sh),
        "walk": anim.export_sheet(walk, parts, z_order, part_bone, part_pivot,
                                  shadow=sh),
        "peck": anim.export_sheet(peck, parts, z_order, part_bone, part_pivot,
                                  shadow=sh),
    }

    colors_used = set(sh.colors_used())
    for p in parts.values():
        colors_used |= p.colors_used()
    return AssetResult(
        category="animal", kind="chicken", variant=variant, seed=seed,
        width=w, height=h, anchor=(int(bx), ground_y), shadow=sh,
        parts=parts, sheets=sheets, rig=rig.to_dict(), colors_used=colors_used,
    )
