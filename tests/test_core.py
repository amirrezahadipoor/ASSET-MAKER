"""Core engine tests: determinism, naming, palette purity, manifest schema."""
from __future__ import annotations

import json
import re

import numpy as np
import pytest

from assetmaker.core import export, noise
from assetmaker.core.export import (AssetResult, layer_filename, save_png,
                                    save_sheet)
from assetmaker.core.palette import ALL_COLORS, RAMPS, make_ramp, rgba
from assetmaker.core.shapes import Canvas, ellipse_mask
from assetmaker.qa import gates
from assetmaker.recipes import catalog


def _render(kind: str, seed: int, variant: int = 1) -> tuple[AssetResult, dict]:
    catalog.load_all()
    res = catalog.get(kind).fn(seed, variant)
    return res, {}


# -- naming ----------------------------------------------------------------

def test_name_pattern():
    n = layer_filename("animal", "chicken", 1, 42, "full")
    assert n == "animal_chicken_v01_s42_full.png"
    n = layer_filename("nature", "bush", 3, 7, "part-leaves")
    assert n == "nature_bush_v03_s7_part-leaves.png"
    n = layer_filename("animal", "chicken", 1, 42, "sheet-walk")
    assert n == "animal_chicken_v01_s42_sheet-walk.png"
    n = layer_filename("nature", "bush", 3, 7, "shadow")
    assert n == "nature_bush_v03_s7_shadow.png"


def test_name_regex_examples():
    for s in ("animal_chicken_v01_s42_full.png",
              "nature_bush_v03_s7_part-head.png",
              "animal_chicken_v01_s42_sheet-walk.png",
              "nature_bush_v03_s7_shadow.png"):
        assert export.NAME_RE.match(s), s


def test_bad_names_rejected():
    with pytest.raises(ValueError):
        layer_filename("Animal", "chicken", 1, 42, "full")
    with pytest.raises(ValueError):
        layer_filename("animal", "chicken", 1, 42, "Full")
    with pytest.raises(ValueError):
        layer_filename("animal", "chicken", 1, 42, "part-Head")


# -- palette / determinism ---------------------------------------------------

def test_palette_complete():
    assert len(ALL_COLORS) > 40
    for ramp in RAMPS.values():
        for c in ramp.all_colors:
            assert c in ALL_COLORS


def test_rgba_validation():
    assert rgba("#53802c") == (0x53, 0x80, 0x2c, 255)
    with pytest.raises(ValueError):
        rgba("#12345g")


def test_make_ramp_hue_shift():
    ramp = make_ramp("tunic", "#4a6fd0")
    assert ramp.steps[2] == "#4a6fd0"
    assert ramp.shade(0.0) == ramp.steps[0]
    assert ramp.shade(1.0) == ramp.steps[-1]


def test_rng_deterministic():
    a = noise.rng_for("x", 1, 2).random(5)
    b = noise.rng_for("x", 1, 2).random(5)
    assert np.allclose(a, b)
    c = noise.rng_for("x", 1, 3).random(5)
    assert not np.allclose(a, c)


def test_png_bytes_deterministic(tmp_path):
    c = Canvas(16, 16)
    m = ellipse_mask(16, 16, 8, 8, 6, 5)
    c.fill_mask(m, "#53802c")
    p1, p2 = tmp_path / "a.png", tmp_path / "b.png"
    b1 = save_png(c, p1)
    b2 = save_png(c, p2)
    assert b1 == b2


# -- gates on the M1 demos ---------------------------------------------------

def test_sphere_passes_gates():
    res, _ = _render("sphere", 42)
    full = res.full()
    obj = res.parts["body"]
    qa = gates.evaluate(res, full, obj.alpha_mask(), recomposed=full)
    failed = [k for k, v in qa["checks"].items() if not v["passed"]]
    assert qa["passed"], f"failed checks: {failed}"


def test_cube_passes_gates():
    res, _ = _render("cube", 42)
    full = res.full()
    obj = res.parts["body"]
    qa = gates.evaluate(res, full, obj.alpha_mask(), recomposed=full)
    failed = [k for k, v in qa["checks"].items() if not v["passed"]]
    assert qa["passed"], f"failed checks: {failed}"


def test_seed_diversity_demos():
    for kind in ("sphere", "cube"):
        digests = []
        for seed in range(20):
            res, _ = _render(kind, seed)
            digests.append(res.full().buf.tobytes())
        ok, detail = gates.check_seed_diversity(digests)
        assert ok, f"{kind}: {detail}"


def test_alpha_binary_and_palette_on_demos():
    for kind in ("sphere", "cube"):
        res, _ = _render(kind, 7)
        full = res.full()
        ok, d = gates.check_alpha_binary(full)
        assert ok, d
        ok, d = gates.check_palette_only(res.colors_used)
        assert ok, d


# -- manifest schema ---------------------------------------------------------

def test_manifest_schema(tmp_path):
    from assetmaker.cli import export_asset

    res, _ = _render("sphere", 42)
    manifest = export_asset(res, tmp_path)
    for key in ("id", "category", "kind", "variant", "seed", "engine_version",
                "size", "anchor", "files", "rig", "palette", "qa"):
        assert key in manifest, key
    assert re.fullmatch(r"\d+\.\d+\.\d+", manifest["engine_version"])
    assert set(manifest["files"]) == {"full", "shadow", "parts", "sheets"}
    # every referenced file exists
    d = tmp_path / manifest["id"]
    assert (d / manifest["files"]["full"]).exists()
    assert (d / manifest["files"]["shadow"]).exists()
    for pf in manifest["files"]["parts"].values():
        assert (d / pf).exists()
    assert (d / "manifest.json").exists()
    loaded = json.loads((d / "manifest.json").read_text())
    assert loaded["id"] == manifest["id"]
