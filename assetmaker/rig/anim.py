"""Animation: per-frame bone rotations + root offsets, exported as sheets.

Nearest-neighbor rotation only, small angles (<=25 deg) — STYLE_GUIDE §10.
Frame format (manifest):
    {"loop": true, "fps": 6, "frames": [
        {"root": [dx, dy], "bones": {"bone_name": rot_deg}, "duration": 1}, ...]}
"""
from __future__ import annotations

import math

import numpy as np
from PIL import Image

from ..core.shapes import Canvas


def make_frame(root: tuple[int, int] = (0, 0),
               bones: dict[str, float] | None = None,
               duration: int = 1) -> dict:
    return {
        "root": [int(root[0]), int(root[1])],
        "bones": dict(bones or {}),
        "duration": int(duration),
    }


def make_animation(frames: list[dict], fps: int = 6, loop: bool = True) -> dict:
    return {"loop": bool(loop), "fps": int(fps), "frames": frames}


def _rotate_canvas(canvas: Canvas, pivot: tuple[int, int],
                   deg: float) -> Canvas:
    """Nearest-neighbor rotation about a pivot. deg==0 is a no-op copy."""
    if abs(deg) < 1e-6:
        return canvas.copy()
    img = canvas.to_pil()
    # PIL rotates counter-clockwise for positive angles in Image.rotate.
    rot = img.rotate(-deg, resample=Image.NEAREST,
                     center=(pivot[0], pivot[1]), expand=False)
    out = Canvas(canvas.w, canvas.h)
    out.buf = np.array(rot, dtype=np.uint8)
    return out


def compose_frame(parts: dict[str, Canvas], z_order: list[str],
                  part_bone: dict[str, str], part_pivot: dict[str, tuple[int, int]],
                  bone_rot: dict[str, float], root: tuple[int, int],
                  shadow: Canvas | None = None) -> Canvas:
    """Composite one animation frame from part canvases.

    Each part rotates by its bone's rotation about its own pivot, then the
    whole frame is shifted by `root`. Shadow does not rotate.
    """
    size_h = max(c.h for c in parts.values())
    size_w = max(c.w for c in parts.values())
    frame = Canvas(size_w, size_h)
    if shadow is not None:
        frame.composite(shadow)
    for name in z_order:
        c = parts[name]
        rot = float(bone_rot.get(part_bone.get(name, ""), 0.0))
        piv = part_pivot.get(name, (c.w // 2, c.h // 2))
        rc = _rotate_canvas(c, piv, rot)
        if root != (0, 0):
            shifted = Canvas(rc.w, rc.h)
            dx, dy = int(root[0]), int(root[1])
            ys0, ys1 = max(0, dy), min(rc.h, rc.h + dy)
            xs0, xs1 = max(0, dx), min(rc.w, rc.w + dx)
            if ys1 > ys0 and xs1 > xs0:
                shifted.buf[ys0 - dy:ys1 - dy, xs0 - dx:xs1 - dx] = \
                    rc.buf[ys0:ys1, xs0:xs1]
            rc = shifted
        frame.composite(rc)
    return frame


def export_sheet(anim: dict, parts: dict[str, Canvas], z_order: list[str],
                 part_bone: dict[str, str],
                 part_pivot: dict[str, tuple[int, int]],
                 shadow: Canvas | None = None) -> list[Canvas]:
    """Render every frame of an animation into full-size canvases."""
    frames: list[Canvas] = []
    for fr in anim["frames"]:
        frames.append(
            compose_frame(parts, z_order, part_bone, part_pivot,
                          fr.get("bones", {}), tuple(fr.get("root", (0, 0))),
                          shadow=shadow)
        )
    return frames


def sine_swing(n: int, amp: float, phase: float = 0.0) -> list[float]:
    """Smooth n-frame swing values in [-amp, +amp] (walk cycles, bobs)."""
    return [amp * math.sin(2 * math.pi * (i / n) + phase) for i in range(n)]
