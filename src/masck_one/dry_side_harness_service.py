"""Dry-side harness routing and service geometry for Masck One.

Digital packaging evidence only. The geometry is a supported harness-envelope route
between the existing battery disconnect interface and the PCB-side dry package. It
does not select conductors, connectors, insulation, current ratings, ingress ratings,
retention force, EMC performance, bend-life, or electrical safety performance.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from itertools import pairwise
import json
import math

import cadquery as cq

from .dry_side_disconnect_interface import MATING_DATUM_WORLD_MM

SCHEMA = "MASCK_ONE_CELL12_DRY_SIDE_HARNESS_SERVICE_V1"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"
SOURCE_MAIN_SHA = "ac59fcd59f50b019cb972bfc526c2daea784bd17"
DRY_BAY_BOUNDS_WORLD_MM = (-24.0, 24.0, -33.0, 33.0, -47.0, -25.0)
HARNESS_ENVELOPE_RADIUS_MM = 1.25
ROUTE_POINTS_WORLD_MM = (
    (17.0, -3.0, -39.0),
    (17.0, 4.0, -39.0),
    (8.0, 4.0, -39.0),
    (8.0, 11.0, -39.0),
    (8.0, 11.0, -34.0),
)
CLIP_CENTERS_WORLD_MM = ((17.0, 4.0, -39.0), (8.0, 11.0, -39.0))
CLIP_RESERVATION_MM = (4.0, 4.0, 4.0)
PCB_HANDOFF_DATUM_WORLD_MM = ROUTE_POINTS_WORLD_MM[-1]
SERVICE_LOOP_EXTRA_PATH_MM = 16.0


class DrySideHarnessError(ValueError):
    pass


def _finite(value: object, label: str, *, positive: bool = False) -> float:
    if type(value) not in (int, float):
        raise DrySideHarnessError(f"{label} must be an exact numeric scalar")
    result = float(value)
    if not math.isfinite(result):
        raise DrySideHarnessError(f"{label} must be finite")
    if positive and result <= 0.0:
        raise DrySideHarnessError(f"{label} must be positive")
    return result


def _point(value: object, label: str) -> tuple[float, float, float]:
    if type(value) is not tuple or len(value) != 3:
        raise DrySideHarnessError(f"{label} must be an exact XYZ tuple")
    return tuple(_finite(v, f"{label}[{i}]") for i, v in enumerate(value))  # type: ignore[return-value]


def _sphere(center: tuple[float, float, float], radius: float) -> cq.Workplane:
    return cq.Workplane("XY").sphere(radius).translate(center)


def _axis_segment(
    first: tuple[float, float, float],
    second: tuple[float, float, float],
    radius: float,
) -> cq.Workplane:
    x0, y0, z0 = first
    x1, y1, z1 = second
    dx, dy, dz = x1 - x0, y1 - y0, z1 - z0
    nonzero = sum(abs(v) > 1e-9 for v in (dx, dy, dz))
    if nonzero != 1:
        raise DrySideHarnessError("harness route segments must be orthogonal and nonzero")
    length = math.sqrt(dx * dx + dy * dy + dz * dz)
    direction = cq.Vector(dx / length, dy / length, dz / length)
    solid = cq.Solid.makeCylinder(radius, length, cq.Vector(*first), direction)
    return cq.Workplane("XY").newObject([solid])


def _validate_route_topology(points: tuple[tuple[float, float, float], ...]) -> None:
    if len(points) < 2:
        raise DrySideHarnessError("harness route needs at least two points")
    for first, second in pairwise(points):
        deltas = tuple(b - a for a, b in zip(first, second, strict=True))
        if sum(abs(delta) > 1e-9 for delta in deltas) != 1:
            raise DrySideHarnessError("harness route segments must be orthogonal and nonzero")


def _route_solid(points: tuple[tuple[float, float, float], ...], radius: float) -> cq.Workplane:
    _validate_route_topology(points)
    route = _sphere(points[0], radius)
    for first, second in pairwise(points):
        route = route.union(_axis_segment(first, second, radius)).union(_sphere(second, radius))
    return route


def _box(size: tuple[float, float, float], center: tuple[float, float, float]) -> cq.Workplane:
    return cq.Workplane("XY").box(*size).translate(center)


def _geometry(shape: cq.Workplane) -> dict[str, object]:
    solid = shape.val()
    if not solid.isValid() or len(solid.Solids()) != 1:
        raise DrySideHarnessError("harness geometry must be one valid B-rep solid")
    volume = float(solid.Volume())
    if not math.isfinite(volume) or volume <= 0.0:
        raise DrySideHarnessError("harness geometry must have finite positive volume")
    bb = solid.BoundingBox()
    return {
        "bounds_world_mm": [
            float(bb.xmin), float(bb.xmax), float(bb.ymin), float(bb.ymax),
            float(bb.zmin), float(bb.zmax),
        ],
        "volume_mm3": volume,
    }


def _path_length(points: tuple[tuple[float, float, float], ...]) -> float:
    return sum(math.dist(first, second) for first, second in pairwise(points))


def _inside_dry_bay(shape: cq.Workplane) -> bool:
    xmin, xmax, ymin, ymax, zmin, zmax = DRY_BAY_BOUNDS_WORLD_MM
    bb = shape.val().BoundingBox()
    return (
        bb.xmin >= xmin - 1e-7 and bb.xmax <= xmax + 1e-7
        and bb.ymin >= ymin - 1e-7 and bb.ymax <= ymax + 1e-7
        and bb.zmin >= zmin - 1e-7 and bb.zmax <= zmax + 1e-7
    )


@dataclass(frozen=True, slots=True)
class DrySideHarnessService:
    route_envelope: cq.Workplane
    clip_reservations: tuple[cq.Workplane, ...]
    route_points_world_mm: tuple[tuple[float, float, float], ...]

    def validate(self) -> "DrySideHarnessService":
        _geometry(self.route_envelope)
        _validate_route_topology(self.route_points_world_mm)
        if len(self.clip_reservations) != len(CLIP_CENTERS_WORLD_MM):
            raise DrySideHarnessError("dry-side harness requires both support reservations")
        for clip in self.clip_reservations:
            _geometry(clip)
            if not _inside_dry_bay(clip):
                raise DrySideHarnessError("harness support reservation escapes current dry-bay package")
            if not self.route_envelope.val().intersect(clip.val()).Volume() > 1e-9:
                raise DrySideHarnessError("harness support reservation must engage the route envelope")

        if not _inside_dry_bay(self.route_envelope):
            raise DrySideHarnessError("harness route escapes current dry-bay package")

        if self.route_points_world_mm[0] != ROUTE_POINTS_WORLD_MM[0]:
            raise DrySideHarnessError("harness route moved from disconnect-side strain relief")
        if self.route_points_world_mm[-1] != PCB_HANDOFF_DATUM_WORLD_MM:
            raise DrySideHarnessError("harness route moved from PCB handoff datum")
        if _path_length(self.route_points_world_mm) < SERVICE_LOOP_EXTRA_PATH_MM:
            raise DrySideHarnessError("harness route lost the minimum digital service-loop allowance")
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        payload: dict[str, object] = {
            "schema": SCHEMA,
            "source_main_sha": SOURCE_MAIN_SHA,
            "coordinate_frame_id": WORLD_FRAME_ID,
            "source_disconnect_mating_datum_world_mm": list(MATING_DATUM_WORLD_MM),
            "route_points_world_mm": [list(point) for point in self.route_points_world_mm],
            "pcb_handoff_datum_world_mm": list(PCB_HANDOFF_DATUM_WORLD_MM),
            "service_loop_extra_path_mm": SERVICE_LOOP_EXTRA_PATH_MM,
            "route_path_length_mm": _path_length(self.route_points_world_mm),
            "geometry": {
                "harness_route_envelope": _geometry(self.route_envelope),
                "clip_reservations": [_geometry(clip) for clip in self.clip_reservations],
            },
            "route_status": "DIGITAL_SUPPORTED_HARNESS_ENVELOPE_AND_SERVICE_LOOP_REALIZED",
            "connector_selected": False,
            "conductor_selected": False,
            "electrical_ratings_selected": False,
            "ingress_validated": False,
            "emc_validated": False,
            "bend_life_validated": False,
            "physical_service_validated": False,
            "evidence_status": "DIGITAL_PACKAGING_AND_SERVICE_GEOMETRY_ONLY",
        }
        payload["manifest_sha256"] = sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        ).hexdigest()
        return payload


def build_dry_side_harness_service() -> DrySideHarnessService:
    points = tuple(_point(point, "route point") for point in ROUTE_POINTS_WORLD_MM)
    route = _route_solid(points, HARNESS_ENVELOPE_RADIUS_MM)
    clips = tuple(_box(CLIP_RESERVATION_MM, center) for center in CLIP_CENTERS_WORLD_MM)
    return DrySideHarnessService(route, clips, points).validate()