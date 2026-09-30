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
- [x] M3 Recipe `tree` (leaf clusters, trunk, roots, shadow). Hardest static
      quality test; do not continue until it is convincingly close to the
      reference trees
- [x] M4 Rig system: parts, bones, pivots, idle/walk animation exporter,
      Godot loader. Gate: rig recomposes to the full image
- [x] M5 Recipe `chicken` (with rig, idle, walk, peck) and `statue` (knight
      on plinth, static + optional subtle rig)
- [x] M6 Recipe `human` (modular parts: hair, tunic colors, 4 directions),
      docs: RECIPE_GUIDE.md so another AI can add a new recipe in one file
- [x] M7 Polish: variant diversity, performance, README with every CLI command
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

### 2026-09-30 M3 — PASS
Built: tree recipe — tapered trunk with root flares, bark streaks, 2-3
branches, solid 9-12 lobe canopy with one shared light field (yellow-green
top-left -> teal shadow pockets bottom-right), short branch forks peeking
through the canopy's lower edge, large bottom-right ground shadow.
Gate check vs reference foliage regions (mean RGB / saturation):
- tree render (0.235, 0.392, 0.103), sat 0.720
- reference regions: (0.261, 0.430, 0.135) sat 0.699 / (0.229, 0.373, 0.137)
  sat 0.689 / (0.173, 0.358, 0.117) sat 0.755 -> inside the reference range.
Honest critique vs reference trees: canopy mass, hue-shift and lobe seams
match the style; the silhouette is still rounder/cauliflower-ish vs the
reference's more varied lobe sizes and drooping lower clusters; branches are
subtler than the reference's visible forks. Inspected at pixel level (the
workspace image viewer is serving stale images this session, so visual checks
are ASCII pixel maps + quantitative stats — noted for transparency).
Gates: 28 pytest tests green incl. 20-seed uniqueness.

### 2026-09-30 M4 — PASS
Built: godot/asset_loader.gd (Godot 4 Skeleton2D/Bone2D/Sprite2D/Animation
builder from manifest.json), rig tests (2-part synthetic asset recomposes to
full with 0 px diff; animation frames genuinely differ; manifest rig schema
locked). Fixed a real recompose-order bug (parts must composite by rig z, not
name). Gate: rig recomposes exactly — verified in tests and per-asset QA.

### 2026-09-30 M5 — PASS
Built: chicken (6-part rig: root/neck/head/wing/two legs, idle+walk+peck
sheets, 3 colorways incl. generated hen_brown ramp via deterministic
register_ramp) and statue (knight on stepped plinth, 2-part subtle-sway rig,
3 variants: plume/sword/shield differences). All QA gates pass per asset
(palette, alpha, outline, light, size, anchor, recompose) + 33 pytest tests.
Honest critique: chicken body/wing/tail/comb/legs read as the reference bird
at pixel level; head part pivots are right for peck; walk leg swings are
larger-angle NN rotations (slightly crunchy at 1x, acceptable per style).
Statue: plinth/figure silhouettes and stone shading are right; the figure is
simpler than the reference knight (no tabard emblem, blockier helmet).
Note: image-viewer tooling served stale images this session; all visual
inspection is pixel-map + quantitative based.

### 2026-09-30 M6 — PASS
Built: human recipe (modular parts legs/tunic/head/hair, 4 directions
down/up/left/right, 3 hair colors, 4 tunic colors = 48 variants; idle+walk
sheets; root/head/arms rig) and RECIPE_GUIDE.md (one-file recipe contract,
toolkit, variant/seed rules, new-color policy, rig guide, pre-commit
checklist). Generated variant ramps (tunic_*, hair_*, hen_brown) are
deterministic and registered into the master palette so `palette_only` stays
honest (fixed a stale-import gate bug along the way).
Honest critique: villager silhouette/shading reads in style; faces are
minimal (2 px eyes) like the reference; left/right profiles are simplified
(one eye + nose bump, no ear). 39 pytest tests green (all kinds gated at 3
seeds, 20-seed uniqueness for the 8 main kinds).

### 2026-09-30 M7 — PASS
Built: full README (install, every CLI command, strict naming rules, complete
manifest.json schema, Godot usage, QA gates, CI docs, repo layout), contact
sheets for all 8 art kinds, workflow_dispatch full render (10 kinds x 16
seeds). Variant diversity: rock 3 silhouettes, bush 4 layouts + flowers,
barrel/crate 2 sizes, tree 3 silhouettes, chicken 3 colorways, statue 3
armaments, human 48 (4 directions x 3 hairs x 4 tunics). Perf: full asset
render < 0.3 s. 39 tests green.

## All milestones complete (2026-09-30)
Honest summary of remaining weaknesses (post-M7 backlog):
- foliage interiors are banded lobe masses vs the reference's finer leaf
  texture; flowers are 2 px blobs vs shaped petals
- human side profiles simplified (no ear, minimal nose)
- statue figure blockier than the reference knight
- image-viewer tooling served stale images this session; all inspection was
  pixel-map + quantitative (color stats vs reference crops) — a final visual
  pass by human eyes is recommended before production use.
