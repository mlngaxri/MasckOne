"""Controlled evidence records for realized fluid-route geometry.

This layer is downstream of the released routing topology. Numeric geometry remains
digital engineering evidence unless a controlled physical record explicitly says
otherwise. Provenance category alone is never sufficient: every consumed measurement
or requirement must bind to an immutable record identity, revision and SHA-256.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from math import isfinite, pi
import json
import re


class FluidGeometryEvidenceError(ValueError):
    pass


PROVENANCE_CAD_MEASURED = "CAD_MEASURED"
PROVENANCE_SUPPLIER_CONTROLLED = "SUPPLIER_CONTROLLED"
PROVENANCE_PHYSICAL_MEASURED = "PHYSICAL_MEASURED"
PROVENANCE_IDS = (
    PROVENANCE_CAD_MEASURED,
    PROVENANCE_SUPPLIER_CONTROLLED,
    PROVENANCE_PHYSICAL_MEASURED,
)
_GEOMETRY_PROVENANCE = {PROVENANCE_CAD_MEASURED, PROVENANCE_PHYSICAL_MEASURED}
_BEND_REQUIREMENT_PROVENANCE = {PROVENANCE_SUPPLIER_CONTROLLED, PROVENANCE_PHYSICAL_MEASURED}
_SERVICE_PROVENANCE = {PROVENANCE_CAD_MEASURED, PROVENANCE_PHYSICAL_MEASURED}
_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")


def _positive(value: object, label: str) -> float:
    if type(value) not in (int, float):
        raise FluidGeometryEvidenceError(f"{label} must be an exact numeric scalar")
    value = float(value)
    if not isfinite(value) or value <= 0.0:
        raise FluidGeometryEvidenceError(f"{label} must be finite and positive")
    return value


def _nonnegative(value: object, label: str) -> float:
    if type(value) not in (int, float):
        raise FluidGeometryEvidenceError(f"{label} must be an exact numeric scalar")
    value = float(value)
    if not isfinite(value) or value < 0.0:
        raise FluidGeometryEvidenceError(f"{label} must be finite and non-negative")
    return 0.0 if value == 0.0 else value


def _exact_text(value: object, label: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise FluidGeometryEvidenceError(f"{label} must be exact nonblank built-in text")
    return value


def _sha(value: object, label: str) -> str:
    if type(value) is not str or _SHA256_RE.fullmatch(value) is None:
        raise FluidGeometryEvidenceError(f"{label} must be canonical lowercase SHA-256")
    return value


def _digest(payload: object) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return sha256(raw).hexdigest()


@dataclass(frozen=True, slots=True)
class ControlledEvidenceReference:
    record_id: str
    revision: str
    sha256: str
    provenance: str

    def validate_invariants(self) -> None:
        _exact_text(self.record_id, "evidence record_id")
        _exact_text(self.revision, "evidence revision")
        _sha(self.sha256, "evidence sha256")
        if type(self.provenance) is not str or self.provenance not in PROVENANCE_IDS:
            raise FluidGeometryEvidenceError("evidence provenance is not controlled")

    def manifest(self) -> dict[str, str]:
        self.validate_invariants()
        return {
            "record_id": self.record_id,
            "revision": self.revision,
            "sha256": self.sha256,
            "provenance": self.provenance,
        }


@dataclass(frozen=True, slots=True)
class ControlledEvidenceRegistry:
    records: tuple[ControlledEvidenceReference, ...]

    def validate_invariants(self) -> None:
        if type(self.records) is not tuple or not self.records:
            raise FluidGeometryEvidenceError("evidence registry must be a non-empty exact tuple")
        if any(type(item) is not ControlledEvidenceReference for item in self.records):
            raise FluidGeometryEvidenceError("evidence registry accepts exact ControlledEvidenceReference records only")
        seen: set[str] = set()
        for item in self.records:
            item.validate_invariants()
            if item.record_id in seen:
                raise FluidGeometryEvidenceError("evidence registry contains duplicate record identity")
            seen.add(item.record_id)

    def require(
        self,
        reference: ControlledEvidenceReference,
        *,
        allowed_provenance: set[str],
        label: str,
    ) -> None:
        self.validate_invariants()
        if type(reference) is not ControlledEvidenceReference:
            raise FluidGeometryEvidenceError(f"{label} must use an exact controlled evidence reference")
        reference.validate_invariants()
        if reference.provenance not in allowed_provenance:
            raise FluidGeometryEvidenceError(f"{label} provenance cannot authorize this evidence role")
        matches = [item for item in self.records if item.record_id == reference.record_id]
        if len(matches) != 1 or matches[0].manifest() != reference.manifest():
            raise FluidGeometryEvidenceError(f"{label} does not match the controlled evidence registry")

    @property
    def manifest(self) -> dict[str, object]:
        self.validate_invariants()
        return {"records": [item.manifest() for item in self.records]}

    @property
    def manifest_sha256(self) -> str:
        return _digest(self.manifest)


@dataclass(frozen=True, slots=True)
class RouteGeometryEvidence:
    segment_id: str
    centerline_length_mm: float
    internal_area_mm2: float
    realized_minimum_bend_radius_mm: float
    required_minimum_bend_radius_mm: float
    service_clearance_mm: float
    required_service_clearance_mm: float
    geometry_provenance: str
    bend_spec_provenance: str
    service_envelope_provenance: str
    geometry_evidence: ControlledEvidenceReference
    bend_spec_evidence: ControlledEvidenceReference
    service_envelope_evidence: ControlledEvidenceReference

    def validate_invariants(self) -> None:
        _exact_text(self.segment_id, "segment_id")
        _positive(self.centerline_length_mm, "centerline_length_mm")
        _positive(self.internal_area_mm2, "internal_area_mm2")
        _positive(self.realized_minimum_bend_radius_mm, "realized_minimum_bend_radius_mm")
        _positive(self.required_minimum_bend_radius_mm, "required_minimum_bend_radius_mm")
        _nonnegative(self.service_clearance_mm, "service_clearance_mm")
        _nonnegative(self.required_service_clearance_mm, "required_service_clearance_mm")
        if type(self.geometry_provenance) is not str or self.geometry_provenance not in _GEOMETRY_PROVENANCE:
            raise FluidGeometryEvidenceError("geometry_provenance cannot establish realized geometry")
        if type(self.bend_spec_provenance) is not str or self.bend_spec_provenance not in _BEND_REQUIREMENT_PROVENANCE:
            raise FluidGeometryEvidenceError("bend_spec_provenance cannot establish a bend requirement")
        if type(self.service_envelope_provenance) is not str or self.service_envelope_provenance not in _SERVICE_PROVENANCE:
            raise FluidGeometryEvidenceError("service_envelope_provenance cannot establish realized service geometry")
        refs = (
            (self.geometry_evidence, self.geometry_provenance, _GEOMETRY_PROVENANCE, "geometry evidence"),
            (self.bend_spec_evidence, self.bend_spec_provenance, _BEND_REQUIREMENT_PROVENANCE, "bend-spec evidence"),
            (self.service_envelope_evidence, self.service_envelope_provenance, _SERVICE_PROVENANCE, "service evidence"),
        )
        for reference, provenance, allowed, label in refs:
            if type(reference) is not ControlledEvidenceReference:
                raise FluidGeometryEvidenceError(f"{label} must use an exact ControlledEvidenceReference")
            reference.validate_invariants()
            if reference.provenance != provenance or reference.provenance not in allowed:
                raise FluidGeometryEvidenceError(f"{label} provenance does not match its controlled record")

    def validate_evidence_registry(self, registry: ControlledEvidenceRegistry) -> None:
        self.validate_invariants()
        if type(registry) is not ControlledEvidenceRegistry:
            raise FluidGeometryEvidenceError("evidence registry must use the exact ControlledEvidenceRegistry type")
        registry.require(self.geometry_evidence, allowed_provenance=_GEOMETRY_PROVENANCE, label="geometry evidence")
        registry.require(
            self.bend_spec_evidence,
            allowed_provenance=_BEND_REQUIREMENT_PROVENANCE,
            label="bend-spec evidence",
        )
        registry.require(
            self.service_envelope_evidence,
            allowed_provenance=_SERVICE_PROVENANCE,
            label="service evidence",
        )

    @property
    def geometric_dead_volume_mL(self) -> float:
        self.validate_invariants()
        return self.centerline_length_mm * self.internal_area_mm2 / 1000.0

    @property
    def bend_margin_mm(self) -> float:
        self.validate_invariants()
        return self.realized_minimum_bend_radius_mm - self.required_minimum_bend_radius_mm

    @property
    def service_margin_mm(self) -> float:
        self.validate_invariants()
        return self.service_clearance_mm - self.required_service_clearance_mm


@dataclass(frozen=True, slots=True)
class PrimePurgeBound:
    """Separates geometric fill volume from non-geometric prime/purge allowances."""

    route_geometric_volume_mL: float
    entrained_air_allowance_mL: float
    compliance_allowance_mL: float
    wetting_retention_allowance_mL: float

    def validate_invariants(self) -> None:
        _positive(self.route_geometric_volume_mL, "route_geometric_volume_mL")
        _nonnegative(self.entrained_air_allowance_mL, "entrained_air_allowance_mL")
        _nonnegative(self.compliance_allowance_mL, "compliance_allowance_mL")
        _nonnegative(self.wetting_retention_allowance_mL, "wetting_retention_allowance_mL")

    @property
    def conservative_prime_bound_mL(self) -> float:
        self.validate_invariants()
        return (
            self.route_geometric_volume_mL
            + self.entrained_air_allowance_mL
            + self.compliance_allowance_mL
            + self.wetting_retention_allowance_mL
        )


def circular_area_mm2(inner_diameter_mm: float) -> float:
    d = _positive(inner_diameter_mm, "inner_diameter_mm")
    return pi * d * d / 4.0


def route_set_dead_volume_mL(
    routes: tuple[RouteGeometryEvidence, ...],
    *,
    evidence_registry: ControlledEvidenceRegistry | None = None,
) -> float:
    if type(routes) is not tuple or not routes:
        raise FluidGeometryEvidenceError("routes must be a non-empty exact tuple")
    seen: set[str] = set()
    total = 0.0
    for route in routes:
        if type(route) is not RouteGeometryEvidence:
            raise FluidGeometryEvidenceError("routes may contain only exact RouteGeometryEvidence records")
        route.validate_invariants()
        if evidence_registry is not None:
            route.validate_evidence_registry(evidence_registry)
        if route.segment_id in seen:
            raise FluidGeometryEvidenceError("duplicate segment geometry evidence")
        seen.add(route.segment_id)
        total += route.geometric_dead_volume_mL
    return total


def require_route_preflight_pass(
    routes: tuple[RouteGeometryEvidence, ...],
    *,
    evidence_registry: ControlledEvidenceRegistry | None = None,
) -> None:
    route_set_dead_volume_mL(routes, evidence_registry=evidence_registry)
    for route in routes:
        if route.bend_margin_mm < 0.0:
            raise FluidGeometryEvidenceError(f"{route.segment_id}: realized bend radius violates controlled requirement")
        if route.service_margin_mm < 0.0:
            raise FluidGeometryEvidenceError(f"{route.segment_id}: service clearance violates controlled requirement")


def require_exact_route_coverage(
    routes: tuple[RouteGeometryEvidence, ...],
    expected_segment_ids: tuple[str, ...],
    *,
    evidence_registry: ControlledEvidenceRegistry | None = None,
) -> None:
    """Legacy exact-coverage helper.

    The authoritative routing-closure path must use fluid_route_realization and an
    authenticated RoutingAuthorityBinding. This helper remains useful for bounded
    partial-route evidence sets but must not be represented as Iteration-28 closure.
    """
    if type(expected_segment_ids) is not tuple or not expected_segment_ids:
        raise FluidGeometryEvidenceError("expected_segment_ids must be a non-empty exact tuple")
    expected: set[str] = set()
    for segment_id in expected_segment_ids:
        _exact_text(segment_id, "expected segment_id")
        if segment_id in expected:
            raise FluidGeometryEvidenceError("controlled manifest contains duplicate segment identity")
        expected.add(segment_id)
    require_route_preflight_pass(routes, evidence_registry=evidence_registry)
    actual = {route.segment_id for route in routes}
    if actual != expected:
        missing = sorted(expected - actual)
        unknown = sorted(actual - expected)
        raise FluidGeometryEvidenceError(f"route coverage mismatch; missing={missing!r}; unknown={unknown!r}")
