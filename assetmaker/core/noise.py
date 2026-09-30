"""Deterministic noise helpers. All randomness flows through PCG64 streams
seeded by SHA-256 of the asset id + purpose, so outputs are reproducible."""
from __future__ import annotations

import hashlib

import numpy as np


def rng_for(*parts: object) -> np.random.Generator:
    """Stable RNG: sha256(':'.join(parts)) -> 128-bit seed -> PCG64."""
    key = ":".join(str(p) for p in parts).encode("utf-8")
    digest = hashlib.sha256(key).digest()
    seed = int.from_bytes(digest[:16], "big")
    return np.random.default_rng(seed)


def value_noise_2d(w: int, h: int, cell: int, rng: np.random.Generator,
                   octaves: int = 2) -> np.ndarray:
    """Smooth value noise in [0,1], bilinear grid + octaves. Cell >= 2."""
    out = np.zeros((h, w), dtype=np.float64)
    amp, total = 1.0, 0.0
    c = max(2, int(cell))
    for _ in range(max(1, octaves)):
        gw, gh = w // c + 2, h // c + 2
        grid = rng.random((gh, gw))
        ys = np.arange(h) / c
        xs = np.arange(w) / c
        y0 = np.floor(ys).astype(int)
        x0 = np.floor(xs).astype(int)
        fy = (ys - y0)[:, None]
        fx = (xs - x0)[None, :]
        # smoothstep for organic feel
        fy = fy * fy * (3 - 2 * fy)
        fx = fx * fx * (3 - 2 * fx)
        g00 = grid[np.ix_(y0, x0)]
        g01 = grid[np.ix_(y0, x0 + 1)]
        g10 = grid[np.ix_(y0 + 1, x0)]
        g11 = grid[np.ix_(y0 + 1, x0 + 1)]
        layer = (g00 * (1 - fx) * (1 - fy) + g01 * fx * (1 - fy)
                 + g10 * (1 - fx) * fy + g11 * fx * fy)
        out += amp * layer
        total += amp
        amp *= 0.5
        c = max(2, c // 2)
    return out / total


def radial_blob(rng: np.random.Generator, lobes: int = 5,
                ruggedness: float = 0.18) -> np.ndarray:
    """Periodic radius multiplier over [0, 2pi): organic lobe silhouettes.

    Returns a callable-free sampled array of 256 radii in
    [1-ruggedness, 1+ruggedness], normalized so mean radius is 1.
    """
    n = 256
    theta = np.linspace(0, 2 * np.pi, n, endpoint=False)
    radius = np.ones(n)
    for k in (1, 2, 3):
        lobes_k = max(2, lobes * k // 2)
        phase = rng.random() * 2 * np.pi
        amp = ruggedness / k
        radius = radius + amp * np.sin(lobes_k * theta + phase)
    radius = np.clip(radius, 1 - ruggedness * 2, 1 + ruggedness * 2)
    return radius / radius.mean()


def scatter_points(rng: np.random.Generator, count: int, x0: float, y0: float,
                   x1: float, y1: float) -> list[tuple[float, float]]:
    """Random points in a box (cluster seeds for foliage lobes etc.)."""
    xs = rng.uniform(x0, x1, size=count)
    ys = rng.uniform(y0, y1, size=count)
    return [(float(a), float(b)) for a, b in zip(xs, ys)]


def pick(rng: np.random.Generator, options: list, weights: list | None = None):
    idx = rng.choice(len(options), p=weights)
    return options[int(idx)]
