"""Skeleton: bones, parts, pivots. The rig is derived from the SAME geometry
that draws the art, so the skeleton always matches the image exactly."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Bone:
    name: str
    parent: str | None
    pos: tuple[int, int]      # pivot position in asset pixel space
    rot: float = 0.0          # rest rotation, degrees
    length: float = 0.0       # distance to child joint / part extent

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "parent": self.parent,
            "pos": [int(self.pos[0]), int(self.pos[1])],
            "rot": float(self.rot),
            "length": float(self.length),
        }


@dataclass
class Part:
    name: str
    file: str                 # layer filename (engine-named)
    bone: str
    pivot: tuple[int, int]    # rotation center in asset pixel space
    z: int

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "file": self.file,
            "bone": self.bone,
            "pivot": [int(self.pivot[0]), int(self.pivot[1])],
            "z": int(self.z),
        }


@dataclass
class Rig:
    bones: list[Bone] = field(default_factory=list)
    parts: list[Part] = field(default_factory=list)
    animations: dict = field(default_factory=dict)

    def add_bone(self, name: str, parent: str | None,
                 pos: tuple[int, int], length: float = 0.0,
                 rot: float = 0.0) -> Bone:
        if any(b.name == name for b in self.bones):
            raise ValueError(f"duplicate bone {name!r}")
        if parent is not None and not any(b.name == parent for b in self.bones):
            raise ValueError(f"parent bone {parent!r} not defined before child")
        b = Bone(name, parent, pos, rot, length)
        self.bones.append(b)
        return b

    def add_part(self, name: str, file: str, bone: str,
                 pivot: tuple[int, int], z: int) -> Part:
        if any(p.name == name for p in self.parts):
            raise ValueError(f"duplicate part {name!r}")
        if not any(b.name == bone for b in self.bones):
            raise ValueError(f"part {name!r} references unknown bone {bone!r}")
        p = Part(name, file, bone, pivot, z)
        self.parts.append(p)
        return p

    def sorted_parts(self) -> list[Part]:
        return sorted(self.parts, key=lambda p: (p.z, p.name))

    def to_dict(self) -> dict:
        return {
            "bones": [b.to_dict() for b in self.bones],
            "parts": [p.to_dict() for p in self.sorted_parts()],
            "animations": self.animations,
        }
