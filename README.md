# ASSET MAKER

Fully procedural 2D pixel-art asset engine. Given a name like `bush`,
`statue`, `chicken`, it generates final PNG art, a matching rig/skeleton JSON,
and a manifest — all by code and math, no downloaded art, no AI images.

Style target: `reference/village.png` (top-down 3/4 pixel art). The rules are
codified in [STYLE_GUIDE.md](STYLE_GUIDE.md). Progress lives in
[ROADMAP.md](ROADMAP.md).

## Quick start

```bash
pip install -e ".[dev]"
pytest -q                                  # tests + quality gates
python -m assetmaker list                  # registered kinds
python -m assetmaker make bush --seed 7 --variant 3
python -m assetmaker sheet bush --count 16 # contact sheet vs reference
```

Outputs go to `out/{category}_{kind}_v{VV}_s{seed}/` with strict naming —
the engine chooses every filename. Full CLI + manifest schema docs arrive in
M7; recipe authoring docs in [RECIPE_GUIDE.md](RECIPE_GUIDE.md) (M6).

## CI

`.github/workflows/render.yml` runs tests, quality gates, and renders assets on
every push and on demand (`workflow_dispatch` with kind/seeds/variant inputs).
Artifacts are uploaded per run; browsable previews are committed to the
`render-output` branch. The job fails if any quality gate fails.
