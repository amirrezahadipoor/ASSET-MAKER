"""M4 rig gate: parts/bones/pivots, animation export, Godot manifest, and —
the hard gate — rig parts recompose to the full image exactly."""
from __future__ import annotations

import numpy as np
import pytest

from assetmaker.core.export import save_png, save_sheet
from assetmaker.core.palette import RAMPS
from assetmaker.core.shapes import Canvas, ellipse_mask
from assetmaker.rig import anim, skeleton


def _build_two_part_asset() -> tuple[Canvas, dict[str, Canvas], skeleton.Rig]:
    """Synthetic rigged asset: a head lobe over a body lobe."""
    w, h = 32, 32
    shadow = Canvas(w, h)
    shadow.fill_mask(ellipse_mask(w, h, 16, 27, 9, 3), "#2c4418")

    body = Canvas(w, h)
    bm = ellipse_mask(w, h, 16, 19, 8, 8)
    body.fill_mask(bm, RAMPS["leaf"].steps[4])
    body.fill_mask(ellipse_mask(w, h, 13, 16, 3, 3), RAMPS["leaf"].steps[7])

    head = Canvas(w, h)
    hm = ellipse_mask(w, h, 16, 9, 5, 5)
    head.fill_mask(hm, RAMPS["leaf"].steps[5])

    rig = skeleton.Rig()
    rig.add_bone("root", None, (16, 19), length=8.0)
    rig.add_bone("neck", "root", (16, 13), length=6.0)
    rig.add_part("body", "part-body.png", "root", (16, 19), z=10)
    rig.add_part("head", "part-head.png", "neck", (16, 12), z=20)
    return shadow, {"body": body, "head": head}, rig


def test_rig_recomposes_to_full():
    shadow, parts, rig = _build_two_part_asset()
    full = Canvas(32, 32)
    full.composite(shadow)
    full.composite(parts["body"])
    full.composite(parts["head"])
    recomposed = Canvas(32, 32)
    recomposed.composite(shadow)
    for p in rig.sorted_parts():
        recomposed.composite(parts[p.name])
    assert (recomposed.buf == full.buf).all(), "rig recompose mismatch"


def test_rig_structure_and_manifest_fields():
    _, _, rig = _build_two_part_asset()
    d = rig.to_dict()
    assert [b["name"] for b in d["bones"]] == ["root", "neck"]
    assert d["bones"][1]["parent"] == "root"
    assert d["parts"][0]["z"] <= d["parts"][1]["z"]
    for part in d["parts"]:
        assert set(part) == {"name", "file", "bone", "pivot", "z"}
    for bone in d["bones"]:
        assert set(bone) == {"name", "parent", "pos", "rot", "length"}


def test_animation_export():
    shadow, parts, rig = _build_two_part_asset()
    idle = anim.make_animation([
        anim.make_frame(bones={"neck": -4.0}),
        anim.make_frame(root=(0, -1), bones={"neck": 0.0}),
        anim.make_frame(bones={"neck": 4.0}),
        anim.make_frame(root=(0, -1), bones={"neck": 0.0}),
    ], fps=6)
    rig.animations["idle"] = idle
    z_order = [p.name for p in rig.sorted_parts()]
    part_bone = {p.name: p.bone for p in rig.parts}
    part_pivot = {p.name: p.pivot for p in rig.parts}
    frames = anim.export_sheet(idle, parts, z_order, part_bone, part_pivot,
                               shadow=shadow)
    assert len(frames) == 4
    # frames must differ (rotation actually applied)
    assert frames[0].buf.tobytes() != frames[1].buf.tobytes()
    assert frames[0].buf.tobytes() != frames[2].buf.tobytes()
    d = rig.to_dict()
    assert "idle" in d["animations"]
    assert d["animations"]["idle"]["fps"] == 6


def test_sheet_and_part_files_named(tmp_path):
    from assetmaker.core.export import layer_filename, save_sheet

    shadow, parts, rig = _build_two_part_asset()
    for name, c in parts.items():
        save_png(c, tmp_path / layer_filename("demo", "rig", 1, 1,
                                              f"part-{name}"))
    idle = anim.make_animation([anim.make_frame(), anim.make_frame()],
                               fps=4)
    frames = anim.export_sheet(
        idle, parts, [p.name for p in rig.sorted_parts()],
        {p.name: p.bone for p in rig.parts},
        {p.name: p.pivot for p in rig.parts}, shadow=shadow)
    save_sheet(frames, tmp_path / layer_filename("demo", "rig", 1, 1,
                                                 "sheet-idle"))
    assert (tmp_path / "demo_rig_v01_s1_part-body.png").exists()
    assert (tmp_path / "demo_rig_v01_s1_part-head.png").exists()
    assert (tmp_path / "demo_rig_v01_s1_sheet-idle.png").exists()


def test_duplicate_bones_rejected():
    rig = skeleton.Rig()
    rig.add_bone("root", None, (0, 0))
    with pytest.raises(ValueError):
        rig.add_bone("root", None, (0, 0))
    with pytest.raises(ValueError):
        rig.add_part("p", "f.png", "missing", (0, 0), 0)
