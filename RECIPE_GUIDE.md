# RECIPE GUIDE — ASSET MAKER

How to add a new asset type in ONE file. Follow this contract exactly and the
QA gates will keep your art in `reference/village.png` style. Read
`STYLE_GUIDE.md` first — it is the law.

## 1. The contract

Create `assetmaker/recipes/<kind>.py`, register it, done:

```python
"""Recipe: lantern (prop) — one-paragraph description + reference notes."""
from __future__ import annotations

import numpy as np
from ..core import noise, primitives, shading, shadow, shapes
from ..core.export import AssetResult
from ..core.outline import outline_silhouette
from ..core.palette import RAMPS
from ..core.shapes import Canvas
from .catalog import register

@register("lantern", "prop", doc="iron lantern, 2 sizes")
def make_lantern(seed: int, variant: int = 1) -> AssetResult:
    rng = noise.rng_for("lantern", variant, seed)   # ALWAYS start here
    w, h = 24, 30
    body = Canvas(w, h)
    mask = shapes.rect_mask(w, h, 6, 10, 17, 24)     # your drawing...
    t = shading.radial_t(mask, 12, 17, 6, 8)          # top-left light!
    shading.apply_shading(body, mask, t, RAMPS["metal"])
    outline_silhouette(body, mask, RAMPS["metal"].outline)  # closed 1px

    anchor = (12, 25)                                # ground contact point
    sh = Canvas(w, h)
    smask = shadow.ground_shadow_mask(w, h, anchor, 8.0, 2.8)
    shadow.cast_shadow(sh, smask, soft=1)
    colors = body.colors_used() | sh.colors_used()
    return AssetResult(
        category="prop", kind="lantern", variant=variant, seed=seed,
        width=w, height=h, anchor=anchor, shadow=sh, parts={"body": body},
        rig=None, colors_used=colors,
    )
```

Then add the module to `load_all()` in `assetmaker/recipes/catalog.py`:
```python
from . import barrel, bush, ..., lantern  # noqa: F401
```

`python -m assetmaker make lantern --seed 42` now works, files are named
`prop_lantern_v01_s42_*.png`, and every QA gate runs on your output.

## 2. The rules (gate-enforced)

| rule | gate | notes |
|---|---|---|
| palette colors only | `palette_only` | RAMPS + ACCENTS + SHADOW_COLOR + registered ramps |
| alpha 0 or 255 | `alpha_binary` | never blend, never opacity |
| closed 1 px outline | `outline_closed` | `outline_silhouette()` after all painting |
| top-left light | `light_direction` | `radial_t`/`vertical_t`/`box_t` do it for you |
| size per category | `size_limits` | prop 8-64, nature 12-128, animal 8-48, human 20-48, structure 16-192 |
| anchor inside image, on the ground | `anchor_inside` | bottom-center of the footprint |
| parts recompose to full | `rig_recompose` | always true if you build parts honestly |
| 20 seeds unique, none broken | tests | put `rng` into SOMETHING visible (nicks, mottle, seam jitter) |

## 3. Drawing toolkit (core/primitives.py)

- `sphere_mass`, `dome_mass` (organic lobes: bushes, canopy, rocks)
- `cylinder_mass` (trunks, posts, barrels), `box_mass` (crates, buildings)
- `crack_lines` (rocks), `seed_nicks` (weathering + seed uniqueness)
- `plank_texture`, `tile_rows` (roofs)
- `shading.radial_t` (dome), `shading.vertical_t` (cylinder),
  `shading.box_t` (3/4 box), `shading.planar_light_t` (big flat lit faces)
- `shapes.*_mask` rasterizers, `noise.rng_for/value_noise_2d/radial_blob`

Paint order inside a recipe: draw back parts first; each part gets its own
outline; composite order IS the z order.

## 4. Variants and seeds

- `variant` (1+) changes STRUCTURE: silhouette, colors, direction, outfit.
  Consecutive variants must differ (gate `test_variants_differ`).
- `seed` changes DETAIL within that structure. Always begin with
  `rng = noise.rng_for("<kind>", variant, seed)` and feed `rng` to every
  noise/jitter call. Seeds must never look identical.

## 5. New colors

Never hand-pick stray hexes. Either use `RAMPS[...]` entries, or generate a
deterministic hue-shifted ramp and register it:

```python
from ..core.palette import make_ramp, register_ramp
TUNIC = register_ramp(make_ramp("tunic_teal", "#2f7a74"))
```

`make_ramp` enforces the hue-shift rule (shadows toward plum/teal, highlights
toward yellow). `register_ramp` makes the colors legal for `palette_only`.

## 6. Rigged assets (optional)

```python
rig = skeleton.Rig()
rig.add_bone("root", None, (cx, cy), length=8.0)      # parents first!
rig.add_bone("head", "root", (cx, cy - 8), length=5.0)
rig.add_part("body", "part-body.png", "root", (cx, cy), z=10)  # z = draw order
rig.add_part("head", "part-head.png", "head", (cx, cy - 8), z=20)
rig.animations = {"idle": anim.make_animation([...]), ...}
```

- One `Canvas` per part, full asset size, transparent elsewhere.
- Pivots on real joints; rotations small (≤25°), nearest-neighbor.
- `sheets["walk"] = anim.export_sheet(...)` (frames are full-size canvases).
- Set `has_rig=True` in `@register(...)`.

## 7. Checklist before you commit a recipe

1. `python -m assetmaker make <kind> --seed 42 --variant 1` prints `[PASS]`.
2. Look at the PNG (pixel-map if needed) and compare to the reference crop:
   light top-left? closed outline? hue-shifted shadows? no stray colors?
3. `python -m assetmaker sheet <kind>` — 16 seeds: none identical, none
   cropped, none noisy.
4. `pytest -q` green.
