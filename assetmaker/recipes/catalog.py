"""Recipe catalog: one file per object type, all registered here.

Contract for a recipe function:
    def make(seed: int, variant: int) -> AssetResult
See RECIPE_GUIDE.md (M6) for the full authoring guide.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from ..core.export import AssetResult


@dataclass(frozen=True)
class Recipe:
    kind: str
    category: str
    fn: Callable[[int, int], AssetResult]
    has_rig: bool
    doc: str


REGISTRY: dict[str, Recipe] = {}


def register(kind: str, category: str, has_rig: bool = False,
             doc: str = "") -> Callable:
    def wrap(fn: Callable[[int, int], AssetResult]) -> Callable:
        if kind in REGISTRY:
            raise ValueError(f"kind {kind!r} already registered")
        REGISTRY[kind] = Recipe(kind, category, fn, has_rig, doc)
        return fn
    return wrap


def get(kind: str) -> Recipe:
    if kind not in REGISTRY:
        known = ", ".join(sorted(REGISTRY))
        raise KeyError(f"unknown kind {kind!r}; registered: {known}")
    return REGISTRY[kind]


def load_all() -> None:
    """Import every built-in recipe module so registration runs."""
    from . import barrel, bush, chicken, crate, demo, human, rock, statue, tree  # noqa: F401
