# STYLE GUIDE — ASSET MAKER

Target style: `reference/village.png` — top-down 3/4 pixel art village (gazeb at
1366x614; art is authored at 1x game scale). Every rule below was extracted by
sampling the reference image (region color histograms + saturation/hue
analysis), not by guessing. Recipes MUST follow these rules or fail QA.

## 1. Camera & projection

- Top-down 3/4 ("3/4 overhead"): objects seen from above and slightly in front.
  Verticals stay vertical; top faces (roofs, barrel lids, crate tops) are
  visible as shallow ellipses/parallelograms.
- No perspective convergence. Parallel lines stay parallel.

## 2. Light

- ONE light source, from the **top-left**. Never changes.
- Highlights sit on the **top-left** of every mass (canopy lobes, roof tiles,
  barrel staves, statue shoulders). Shades fall on the **bottom-right**.
- QA check `light_direction`: mean luminance of the top-left quadrant of the
  silhouette must exceed the bottom-right quadrant.

## 3. Hue-shifted shading (the signature of this style)

Shading steps are NOT darker/lighter copies of the base color. Sampled proof
from the reference foliage: mid `#53802c` (hue 92°) → deep shadow `#0b3836`
(hue 187°) → highlight `#abb948` (hue 68°).

| family | shadow steps shift toward | highlight steps shift toward |
|---|---|---|
| greens (grass, foliage) | teal / blue-green (hue +60..+100°) | yellow-green (hue −20..−30°) |
| browns (wood, bark, roofs) | red-violet / plum (hue +10..+20°, sat up) | orange-yellow (sat down, val up) |
| grays (stone, metal) | blue-olive (cooler) | warm cream (warmer) |

Ramps are authored dark→light with this shift baked in (see
`assetmaker/core/palette.py`). Never generate shading by multiplying RGB.

## 4. Palette

Master palette = the sampled colors of `reference/village.png` organized into
material ramps. **Every output pixel must be one of these colors.** Alpha is
always 0 or 255 (no anti-aliasing, ever).

### Ramps (outline first, then dark→light)

- **leaf** (foliage, bushes, treetops): `#10141f` · `#0b3836` `#124f33`
  `#2c4418` `#42640a` `#367a0c` `#53802c` `#64bd18` `#76bc3a` `#abb948`
- **grass** (ground, tufts): `#243512` · `#293e16` `#2c4418` `#3f671d`
  `#4c7529` `#53802c` `#6ba33a` `#64bd18`
- **bark** (trunks, logs): `#1c1815` · `#24170c` `#3c230e` `#523319`
  `#5b381a` `#764d29` `#aa7447`
- **wood** (planks, crates, fences): `#231a14` · `#3c230e` `#432d19`
  `#57492f` `#645433` `#764d29` `#917444` `#aa7447`
- **roof_orange** (tiles): `#24170c` · `#3c230e` `#5b3412` `#895426`
  `#a46732` `#d18340`
- **roof_red** (tiles): `#1c1815` · `#39160b` `#4e2214` `#783621`
  `#ae583c` `#c66343` `#ea8868`
- **stone_warm** (statues, plaster): `#10141f` · `#383931` `#494a42`
  `#605d4e` `#6e6a5e` `#96928e` `#b1af9a` `#c9c6b3`
- **stone_cool** (rocks, chimneys): `#121723` · `#343130` `#494744`
  `#6b6d69` `#878480` `#aea9a5` `#c9cdc1`
- **wall_timber** (house walls): `#1c1815` · `#3c230e` `#523319`
  `#5c5037` `#786845` `#8a774f` `#918b69`
- **dirt** (paths, bare ground): `#645433` · `#7e6621` `#917e55`
  `#a38957` `#ad9a70` `#bc9d5f` `#d9cba6`
- **canvas** (cloth, paper, sails): `#57503c` · `#8a8064` `#ae9d74`
  `#cebd91` `#d9cba6` `#efe7c3`
- **metal** (iron, steel): `#10141f` · `#383931` `#494747` `#6b6d69`
  `#96928e` `#c9cdc1`
- **skin**: `#231a14` · `#7a3c28` `#a05a3c` `#c66343` `#df8568` `#f0a888`
- **cloth_red**: `#1c1815` · `#4e2214` `#6a2021` `#952c2d` `#c66343`
- **cloth_blue** (flowers, tunics): `#121723` · `#374155` `#47546e`
  `#5981d4` `#6890ed` `#97add8` `#c6daff`
