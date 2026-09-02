"""Deterministic CAD geometry for the controlled Cell 3 retention load path.

This module converts released retention datums into actual CadQuery solids. It does not
invent anthropometry, fit, comfort, force or material behaviour. Callers must provide the
six world-coordinate datums and a released physical radius for every structural member.
The result is suitable for STEP/assembly integration and CAD-native collision work.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite, sqrt
from typing import Mapping

import cadquery as cq

from engineering.cell3.retention_package_contract import RetentionDatums, Vec3


MEMBER_ENDPOINTS = {
    "left_yoke_link": ("left_yoke", "left_junction"),
    "right_yoke_link": ("right_yoke", "right_junction"),
    "crown_left": ("left_junction", "crown_apex"),
    "crown_right": ("crown_apex", "right_junction"),
    "occipital_left": ("left_junction", "occipital_center"),
    "occipital_right": ("occipital_center", "right_junction"),
}


@dataclass(frozen=True)
class RetentionCadMember:
    name: str
    start: Vec3
    end: Vec3
    radius_mm: float
    length_mm: float
    solid: cq.Shape


@dataclass(frozen=True)
class RetentionCadAssembly:
    members: tuple[RetentionCadMember, ...]
    compound: cq.Compound

    def manifest(self) -> dict:
        return {
            "status": "CONTROLLED_CAD_GEOMETRY_NOT_PHYSICAL_VALIDATION",
            "member_count": len(self.members),
            "members": [
                {
                    "name": member.name,
                    "start_mm": list(member.start),
                    "end_mm": list(member.end),
                    "radius_mm": member.radius_mm,
                    "length_mm": member.length_mm,
                }
                for member in self.members
            ],
            "limitations": [
                "straight circular members only",
                "released datums and radii required from caller",
                "no anthropometric or comfort inference",
                "curved production members and adjusters require CAD-native sweep closure",
            ],
        }


def _validate_point(label: str, point: Vec3) -> None:
    if not isinstance(point, tuple) or len(point) != 3 or any(
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not isfinite(value)
        for value in point
    ):
        raise ValueError(f"{label} must be a finite numeric xyz tuple")


def _distance(a: Vec3, b: Vec3) -> float:
    return sqrt(sum((b[index] - a[index]) ** 2 for index in range(3)))


def _cylinder_between(start: Vec3, end: Vec3, radius_mm: float) -> cq.Shape:
    length = _distance(start, end)
    if length <= 0.0:
        raise ValueError("retention member endpoints must be distinct")
    direction = cq.Vector(
        (end[0] - start[0]) / length,
        (end[1] - start[1]) / length,
        (end[2] - start[2]) / length,
    )
    return cq.Solid.makeCylinder(radius_mm, length, cq.Vector(*start), direction)


def build_retention_cad(
    datums: RetentionDatums,
    member_radii_mm: Mapping[str, float],
) -> RetentionCadAssembly:
    """Build the six deliberate structural retention members as physical CAD solids.

    The function fails closed if any datum is malformed, any structural member radius is
    missing, an unexpected radius key is supplied, or any member degenerates to zero length.
    It intentionally does not choose dimensions on behalf of the caller.
    """

    for name, point in datums.__dict__.items():
        _validate_point(name, point)

    expected = set(MEMBER_ENDPOINTS)
    supplied = set(member_radii_mm)
    missing = expected - supplied
    extra = supplied - expected
    if missing or extra:
        detail = []
        if missing:
            detail.append(f"missing={sorted(missing)}")
        if extra:
            detail.append(f"unexpected={sorted(extra)}")
        raise ValueError("member radii must exactly cover structural members: " + ", ".join(detail))

    members: list[RetentionCadMember] = []
    for member_name, (start_name, end_name) in MEMBER_ENDPOINTS.items():
        radius = member_radii_mm[member_name]
        if (
            not isinstance(radius, (int, float))
            or isinstance(radius, bool)
            or not isfinite(radius)
            or radius <= 0.0
        ):
            raise ValueError(f"{member_name} radius must be finite and positive")
        start = getattr(datums, start_name)
        end = getattr(datums, end_name)
        length = _distance(start, end)
        if length <= 0.0:
            raise ValueError(f"{member_name} has a degenerate load path")
        solid = _cylinder_between(start, end, float(radius))
        members.append(
            RetentionCadMember(
                name=member_name,
                start=start,
                end=end,
                radius_mm=float(radius),
                length_mm=length,
                solid=solid,
            )
        )

    compound = cq.Compound.makeCompound([member.solid for member in members])
    return RetentionCadAssembly(tuple(members), compound)
