"""Master palette: material ramps sampled from reference/village.png.

Ramp rule (STYLE_GUIDE.md §3): shading steps are hue-shifted — shadows toward
teal/plum/blue, highlights toward yellow/cream. All colors are authored
explicitly from reference samples. Every rendered pixel must be one of these.
"""
from __future__ import annotations

import colorsys
from dataclasses import dataclass


@dataclass(frozen=True)
class Ramp:
    """A material ramp: outline color + shading steps dark -> light."""

    name: str
    outline: str
    steps: tuple[str, ...]  # dark -> light, >= 3

    def __post_init__(self) -> None:
        if len(self.steps) < 3:
            raise ValueError(f"ramp {self.name!r} needs >= 3 steps")
        for c in (self.outline, *self.steps):
            _check_hex(c)

    def shade(self, t: float) -> str:
        """Map t in [0, 1] to a ramp color (dark -> light)."""
        if t <= 0.0:
            return self.steps[0]
        if t >= 1.0:
            return self.steps[-1]
        f = t * (len(self.steps) - 1)
        return self.steps[int(f + 0.5)]

    def step_index(self, color: str) -> int:
        return self.steps.index(color.lower())

    @property
    def all_colors(self) -> tuple[str, ...]:
        return (self.outline, *self.steps)


def _check_hex(c: str) -> None:
    if not (isinstance(c, str) and len(c) == 7 and c[0] == "#"):
        raise ValueError(f"bad hex color {c!r}")
    int(c[1:], 16)


# --------------------------------------------------------------------------
# Ramps sampled from reference/village.png (see STYLE_GUIDE.md §4)
# --------------------------------------------------------------------------

RAMPS: dict[str, Ramp] = {
    "leaf": Ramp(
        "leaf", "#10141f",
        ("#0b3836", "#124f33", "#2c4418", "#42640a", "#367a0c",
         "#53802c", "#64bd18", "#76bc3a", "#abb948"),
    ),
    "grass": Ramp(
        "grass", "#243512",
        ("#293e16", "#2c4418", "#3f671d", "#4c7529", "#53802c",
         "#6ba33a", "#64bd18"),
    ),
    "bark": Ramp(
        "bark", "#1c1815",
        ("#24170c", "#3c230e", "#523319", "#5b381a", "#764d29", "#aa7447"),
    ),
    "wood": Ramp(
        "wood", "#231a14",
        ("#3c230e", "#432d19", "#57492f", "#645433", "#764d29",
         "#917444", "#aa7447"),
    ),
    "roof_orange": Ramp(
        "roof_orange", "#24170c",
        ("#3c230e", "#5b3412", "#895426", "#a46732", "#d18340"),
    ),
    "roof_red": Ramp(
        "roof_red", "#1c1815",
        ("#39160b", "#4e2214", "#783621", "#ae583c", "#c66343", "#ea8868"),
    ),
    "stone_warm": Ramp(
        "stone_warm", "#10141f",
        ("#383931", "#494a42", "#605d4e", "#6e6a5e", "#96928e",
         "#b1af9a", "#c9c6b3"),
    ),
    "stone_cool": Ramp(
        "stone_cool", "#121723",
        ("#343130", "#494744", "#6b6d69", "#878480", "#aea9a5", "#c9cdc1"),
    ),
    "wall_timber": Ramp(
        "wall_timber", "#1c1815",
        ("#3c230e", "#523319", "#5c5037", "#786845", "#8a774f", "#918b69"),
    ),
    "dirt": Ramp(
        "dirt", "#645433",
        ("#7e6621", "#917e55", "#a38957", "#ad9a70", "#bc9d5f", "#d9cba6"),
    ),
    "canvas": Ramp(
        "canvas", "#3c230e",
        ("#8a8064", "#ae9d74", "#cebd91", "#d9cba6", "#efe7c3"),
    ),
    "metal": Ramp(
        "metal", "#10141f",
        ("#383931", "#494747", "#6b6d69", "#96928e", "#c9cdc1"),
    ),
    "skin": Ramp(
        "skin", "#231a14",
        ("#7a3c28", "#a05a3c", "#c66343", "#df8568", "#f0a888"),
    ),
    "cloth_red": Ramp(
        "cloth_red", "#1c1815",
        ("#4e2214", "#6a2021", "#952c2d", "#c66343"),
    ),
    "cloth_blue": Ramp(
        "cloth_blue", "#121723",
        ("#374155", "#47546e", "#5981d4", "#6890ed", "#97add8", "#c6daff"),
    ),
    "straw": Ramp(
        "straw", "#392f15",
        ("#505023", "#7e6621", "#98942c", "#abb948", "#d0c060"),
    ),
    "cream": Ramp(
        "cream", "#231a14",
        ("#8a8064", "#b1a888", "#d9cba6", "#efe7c3"),
    ),
}

