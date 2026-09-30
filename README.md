# ASSET MAKER

Fully procedural 2D pixel-art asset engine. Give it a name — `bush`, `rock`,
`barrel`, `crate`, `tree`, `chicken`, `statue`, `human` — and it generates:

1. final PNG art (all layers, strict naming),
2. a matching rig/skeleton as JSON (derived from the drawing geometry),
3. a `manifest.json` per asset,
4. sprite-sheet animations (`idle`, `walk`, `peck` where rigged),

everything by code and math. No downloaded art, no AI image generation, no
external asset packs. Same seed = byte-identical output.

Style target: `reference/village.png` (top-down 3/4 pixel art). Rules are
codified in [STYLE_GUIDE.md](STYLE_GUIDE.md); progress in
[ROADMAP.md](ROADMAP.md); recipe authoring in
[RECIPE_GUIDE.md](RECIPE_GUIDE.md).

## Install

```bash
pip install -e ".[dev]"        # Python 3.11+, Pillow + numpy + pytest only
```

## CLI — every command

```bash
# generate one asset (all layers + manifest; runs every QA gate)
python -m assetmaker make <kind> --seed N --variant V
python -m assetmaker make chicken --seed 42 --variant 1

# render N consecutive seeds starting at --seed (used by CI)
python -m assetmaker make tree --seed 42 --seeds 16 --variant 2

# skip QA (debug only)
python -m assetmaker make rock --seed 7 --no-qa

# choose the output root (default: out/)
python -m assetmaker make barrel --seed 7 --out /tmp/assets

# list registered kinds (category, static|rigged, doc)
python -m assetmaker list

# contact sheet: N seeds side by side + a crop of the reference
python -m assetmaker sheet <kind> --count 16 --seed 42 --variant 1
python -m assetmaker sheet bush --output contact_sheet.png
```

`make` exits non-zero if any quality gate fails, so it can gate CI directly.

## Output naming (strict — the engine chooses all names)

```
out/{category}_{kind}_v{VV}_s{seed}/
    {category}_{kind}_v{VV}_s{seed}_full.png          # composited art
    {category}_{kind}_v{VV}_s{seed}_shadow.png        # ground shadow layer
    {category}_{kind}_v{VV}_s{seed}_part-{name}.png   # one layer per rig part
    {category}_{kind}_v{VV}_s{seed}_sheet-{anim}.png  # animation strip
    manifest.json
```

Examples: `animal_chicken_v01_s42_full.png`,
`nature_bush_v03_s7_part-leaves.png`,
`animal_chicken_v01_s42_sheet-walk.png`. Layer names match
`full | shadow | part-{a-z0-9-} | sheet-{a-z0-9-}`; categories are
`nature | prop | structure | animal | human | demo`.

## manifest.json schema

```jsonc
{
  "id": "animal_chicken_v01_s42",        // {category}_{kind}_v{VV}_s{seed}
  "category": "animal",
  "kind": "chicken",
  "variant": 1,
  "seed": 42,
  "engine_version": "1.0.0",
  "size": [40, 38],                       // canvas w, h in px
  "anchor": [17, 32],                     // ground contact point (inside image)
  "files": {
    "full": "animal_chicken_v01_s42_full.png",
    "shadow": "animal_chicken_v01_s42_shadow.png",
    "parts": { "body": "..._part-body.png", "head": "..._part-head.png", ... },
    "sheets": { "idle": "..._sheet-idle.png", "walk": "...", "peck": "..." }
  },
  "rig": null | {
    "bones": [
      { "name": "root", "parent": null, "pos": [17, 21], "rot": 0, "length": 8 },
      { "name": "neck", "parent": "root", "pos": [21, 15], "rot": 0, "length": 5 }
    ],
    "parts": [
      { "name": "body", "file": "..._part-body.png", "bone": "root",
        "pivot": [17, 21], "z": 20 }
    ],
    "animations": {
      "idle": { "loop": true, "fps": 5, "frames": [
        { "root": [0, -1], "bones": { "neck": -3 }, "duration": 1 } ] }
    }
  },
  "palette": ["#10141f", "#0b3836", ...], // exact colors used (all from the
                                          // master palette, hue-shifted ramps)
  "qa": {
    "passed": true,
    "checks": {
      "palette_only":     { "passed": true, "detail": "..." },
      "alpha_binary":     { "passed": true, "detail": "..." },
      "outline_closed":   { "passed": true, "detail": "..." },
      "silhouette_readable": { "passed": true, "detail": "..." },
      "light_direction":  { "passed": true, "detail": "..." },
      "size_limits":      { "passed": true, "detail": "..." },
      "anchor_inside":    { "passed": true, "detail": "..." },
      "rig_recompose":    { "passed": true, "detail": "0/N pixels differ" }
    }
  }
}
```

Conventions the engine guarantees:

- `alpha` is always 0 or 255; every pixel color is in `palette`.
- The outline is closed and 1 px (`outline_closed`).
- Light comes from the top-left (`light_direction`).
- Rig parts recomposited in `z` order + shadow = `full`, byte-exact
  (`rig_recompose`).
- The rig is derived from the same geometry that draws the art — skeleton
  positions always match the image.

## Godot 4

`godot/asset_loader.gd` builds a scene from a manifest folder:

```gdscript
var scene := AssetLoader.load_asset("res://assets/animal_chicken_v01_s42")
add_child(scene)
scene.get_node("AnimationPlayer").play("walk")
```

It creates Skeleton2D + Bone2D hierarchy, one Sprite2D per part (nearest
filter), the shadow sprite, and an AnimationPlayer library with one clip per
manifest animation.

## Quality gates (run on every asset, enforced in CI)

automatic (`assetmaker/qa/gates.py`): palette purity, binary alpha, closed
1 px outline, silhouette readability (no specks/crops/noise), light
direction, category size limits, anchor validity, rig recomposition, and
20-seed diversity (none identical, none broken).

manual gate: `python -m assetmaker sheet <kind>` renders
`contact_sheet.png`-style comparisons (16 seeds next to a reference crop) for
written critique — see the Status log in [ROADMAP.md](ROADMAP.md).

## CI (GitHub Actions)

`.github/workflows/render.yml` on every `push` and `workflow_dispatch`
(inputs: `kind`, `seeds`, `variant`): installs, runs pytest (gates), renders
assets + contact sheets, uploads everything as artifacts, and commits
previews into `previews/` on the `render-output` branch for browsing in the
repo. The job fails if any quality gate fails.

## Repo layout

```
assetmaker/core/      palette, shading, outline, dither, shapes, noise,
                      shadow, primitives, export (naming + manifest)
assetmaker/rig/       skeleton.py (bones/parts), anim.py (frame/sheet export)
assetmaker/recipes/   one file per kind, registered in catalog.py
assetmaker/qa/        gates.py (automatic checks)
tests/                determinism, naming, gates, rig recompose, recipes
godot/asset_loader.gd Godot 4 loader
reference/            village.png (style source)
```
