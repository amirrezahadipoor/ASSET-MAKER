"""Recipe: human (human) — modular villager: hair + tunic parts, 4 directions.

Reference study: ~26x34 villagers with skin heads, dark hair, colored tunics,
tiny 2 px eyes, 1 px outlines. Variant scheme (48 combos):
    direction = (variant-1) % 4          -> down, up, left, right
    hair      = ((variant-1)//4) % 3     -> brown, black, blond
    tunic     = ((variant-1)//12) % 4    -> red, blue, green, brown
Parts: legs / tunic / head / hair (rig-recomposable). Rig: root + head + arms.
"""
from __future__ import annotations

import numpy as np

from ..core import noise, primitives, shading, shadow, shapes
from ..core.export import AssetResult
from ..core.outline import outline_silhouette
from ..core.palette import RAMPS, make_ramp, register_ramp
from ..core.shapes import Canvas, line_mask
from ..rig import anim, skeleton
from .catalog import register

SKIN = RAMPS["skin"]
DARK = "#10141f"
EYE = "#10141f"

TUNICS = [
    register_ramp(make_ramp("tunic_red", "#a03c2e")),
    register_ramp(make_ramp("tunic_blue", "#3a5fa8")),
    register_ramp(make_ramp("tunic_green", "#4a7a3a")),
    register_ramp(make_ramp("tunic_brown", "#8a6a42")),
]
HAIRS = [
    register_ramp(make_ramp("hair_brown", "#6a4526")),
    register_ramp(make_ramp("hair_black", "#2a2a30")),
    register_ramp(make_ramp("hair_blond", "#c8a548")),
]
PANTS = RAMPS["wall_timber"]
DIRS = ("down", "up", "left", "right")


@register("human", "human", has_rig=True,
          doc="modular villager: 4 directions, 3 hairs, 4 tunic colors")
