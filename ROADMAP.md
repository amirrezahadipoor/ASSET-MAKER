# ROADMAP — ASSET MAKER

Milestones are ticked only after their gate passes honestly. Never tick a
milestone whose gate failed.

## Milestones

- [ ] M0 STYLE_GUIDE.md from the reference + repo skeleton + CI running with a
      trivial test
- [ ] M1 Core: palette ramps, shading, auto outline, shadow, dither, export,
      manifest writer, naming. Gate: a sphere and a cube render in the style
- [ ] M2 Recipe `bush` (many variants) + `rock` + `barrel` + `crate`
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

(append one entry per milestone attempt: date, what was built, gate result,
honest critique pointer)
