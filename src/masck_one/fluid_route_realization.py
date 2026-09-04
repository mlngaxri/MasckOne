"""Authenticated 3D fluid-route realization downstream of Iteration 28.

A realized route is usable for digital collision and volume analysis only when it
binds to the released routing authority and to controlled geometry evidence. This
module never promotes CAD geometry into hydraulic, leakage, recovery, hygiene,
prime, purge, orientation-independence or efficacy evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from math import copysign, isfinite, sqrt
import json
import re

from .fluid_geometry_evidence import (
    ControlledEvidenceReference,
    ControlledEvidenceRegistry,
    FluidGeometryEvidenceError,
    PROVENANCE_CAD_MEASURED,
    PROVENANCE_PHYSICAL_MEASURED,
)
from .fluid_routing_checks import FluidRoutingClosureArchitecture, RoutingSegmentCheck


class FluidRouteRealizationError(ValueError):
    pass


ITERATION_28_RELEASE_COMMIT_SHA = "fcd9e1d6fe9a9d8db00891d5ae73e1823773af71"
_GEOMETRY_PROVENANCE = {PROVENANCE_CAD_MEASURED, PROVENANCE_PHYSICAL_MEASURED}
_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")


def _text(value: object, label: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise FluidRouteRealizationError(f"{label} must be exact built-in nonblank text")
    return value


def _sha(value: object, label: str) -> str:
    if type(value) is not str or _SHA256_RE.fullmatch(value) is None:
        raise FluidRouteRealizationError(f"{label} must be canonical lowercase SHA-256")
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
    xyz: list[float] = []
    for axis, coordinate in zip("xyz", value):
        if type(coordinate) not in (int, float):
            raise FluidRouteRealizationError(f"{label}.{axis} must be an exact numeric scalar")
        coordinate = float(coordinate)
        if not isfinite(coordinate):
            raise FluidRouteRealizationError(f"{label}.{axis} must be finite")
        if coordinate == 0.0 and copysign(1.0, coordinate) < 0.0:
            raise FluidRouteRealizationError(f"{label}.{axis} cannot use negative signed zero")
        xyz.append(0.0 if coordinate == 0.0 else coordinate)
    return xyz[0], xyz[1], xyz[2]


def _distance_mm(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return sqrt((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2 + (b[2] - a[2]) ** 2)


def _digest(payload: object) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return sha256(raw).hexdigest()


def _segment_identity(segment: RoutingSegmentCheck) -> tuple[str, str, str, str, str, str]:
    segment.validate_invariants()
    return (
        segment.segment_id,
        segment.system,
        segment.phase_identity,
        segment.stage,
        segment.source_interface_id,
        segment.target_interface_id,
    )


@dataclass(frozen=True, slots=True)
class RoutingAuthorityBinding:
    """Immutable snapshot of the controlled routing authority consumed by geometry."""

    release_commit_sha: str
    routing_architecture_sha256: str
    source_authority_revision: str
    segments: tuple[RoutingSegmentCheck, ...]

    def validate_invariants(self) -> None:
        release = _sha(self.release_commit_sha, "routing release commit")
        if release != ITERATION_28_RELEASE_COMMIT_SHA:
            raise FluidRouteRealizationError("routing authority is not bound to the controlled Iteration-28 release commit")
        _sha(self.routing_architecture_sha256, "routing architecture SHA")
        _text(self.source_authority_revision, "routing authority revision")
        if type(self.segments) is not tuple or not self.segments:
            raise FluidRouteRealizationError("routing authority segments must be a non-empty exact tuple")
        if any(type(item) is not RoutingSegmentCheck for item in self.segments):
            raise FluidRouteRealizationError("routing authority accepts exact RoutingSegmentCheck records only")
        ids: set[str] = set()
        for segment in self.segments:
            segment.validate_invariants()
            if segment.segment_id in ids:
                raise FluidRouteRealizationError("routing authority contains duplicate segment identity")
            ids.add(segment.segment_id)

    @property
    def segment_manifest_sha256(self) -> str:
        self.validate_invariants()
        return _digest([list(_segment_identity(item)) for item in self.segments])

    @property
    def manifest(self) -> dict[str, object]:
        self.validate_invariants()
        return {
            "release_commit_sha": self.release_commit_sha,
            "routing_architecture_sha256": self.routing_architecture_sha256,
            "source_authority_revision": self.source_authority_revision,
            "segment_manifest_sha256": self.segment_manifest_sha256,
            "segments": [
                {
                    "segment_id": identity[0],
                    "system": identity[1],
                    "phase_identity": identity[2],
                    "stage": identity[3],
                    "source_interface_id": identity[4],
                    "target_interface_id": identity[5],
                }
                for identity in (_segment_identity(item) for item in self.segments)
            ],
        }

    @property
    def manifest_sha256(self) -> str:
        return _digest(self.manifest)

    def validate_against(self, routing: FluidRoutingClosureArchitecture) -> None:
        self.validate_invariants()
        if type(routing) is not FluidRoutingClosureArchitecture:
            raise FluidRouteRealizationError("routing must use the exact FluidRoutingClosureArchitecture type")
        routing.validate_invariants()
        if self.routing_architecture_sha256 != routing.architecture_sha256:
            raise FluidRouteRealizationError("routing authority is stale for the controlled routing architecture SHA")
        if self.source_authority_revision != routing.source_authority_revision:
            raise FluidRouteRealizationError("routing authority is stale for the controlled authority revision")
        actual = tuple(_segment_identity(item) for item in routing.segments)
        expected = tuple(_segment_identity(item) for item in self.segments)
        if actual != expected:
            raise FluidRouteRealizationError("routing authority segment manifest no longer matches controlled routing")


def build_routing_authority_binding(routing: FluidRoutingClosureArchitecture) -> RoutingAuthorityBinding:
    if type(routing) is not FluidRoutingClosureArchitecture:
        raise FluidRouteRealizationError("routing must use the exact FluidRoutingClosureArchitecture type")
    routing.validate_invariants()
    segments = tuple(RoutingSegmentCheck(**item.manifest()) for item in routing.segments)
    binding = RoutingAuthorityBinding(
        release_commit_sha=ITERATION_28_RELEASE_COMMIT_SHA,
        routing_architecture_sha256=routing.architecture_sha256,
        source_authority_revision=routing.source_authority_revision,
        segments=segments,
    )
    binding.validate_against(routing)
    return binding


@dataclass(frozen=True, slots=True)
class RealizedRouteGeometry:
    """Explicit piecewise-linear route geometry bound to authenticated topology."""

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
    geometry_evidence: ControlledEvidenceReference
    routing_release_commit_sha: str
    routing_authority_sha256: str
    routing_authority_revision: str

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
        if type(self.geometry_evidence) is not ControlledEvidenceReference:
            raise FluidRouteRealizationError("geometry_evidence must use an exact ControlledEvidenceReference")
        try:
            self.geometry_evidence.validate_invariants()
        except FluidGeometryEvidenceError as exc:
            raise FluidRouteRealizationError("geometry_evidence is invalid") from exc
        if self.geometry_evidence.provenance != self.geometry_provenance:
            raise FluidRouteRealizationError("geometry evidence provenance does not match route provenance")
        if self.geometry_evidence.revision != self.source_geometry_revision:
            raise FluidRouteRealizationError("geometry evidence revision does not match route geometry revision")
        release = _sha(self.routing_release_commit_sha, "routing_release_commit_sha")
        if release != ITERATION_28_RELEASE_COMMIT_SHA:
            raise FluidRouteRealizationError("realized route is not bound to the controlled Iteration-28 release commit")
        _sha(self.routing_authority_sha256, "routing_authority_sha256")
        _text(self.routing_authority_revision, "routing_authority_revision")
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

    def validate_evidence_registry(self, registry: ControlledEvidenceRegistry) -> None:
        self.validate_invariants()
        if type(registry) is not ControlledEvidenceRegistry:
            raise FluidRouteRealizationError("evidence registry must use the exact ControlledEvidenceRegistry type")
        try:
            registry.require(
                self.geometry_evidence,
                allowed_provenance=_GEOMETRY_PROVENANCE,
                label="route geometry evidence",
            )
        except FluidGeometryEvidenceError as exc:
            raise FluidRouteRealizationError("route geometry evidence is not authenticated") from exc

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
        return sum(
            length * float(area)
            for length, area in zip(self.span_lengths_mm, self.span_internal_area_mm2)
        ) / 1000.0

    def manifest(self) -> dict[str, object]:
        self.validate_invariants()
        return {
            "segment_id": self.segment_id,
            "system": self.system,
            "phase_identity": self.phase_identity,
            "source_interface_id": self.source_interface_id,
            "target_interface_id": self.target_interface_id,
            "centerline_points_mm": [list(point) for point in self.centerline_points_mm],
            "span_internal_area_mm2": list(self.span_internal_area_mm2),
            "centerline_length_mm": self.centerline_length_mm,
            "geometric_dead_volume_mL": self.geometric_dead_volume_mL,
            "maximum_tessellation_chord_error_mm": self.maximum_tessellation_chord_error_mm,
            "geometry_provenance": self.geometry_provenance,
            "source_geometry_revision": self.source_geometry_revision,
            "geometry_evidence": self.geometry_evidence.manifest(),
            "routing_release_commit_sha": self.routing_release_commit_sha,
            "routing_authority_sha256": self.routing_authority_sha256,
            "routing_authority_revision": self.routing_authority_revision,
            "evidence_status": "DIGITAL_ROUTE_GEOMETRY_ONLY_NOT_HYDRAULIC_OR_PHYSICAL_PERFORMANCE_EVIDENCE",
        }


def require_topology_binding(
    route: RealizedRouteGeometry,
    segment: RoutingSegmentCheck,
    *,
    authority: RoutingAuthorityBinding,
    routing: FluidRoutingClosureArchitecture,
    evidence_registry: ControlledEvidenceRegistry | None = None,
) -> None:
    if type(route) is not RealizedRouteGeometry:
        raise FluidRouteRealizationError("route must be an exact RealizedRouteGeometry record")
    if type(segment) is not RoutingSegmentCheck:
        raise FluidRouteRealizationError("segment must be an exact RoutingSegmentCheck record")
    if type(authority) is not RoutingAuthorityBinding:
        raise FluidRouteRealizationError("authority must use the exact RoutingAuthorityBinding type")
    authority.validate_against(routing)
    route.validate_invariants()
    segment.validate_invariants()
    if evidence_registry is not None:
        route.validate_evidence_registry(evidence_registry)
    if route.routing_release_commit_sha != authority.release_commit_sha:
        raise FluidRouteRealizationError("realized route release binding is stale")
    if route.routing_authority_sha256 != authority.routing_architecture_sha256:
        raise FluidRouteRealizationError("realized route architecture binding is stale")
    if route.routing_authority_revision != authority.source_authority_revision:
        raise FluidRouteRealizationError("realized route authority revision is stale")
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
        raise FluidRouteRealizationError("realized geometry does not exactly match controlled topology identity")
    authorized = {item.segment_id: item for item in authority.segments}
    expected_authority_segment = authorized.get(segment.segment_id)
    if expected_authority_segment is None or _segment_identity(expected_authority_segment) != _segment_identity(segment):
        raise FluidRouteRealizationError("segment is not the authenticated controlled topology record")


def realized_route_set_dead_volume_mL(
    routes: tuple[RealizedRouteGeometry, ...],
    *,
    authority: RoutingAuthorityBinding,
    routing: FluidRoutingClosureArchitecture,
    evidence_registry: ControlledEvidenceRegistry | None = None,
) -> float:
    """Aggregate only an exact one-to-one authenticated routing-authority route set."""
    if type(routes) is not tuple or not routes:
        raise FluidRouteRealizationError("routes must be a non-empty exact tuple")
    if type(authority) is not RoutingAuthorityBinding:
        raise FluidRouteRealizationError("authority must use the exact RoutingAuthorityBinding type")
    authority.validate_against(routing)
    segment_by_id = {segment.segment_id: segment for segment in authority.segments}
    if len(segment_by_id) != len(authority.segments):
        raise FluidRouteRealizationError("routing authority contains duplicate segment identity")
    if len(routes) != len(authority.segments):
        raise FluidRouteRealizationError("realized route set does not exactly cover authenticated topology")
    seen: set[str] = set()
    total = 0.0
    for route in routes:
        if type(route) is not RealizedRouteGeometry:
            raise FluidRouteRealizationError("routes may contain only exact RealizedRouteGeometry records")
        if route.segment_id in seen:
            raise FluidRouteRealizationError("duplicate realized route segment identity")
        segment = segment_by_id.get(route.segment_id)
        if segment is None:
            raise FluidRouteRealizationError("realized route contains unknown authenticated topology segment")
        require_topology_binding(
            route,
            segment,
            authority=authority,
            routing=routing,
            evidence_registry=evidence_registry,
        )
        seen.add(route.segment_id)
        total += route.geometric_dead_volume_mL
    if seen != set(segment_by_id):
        raise FluidRouteRealizationError("realized route set does not exactly cover authenticated topology")
    return total