# Ground contact shadow color (sampled grass-shadow from the reference).
SHADOW_COLOR = "#2c4418"

# Flat accent colors (flowers, berries) sampled from the reference.
ACCENTS: dict[str, str] = {
    "flower_red": "#952c2d",
    "flower_red_dark": "#6a2021",
    "flower_blue": "#5981d4",
    "flower_blue_light": "#97add8",
    "flower_yellow": "#d0c060",
    "ink": "#000000",  # used by the reference on buildings; legal, rare
}

ALL_COLORS: tuple[str, ...] = tuple(
    dict.fromkeys(
        [c for ramp in RAMPS.values() for c in ramp.all_colors]
        + [SHADOW_COLOR]
        + list(ACCENTS.values())
    )
)

_COLOR_SET = frozenset(ALL_COLORS)
_HEX_TO_RGBA: dict[str, tuple[int, int, int, int]] = {
    c: (int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16), 255) for c in ALL_COLORS
}
_HEX_TO_RGBA["transparent"] = (0, 0, 0, 0)


def is_palette_color(color: str) -> bool:
    return color.lower() in _COLOR_SET


def rgba(color: str) -> tuple[int, int, int, int]:
    """Hex -> RGBA tuple. 'transparent' -> (0,0,0,0)."""
    if color == "transparent":
        return (0, 0, 0, 0)
    c = color.lower()
    if c not in _HEX_TO_RGBA:
        raise ValueError(f"color {color!r} is not in the master palette")
    return _HEX_TO_RGBA[c]


# --------------------------------------------------------------------------
# Procedural variant ramps (e.g. tunic colors) with enforced hue-shift
# --------------------------------------------------------------------------

def _hex_to_hsv(c: str) -> tuple[float, float, float]:
    r, g, b = (int(c[i:i + 2], 16) / 255.0 for i in (1, 3, 5))
    return colorsys.rgb_to_hsv(r, g, b)


def _hsv_to_hex(h: float, s: float, v: float) -> str:
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, min(max(s, 0.0), 1.0),
                                  min(max(v, 0.0), 1.0))
    return "#{:02x}{:02x}{:02x}".format(round(r * 255), round(g * 255),
                                        round(b * 255))


def shift_color(color: str, dh: float, ds: float, dv: float) -> str:
    h, s, v = _hex_to_hsv(color)
    return _hsv_to_hex(h + dh, s + ds, v + dv)


def make_ramp(name: str, base: str, outline: str | None = None) -> Ramp:
    """Build a 5-step hue-shifted ramp around a base color.

    Steps: (dark2, dark1, base, light1, light2) — base is the middle step.
    Shadows: hue +0.06 (toward plum/teal), sat +0.10, value down.
    Highlights: hue -0.04 (toward yellow), sat -0.12, value up.
    Deterministic pure math; used for variant colors (tunics, hair...).
    """
    _check_hex(base)
    dark2 = shift_color(base, +0.08, +0.12, -0.30)
    dark1 = shift_color(base, +0.04, +0.06, -0.15)
    light1 = shift_color(base, -0.03, -0.08, +0.12)
    light2 = shift_color(base, -0.05, -0.14, +0.22)
    out = outline or shift_color(dark2, +0.02, +0.05, -0.18)
    return Ramp(name, out, (dark2, dark1, base, light1, light2))


def register_ramp(ramp: Ramp) -> Ramp:
    """Add a generated ramp (variant colors) to the master palette.

    Pure and deterministic: same ramp name/base => same colors, so QA
    palette-purity stays meaningful and seeds stay reproducible.
    """
    global ALL_COLORS, _COLOR_SET, _HEX_TO_RGBA
    RAMPS[ramp.name] = ramp
    merged = list(ALL_COLORS)
    for c in ramp.all_colors:
        if c not in _COLOR_SET:
            merged.append(c)
    ALL_COLORS = tuple(merged)
    _COLOR_SET = frozenset(ALL_COLORS)
    for c in ramp.all_colors:
        _HEX_TO_RGBA.setdefault(
            c, (int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16), 255))
    return ramp