def make_human(seed: int, variant: int = 1) -> AssetResult:
    rng = noise.rng_for("human", variant, seed)
    v = max(0, variant - 1)
    facing = DIRS[v % 4]
    hair_ramp = HAIRS[(v // 4) % 3]
    tunic = TUNICS[(v // 12) % 4]

    w, h = 32, 43
    cx = 16
    ground_y = 39
    head_y = 10.0

    parts: dict[str, Canvas] = {}

    # ---- legs + boots ----
    legs = Canvas(w, h)
    lmask = shapes.capsule_mask(w, h, cx - 2.5, 24, cx - 3, ground_y - 2, 2.2)
    lmask |= shapes.capsule_mask(w, h, cx + 2.5, 24, cx + 3, ground_y - 2, 2.2)
    t = shading.vertical_t(lmask)
    shading.apply_shading(legs, lmask, t, PANTS)
    for bx in (cx - 2, cx + 2):
        boot = shapes.rect_mask(w, h, bx - 2, ground_y - 3, bx + 2, ground_y - 1)
        legs.fill_mask(boot & lmask, PANTS.steps[0])
    outline_silhouette(legs, lmask, PANTS.outline)
    parts["legs"] = legs

    # ---- tunic (torso + arms) ----
    tunic_c = Canvas(w, h)
    tmask = shapes.rect_mask(w, h, cx - 6, 17, cx + 6, 26)
    tmask |= shapes.ellipse_mask(w, h, cx, 17.5, 6.2, 3.2)
    # arms
    tmask |= shapes.capsule_mask(w, h, cx - 7, 18, cx - 9, 25, 2.0)
    tmask |= shapes.capsule_mask(w, h, cx + 7, 18, cx + 9, 25, 2.0)
    # hands (skin) at arm ends
    hands = shapes.ellipse_mask(w, h, cx - 9, 26, 1.7, 1.9)
    hands |= shapes.ellipse_mask(w, h, cx + 9, 26, 1.7, 1.9)
    planar = shading.planar_light_t(tmask, cx, 20, 8, 6)
    tt = np.clip(0.28 + 0.5 * planar, 0, 1)
    tt = primitives._modulate(tt, tmask, rng, 0.05, cell=5)
    shading.apply_shading(tunic_c, tmask, tt, tunic)
    primitives.seed_nicks(tunic_c, tmask, tunic, rng, count=2)  # cloth wear
    tunic_c.fill_mask(hands & tmask, SKIN.steps[3])
    # belt
    belt = shapes.rect_mask(w, h, cx - 6, 22, cx + 6, 23)
    tunic_c.fill_mask(belt & tmask, PANTS.steps[0])
    # collar hint
    collar = shapes.rect_mask(w, h, cx - 2, 17, cx + 2, 18)
    tunic_c.fill_mask(collar & tmask, tunic.steps[0])
    outline_silhouette(tunic_c, tmask, tunic.outline)
    parts["tunic"] = tunic_c

    # ---- head (skin) ----
    head = Canvas(w, h)
    hmask = shapes.ellipse_mask(w, h, cx, head_y, 4.4, 4.8)
    t = shading.radial_t(hmask, cx, head_y, 4.4, 4.8)
    shading.apply_shading(head, hmask, t, SKIN)
    if facing == "down":
        for ex in (cx - 2, cx + 2):
            eye = np.zeros((h, w), dtype=bool)
            eye[int(head_y):int(head_y) + 1, ex:ex + 1] = True
            head.fill_mask(eye, EYE)
    elif facing in ("left", "right"):
        side = -1 if facing == "left" else 1
        eye = np.zeros((h, w), dtype=bool)
        eye[int(head_y):int(head_y) + 1, int(cx + 1.6 * side):int(cx + 1.6 * side) + 1] = True
        head.fill_mask(eye, EYE)
        nose = shapes.ellipse_mask(w, h, cx + 4.2 * side, head_y + 1.4, 1.1, 1.1)
        head.fill_mask(nose & hmask, SKIN.steps[3])
    # neck
    neck = shapes.rect_mask(w, h, cx - 1, 13, cx + 1, 15)
    head.fill_mask(neck, SKIN.steps[1])
    outline_silhouette(head, hmask | neck, SKIN.outline)
    parts["head"] = head

    # ---- hair (modular) ----
    hair = Canvas(w, h)
    if facing == "up":
        hairmask = shapes.ellipse_mask(w, h, cx, head_y - 0.4, 4.6, 5.0)
    elif facing == "left":
        hairmask = shapes.ellipse_mask(w, h, cx + 0.6, head_y - 0.8, 4.4, 4.4)
        hairmask |= shapes.rect_mask(w, h, cx + 1, head_y - 5, cx + 5, head_y + 2)
    elif facing == "right":
        hairmask = shapes.ellipse_mask(w, h, cx - 0.6, head_y - 0.8, 4.4, 4.4)
        hairmask |= shapes.rect_mask(w, h, cx - 5, head_y - 5, cx - 1, head_y + 2)
    else:
        hairmask = shapes.ellipse_mask(w, h, cx, head_y - 1.2, 4.6, 4.2)
        hairmask |= shapes.rect_mask(w, h, cx - 5, head_y - 5, cx + 5, head_y - 2)
    t = shading.radial_t(hairmask, cx, head_y - 1, 4.8, 4.4)
    shading.apply_shading(hair, hairmask, t, hair_ramp)
    primitives.seed_nicks(hair, hairmask, hair_ramp, rng, count=2)  # strands
    outline_silhouette(hair, hairmask, hair_ramp.outline)
    parts["hair"] = hair

    # ---- shadow ----
    sh = Canvas(w, h)
    smask = shadow.ground_shadow_mask(w, h, (cx, ground_y), 7.5, 2.6)
    shadow.cast_shadow(sh, smask, soft=1)

    # ---- rig ----
    rig = skeleton.Rig()
    rig.add_bone("root", None, (cx, 24), length=8.0)
    rig.add_bone("head", "root", (cx, 15), length=6.0)
    rig.add_bone("arm-l", "root", (cx - 7, 18), length=8.0)
    rig.add_bone("arm-r", "root", (cx + 7, 18), length=8.0)
    rig.add_part("legs", "part-legs.png", "root", (cx, 24), z=10)
    rig.add_part("tunic", "part-tunic.png", "root", (cx, 22), z=20)
    rig.add_part("head", "part-head.png", "head", (cx, 15), z=30)
    rig.add_part("hair", "part-hair.png", "head", (cx, 15), z=40)

    idle = anim.make_animation([
        anim.make_frame(bones={"head": -2.0}),
        anim.make_frame(root=(0, -1)),
        anim.make_frame(bones={"head": 2.0}),
        anim.make_frame(root=(0, -1)),
    ], fps=4)
    walk = anim.make_animation([
        anim.make_frame(root=(0, -1), bones={"arm-l": 14.0, "arm-r": -14.0,
                                             "head": -2.0}),
        anim.make_frame(bones={"arm-l": 4.0, "arm-r": -4.0}),
        anim.make_frame(root=(0, -1), bones={"arm-l": -14.0, "arm-r": 14.0,
                                             "head": 2.0}),
        anim.make_frame(bones={"arm-l": -4.0, "arm-r": 4.0}),
    ], fps=6)
    rig.animations = {"idle": idle, "walk": walk}

    z_order = [p.name for p in rig.sorted_parts()]
    part_bone = {p.name: p.bone for p in rig.parts}
    part_pivot = {p.name: p.pivot for p in rig.parts}
    sheets = {
        "idle": anim.export_sheet(idle, parts, z_order, part_bone, part_pivot,
                                  shadow=sh),
        "walk": anim.export_sheet(walk, parts, z_order, part_bone, part_pivot,
                                  shadow=sh),
    }

    colors_used = set(sh.colors_used())
    for p in parts.values():
        colors_used |= p.colors_used()
    return AssetResult(
        category="human", kind="human", variant=variant, seed=seed,
        width=w, height=h, anchor=(cx, ground_y), shadow=sh, parts=parts,
        sheets=sheets, rig=rig.to_dict(), colors_used=colors_used,
    )