- **straw** (dry grass, thatch, yellow flowers): `#392f15` · `#505023`
  `#7e6621` `#98942c` `#abb948` `#d0c060`
- **cream** (white feathers, plaster light): `#57503c` · `#8a8064`
  `#b1a888` `#d9cba6` `#efe7c3`

### Non-ramp colors

- **shadow** (ground contact shadow): `#2c4418` (sampled grass-shadow).
  Drawn ONLY in the `shadow` layer / under the asset.

## 5. Outlines

- Closed, exactly **1 px**, on every silhouette and every major internal part
  boundary (canopy vs trunk, roof vs wall, head vs body).
- Outline color = the ramp's `outline` entry (near-black with a hue tint —
  navy for foliage/stone, brown-black for wood/roofs). NOT pure black except
  where the reference uses it (`#000000` on buildings).
- Outline occupies the outermost pixel ring of the shape (inside the fill's
  bounding mask), never 2 px, never gapped. QA checks both.
- Sub-parts inside a silhouette (e.g. tile rows) use 1 px separation lines in
  the material's dark steps, not full outline color.

## 6. Shading rules

- 5–8 visible steps per material ramp (reference is never 2-tone).
- Banding is allowed and preferred; dithering (ordered Bayer 4x4) only at:
  ramp-step transitions on curved masses (canopies, barrels), and the soft rim
  of ground shadows. Never random noise dithering.
- Curved masses (sphere-like): pseudo-3D lambert from a height dome, quantized
  to the ramp. The highlight "island" sits top-left of center.
- Box-like masses: 3 faces — top = light step, left = mid, right = shade, with
  the top face 1–2 steps brighter than the left face.

## 7. Ground shadows

- Every freestanding asset gets a soft ground shadow, offset to the
  **bottom-right** of the contact point (light is top-left). Offset ≈ 12–20%
  of asset width; ellipse wider than the base.
- Color `#2c4418`, edges softened with Bayer dither dropout (alpha stays
  0/255). No shadow outlines.

## 8. Foliage (the quality bar)

- Canopies are **clusters of overlapping lobes** (3–8 blobs), not one ellipse.
  Lobe silhouettes are irregular (low-frequency radial noise, ±15–25% radius).
- Inside a canopy: bright lobes toward top-left, deep teal shadow pockets
  toward bottom-right, mid greens between. Lobe separation lines are 1 px dark
  (`#124f33`/`#0b3836`), drawn where lobes overlap.
- Trees: trunk with slight taper + 2–3 root flares, 2–3 branches entering the
  canopy. Trunk is 5–8 px wide at 1x for a 64–80 px tree.
- Bushes: 3–5 lobes, no trunk, wider than tall.

## 9. Sizes (1x pixels, category limits for QA)

| category | size range | examples in reference |
|---|---|---|
| prop | 8–64 px | barrel ≈26x30, crate ≈22x22, stump ≈30x22 |
| nature | 12–128 px | rock ≈26x22, bush ≈30x24, tree ≈72x96 |
| animal | 8–48 px | chicken ≈18x16 |
| human | 20–48 px | villager ≈26x34 |
| structure | 16–192 px | statue ≈40x80, house ≈120x110 |

- Anchor (`anchor` in manifest) = ground contact point, always inside the
  image, at the bottom-center of the object's footprint.

## 10. Rig & layers

- Layers: `shadow` (bottom), `part-*` (z-ordered), composited = `full`.
  Rig recomposition must reproduce `full` exactly (pixel diff = 0).
- Pivots are on real joints (hip, neck, shoulder, canopy/trunk junction).
- Animation = per-frame bone rotations (small angles, ≤25°) + root offsets.
  Nearest-neighbor rotation only; no smoothing.

## 11. Determinism

- Same (kind, variant, seed) ⇒ byte-identical PNGs (fixed Pillow output
  settings, numpy PCG64 streams seeded from SHA-256 of the asset id).
- No clock, no platform randomness, no dict-order dependence.

## 12. Naming (strict)

```
{category}_{kind}_v{VV}_s{seed}_{layer}.png
layer ∈ {full, shadow, part-{partname}, sheet-{anim}}
out/{category}_{kind}_v{VV}_s{seed}/  + manifest.json
```

The engine chooses all names. Callers never name files.
