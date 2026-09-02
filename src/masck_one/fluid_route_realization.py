"""Topology-bound 3D fluid-route realization.

This module is the first geometry-owning layer downstream of Iteration 28. It does not
invent routes. A route becomes quantitatively usable only when explicit 3D centerline
vertices and per-span internal cross-sectional areas are supplied with controlled CAD
or physical provenance and bind exactly to one released topology segment.

Polyline length is a geometric property of the supplied realization. It is not a pump,
hydraulic, leakage, recovery, prime, purge, hygiene, or efficacy result.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite, sqrt

from .fluid_geometry_evidence import (
    FluidGeometryEvidenceError,
    PROVENANCE_CAD_MEASURED,
    PROVENANCE_PHYSICAL_MEASURED,
)
from .fluid_routing_checks import RoutingSegmentCheck


class FluidRouteRealizationError(ValueError):
    pass


_GEOMETRY_PROVENANCE = {PROVENANCE_CAD_MEASURED, PROVENANCE_PHYSICAL_MEASURED}


def _text(value: object, label: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise FluidRouteRealizationError(f"{label} must be exact built-in nonblank text")
    return value


def _positive(value: object, label: str) -> float:
    if type(value) not in (int, float):
        raise FluidRouteRealizationError(f"{label} must be an exact numeric scalar")
    value = float(value)
    if not isfinite(value) or value <= 0.0:
        raise FluidRouteRealizationError(f"{label} must be finite and positive")
    return value


def _point(value: object, label: str) -> tuple[float, float, float]:
    if type(value) is not tuple or len(value) != 3:
        raise FluidRouteRealizationError(f"{label} must be an exact xyz tuple")
    xyz = []
    for axis, coordinate in zip("xyz", value):
        if type(coordinate) not in (int, float):
            raise FluidRouteRealizationError(f"{label}.{axis} must be an exact numeric scalar")
        coordinate = float(coordinate)
        if not isfinite(coordinate):
            raise FluidRouteRealizationError(f"{label}.{axis} must be finite")
        xyz.append(0.0 if coordinate == 0.0 else coordinate)
    return xyz[0], xyz[1], xyz[2]


def _distance_mm(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return sqrt((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2 + (b[2] - a[2]) ** 2)


@dataclass(frozen=True, slots=True)
class RealizedRouteGeometry:
    """Explicit piecewise-linear route geometry bound to one topology segment.

    `span_internal_area_mm2[i]` applies to the span from point i to point i+1. A CAD
    export containing curves must be tessellated under a controlled tolerance before
    entering this type. `maximum_tessellation_chord_error_mm` records that tolerance;
    it does not convert a coarse polyline into exact curve length.
    """

    segment_id: str
    system: str
    phase_identity: str
    source_interface_id: str
    target_interface_id: str
    centerline_points_mm: tuple[tuple[float, float, float], ...]
    span_internal_area_mm2: tuple[float, ...]
    maximum_tessellation_chord_error_mm: float
    geometry_provenance: str
    source_geometry_revision: str

    def validate_invariants(self) -> None:
        _text(self.segment_id, "segment_id")
        _text(self.system, "system")
        _text(self.phase_identity, "phase_identity")
        _text(self.source_interface_id, "source_interface_id")
        _text(self.target_interface_id, "target_interface_id")
        _text(self.source_geometry_revision, "source_geometry_revision")
        if self.source_interface_id == self.target_interface_id:
            raise FluidRouteRealizationError("realized route cannot alias source and target interfaces")
        if type(self.geometry_provenance) is not str or self.geometry_provenance not in _GEOMETRY_PROVENANCE:
            raise FluidRouteRealizationError("geometry_provenance cannot establish realized route geometry")
        if type(self.centerline_points_mm) is not tuple or len(self.centerline_points_mm) < 2:
            raise FluidRouteRealizationError("centerline_points_mm must contain at least two exact xyz tuples")
        points = tuple(_point(p, f"centerline_points_mm[{i}]") for i, p in enumerate(self.centerline_points_mm))
        if type(self.span_internal_area_mm2) is not tuple:
            raise FluidRouteRealizationError("span_internal_area_mm2 must be an exact tuple")
        if len(self.span_internal_area_mm2) != len(points) - 1:
            raise FluidRouteRealizationError("one internal-area value is required for every centerline span")
        for i, area in enumerate(self.span_internal_area_mm2):
            _positive(area, f"span_internal_area_mm2[{i}]")
        _positive(self.maximum_tessellation_chord_error_mm, "maximum_tessellation_chord_error_mm")
        for i, (a, b) in enumerate(zip(points, points[1:])):
            if _distance_mm(a, b) <= 0.0:
                raise FluidRouteRealizationError(f"centerline span {i} has zero length")

    @property
    def span_lengths_mm(self) -> tuple[float, ...]:
        self.validate_invariants()
        points = tuple(_point(p, f"centerline_points_mm[{i}]") for i, p in enumerate(self.centerline_points_mm))
        return tuple(_distance_mm(a, b) for a, b in zip(points, points[1:]))

    @property
    def centerline_length_mm(self) -> float:
        return sum(self.span_lengths_mm)

    @property
    def geometric_dead_volume_mL(self) -> float:
        self.validate_invariants()
        return sum(length * float(area) for length, area in zip(self.span_lengths_mm, self.span_internal_area_mm2)) / 1000.0


def require_topology_binding(route: RealizedRouteGeometry, segment: RoutingSegmentCheck) -> None:
    """Fail closed unless realized geometry is exactly the released segment it claims to be."""
    if type(route) is not RealizedRouteGeometry:
        raise FluidRouteRealizationError("route must be an exact RealizedRouteGeometry record")
    if type(segment) is not RoutingSegmentCheck:
        raise FluidRouteRealizationError("segment must be an exact RoutingSegmentCheck record")
    route.validate_invariants()
    segment.validate_invariants()
    expected = (
        segment.segment_id,
        segment.system,
        segment.phase_identity,
        segment.source_interface_id,
        segment.target_interface_id,
    )
    actual = (
        route.segment_id,
        route.system,
        route.phase_identity,
        route.source_interface_id,
        route.target_interface_id,
    )
    if actual != expected:
        raise FluidRouteRealizationError("realized geometry does not exactly match released topology identity")


def realized_route_set_dead_volume_mL(
    routes: tuple[RealizedRouteGeometry, ...],
    segments: tuple[RoutingSegmentCheck, ...],
) -> float:
    """Aggregate only an exact one-to-one topology-bound realized route set."""
    if type(routes) is not tuple or not routes:
        raise FluidRouteRealizationError("routes must be a non-empty exact tuple")
    if type(segments) is not tuple or not segments:
        raise FluidRouteRealizationError("segments must be a non-empty exact tuple")
    segment_by_id: dict[str, RoutingSegmentCheck] = {}
    for segment in segments:
        if type(segment) is not RoutingSegmentCheck:
            raise FluidRouteRealizationError("segments may contain only exact RoutingSegmentCheck records")
        segment.validate_invariants()
        if segment.segment_id in segment_by_id:
            raise FluidRouteRealizationError("released topology contains duplicate segment identity")
        segment_by_id[segment.segment_id] = segment
    if len(routes) != len(segments):
        raise FluidRouteRealizationError("realized route set does not exactly cover released topology")
    seen: set[str] = set()
    total = 0.0
    for route in routes:
        if type(route) is not RealizedRouteGeometry:
            raise FluidRouteRealizationError("routes may contain only exact RealizedRouteGeometry records")
        if route.segment_id in seen:
            raise FluidRouteRealizationError("duplicate realized route segment identity")
        segment = segment_by_id.get(route.segment_id)
        if segment is None:
            raise FluidRouteRealizationError("realized route contains unknown topology segment identity")
        require_topology_binding(route, segment)
        seen.add(route.segment_id)
        total += route.geometric_dead_volume_mL
    if seen != set(segment_by_id):
        raise FluidRouteRealizationError("realized route set does not exactly cover released topology")
    return total
