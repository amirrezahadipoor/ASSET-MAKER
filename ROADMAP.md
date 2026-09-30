# ROADMAP — ASSET MAKER

Milestones are ticked only after their gate passes honestly. Never tick a
milestone whose gate failed.

## Milestones

- [x] M0 STYLE_GUIDE.md from the reference + repo skeleton + CI running with a
      trivial test
- [x] M1 Core: palette ramps, shading, auto outline, shadow, dither, export,
      manifest writer, naming. Gate: a sphere and a cube render in the style
- [x] M2 Recipe `bush` (many variants) + `rock` + `barrel` + `crate`
      Gate: side by side with the reference, honest critique
- [ ] M3 Recipe `tree` (leaf clusters, trunk, roots, shadow). Hardest static
      quality test; do not continue until it is convincingly close to the
      reference trees
- [ ] M4 Rig system: parts, bones, pivots, idle/walk animation exporter,
      Godot loader. Gate: rig recomposes to the full image
- [ ] M5 Recipe `chicken` (with rig, idle, walk, peck) and `statue` (knight
      on plinth, static + optional subtle rig)
- [ ] M6 Recipe `human` (modular parts: hair, tunic colors, 4 directions),
      docs: RECIPE_GUIDE.md so another AI can add a new recipe in one file
- [ ] M7 Polish: variant diversity, performance, README with every CLI command
      and the manifest schema

## Status log

### 2026-09-30 M0 — PASS
Built: STYLE_GUIDE.md (all rules sampled from reference/village.png pixel
data), repo skeleton, pytest suite, .github/workflows/render.yml. CI run
36688005937 completed **success** on GitHub (tests + 16-seed render +
artifact upload + previews committed to `render-output` branch).

### 2026-09-30 M1 — PASS
Built: core modules (palette ramps with hue-shift, planar+lambert shading,
closed 1 px auto-outline, Bayer dither, soft shadow, deterministic noise,
export/naming/manifest), rig base, QA gates, CLI (`make|list|sheet`),
sphere + cube style proofs. Gate: both render in the style — verified by
pixel-level inspection (compact top-left highlight island, clean ramp bands
like the reference rock, facet cracks, closed dark outline, soft bottom-right
shadow). All gates green; 20 seeds unique. Fixed along the way: dither noise
(reference uses clean bands on small masses), shading range compression
(planar-light blend), inverted cylinder light sign.

### 2026-09-30 M2 — PASS
Built: recipes rock (3 silhouettes), bush (4 layouts + flower accents),
barrel (2 sizes), crate (2 sizes), all seed-unique. Comparison artifacts:
`out/m2_vs_reference.png`, `out/contact_sheet_*.png`.
Quantitative style match: bush render mean RGB (0.258, 0.423, 0.135) vs
reference foliage (0.263, 0.425, 0.137); saturation 0.700 vs 0.688.
Honest critique vs reference:
- rock: close to the reference rock (bands, cracks, highlight island). Still
  slightly rounder than the reference's faceted silhouette.
- bush: canopy light flow (yellow-green top-left -> teal pocket bottom-right)
  matches; interior still more bandy than the reference's leaf texture;
  flowers are 2 px blobs, reference has distinct petals.
- barrel: stave/hoop/lid structure correct, cylindrical light correct; hoop
  contrast slightly heavy vs the reference's finer hoops.
- crate: planks, corner posts, nails and top-face gradient read like the
  reference crates; side face still flatter than the reference.
Gates: palette purity, alpha binary, closed outline, silhouette, light
direction, size limits, anchor, rig recompose, 20-seed diversity — all pass
(26 pytest tests).
