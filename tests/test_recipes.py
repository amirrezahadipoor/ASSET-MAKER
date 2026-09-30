"""Recipe-wide gates: every registered kind, many seeds."""
from __future__ import annotations

import numpy as np
import pytest

from assetmaker.core.export import NAME_RE
from assetmaker.qa import gates
from assetmaker.recipes import catalog


@pytest.fixture(scope="module")
def kinds():
    catalog.load_all()
    return sorted(catalog.REGISTRY)


def test_registry_not_empty(kinds):
    assert len(kinds) >= 4


@pytest.mark.parametrize("kind", ["bush", "rock", "barrel", "crate", "sphere",
                                  "cube"])
def test_kind_passes_gates(kind):
    catalog.load_all()
    for seed in (7, 42, 99):
        res = catalog.get(kind).fn(seed, 1)
        full = res.full()
        obj_mask = res.parts["body"].alpha_mask()
        qa = gates.evaluate(res, full, obj_mask, recomposed=full)
        failed = [k for k, v in qa["checks"].items() if not v["passed"]]
        assert qa["passed"], f"{kind} seed {seed}: {failed}"


@pytest.mark.parametrize("kind", ["bush", "rock", "barrel", "crate"])
def test_twenty_seeds_unique_and_whole(kind):
    catalog.load_all()
    digests = []
    for seed in range(20):
        res = catalog.get(kind).fn(seed, 1)
        full = res.full()
        assert full.alpha_mask().sum() > 20, f"{kind} s{seed} empty"
        bbox = full.bbox()
        assert bbox is not None
        x0, y0, x1, y1 = bbox
        assert x0 > 0 and y0 > 0 and x1 < full.w - 1 and y1 < full.h - 1, \
            f"{kind} s{seed} cropped at {bbox}"
        digests.append(full.buf.tobytes())
    ok, detail = gates.check_seed_diversity(digests)
    assert ok, f"{kind}: {detail}"


def test_variants_differ(kinds):
    catalog.load_all()
    for kind in kinds:
        r = catalog.REGISTRY[kind]
        a = r.fn(42, 1).full().buf.tobytes()
        b = r.fn(42, 2).full().buf.tobytes()
        assert a != b, f"{kind}: variant 1 == variant 2"


def test_files_follow_naming(tmp_path, kinds):
    from assetmaker.cli import export_asset

    catalog.load_all()
    for kind in kinds:
        res = catalog.get(kind).fn(5, 1)
        manifest = export_asset(res, tmp_path)
        assert manifest["qa"]["passed"], f"{kind} qa failed in export"
        for layer, fn in [("full", manifest["files"]["full"]),
                          ("shadow", manifest["files"]["shadow"])]:
            assert NAME_RE.match(fn), fn
        for fn in manifest["files"]["parts"].values():
            assert NAME_RE.match(fn), fn
