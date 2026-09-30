"""Export: strict naming, deterministic PNGs, manifest.json writer.

Naming (never deviate, engine chooses all names):
    {category}_{kind}_v{VV}_s{seed}_{layer}.png
    layer = full | part-{partname} | sheet-{anim} | shadow
Output folder: out/{category}_{kind}_v{VV}_s{seed}/ + manifest.json
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from .palette import ALL_COLORS
from .shapes import Canvas

ENGINE_VERSION = "1.0.0"

NAME_RE = re.compile(
    r"^(?P<category>[a-z]+)_(?P<kind>[a-z0-9]+)_v(?P<variant>\d{2})"
    r"_s(?P<seed>\d+)_(?P<layer>full|shadow|part-[a-z0-9-]+|sheet-[a-z0-9-]+)\.png$"
)

LAYER_RE = re.compile(r"^(full|shadow|part-[a-z0-9-]+|sheet-[a-z0-9-]+)$")


def asset_id(category: str, kind: str, variant: int, seed: int) -> str:
    return f"{category}_{kind}_v{variant:02d}_s{seed}"


def out_dir(root: Path, category: str, kind: str, variant: int, seed: int) -> Path:
    return Path(root) / asset_id(category, kind, variant, seed)


def layer_filename(category: str, kind: str, variant: int, seed: int,
                   layer: str) -> str:
    if not LAYER_RE.match(layer):
        raise ValueError(f"bad layer name {layer!r}")
    for token in (category, kind):
        if not re.fullmatch(r"[a-z0-9]+", token):
            raise ValueError(f"bad name token {token!r}")
    return f"{category}_{kind}_v{variant:02d}_s{seed}_{layer}.png"


def save_png(canvas: Canvas, path: Path) -> bytes:
    """Deterministic PNG write: fixed encoder settings, no metadata."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    img = canvas.to_pil()
    img.save(path, format="PNG", optimize=False, compress_level=6)
    return path.read_bytes()


def save_sheet(frames: list[Canvas], path: Path, pad: int = 2) -> bytes:
    """Horizontal sprite strip from full-frame canvases (animation sheets)."""
    if not frames:
        raise ValueError("no frames")
    w = sum(f.w for f in frames) + pad * (len(frames) - 1)
    h = max(f.h for f in frames)
    sheet = Canvas(w, h)
    x = 0
    for f in frames:
        sheet.buf[:f.h, x:x + f.w] = f.buf
        x += f.w + pad
    return save_png(sheet, Path(path))


# --------------------------------------------------------------------------
# Manifest
# --------------------------------------------------------------------------

@dataclass
class AssetResult:
    """Everything one asset generation produces."""

    category: str
    kind: str
    variant: int
    seed: int
    width: int
    height: int
    anchor: tuple[int, int]
    shadow: Canvas
    parts: dict[str, Canvas] = field(default_factory=dict)  # z-ordered
    sheets: dict[str, list[Canvas]] = field(default_factory=dict)
    rig: dict | None = None
    colors_used: set[str] = field(default_factory=set)

    def full(self) -> Canvas:
        """Composite shadow + parts in z order -> the full image."""
        c = Canvas(self.width, self.height)
        c.composite(self.shadow)
        for _, p in self.parts.items():
            c.composite(p)
        return c


def build_manifest(res: AssetResult, files: dict, qa: dict,
                   palette: list[str]) -> dict:
    m = {
        "id": asset_id(res.category, res.kind, res.variant, res.seed),
        "category": res.category,
        "kind": res.kind,
        "variant": res.variant,
        "seed": res.seed,
        "engine_version": ENGINE_VERSION,
        "size": [res.width, res.height],
        "anchor": [int(res.anchor[0]), int(res.anchor[1])],
        "files": files,
        "rig": res.rig,
        "palette": palette,
        "qa": qa,
    }
    return m


def write_manifest(path: Path, manifest: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, sort_keys=False) + "\n",
                    encoding="utf-8")


def palette_for(colors_used: set[str]) -> list[str]:
    """Sorted subset of the master palette actually used by this asset."""
    return [c for c in ALL_COLORS if c in colors_used]
