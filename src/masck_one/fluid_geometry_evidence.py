"""Physical fluid-route geometry evidence and hydraulic preflight.

This module is intentionally downstream of the Iteration 28 topology ledger. It accepts
realized route measurements only when their provenance is explicit. Calculations are
engineering preflight, never physical performance evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite, pi


class FluidGeometryEvidenceError(ValueError):
    pass


PROVENANCE_CAD_MEASURED = "CAD_MEASURED"
PROVENANCE_SUPPLIER_CONTROLLED = "SUPPLIER_CONTROLLED"
PROVENANCE_PHYSICAL_MEASURED = "PHYSICAL_MEASURED"
_GEOMETRY_PROVENANCE = {PROVENANCE_CAD_MEASURED, PROVENANCE_PHYSICAL_MEASURED}
_BEND_REQUIREMENT_PROVENANCE = {PROVENANCE_SUPPLIER_CONTROLLED, PROVENANCE_PHYSICAL_MEASURED}
_SERVICE_PROVENANCE = {PROVENANCE_CAD_MEASURED, PROVENANCE_PHYSICAL_MEASURED}


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
        raise FluidGeometryEvidenceError(f"{label} must be exact nonblank text")
    return value


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
    """Separates geometric fill volume from experimentally observed prime/purge burden."""

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


def route_set_dead_volume_mL(routes: tuple[RouteGeometryEvidence, ...]) -> float:
    """Aggregate a caller-declared partial evidence set. This is not topology closure."""
    if type(routes) is not tuple or not routes:
        raise FluidGeometryEvidenceError("routes must be a non-empty exact tuple")
    seen: set[str] = set()
    total = 0.0
    for route in routes:
        if type(route) is not RouteGeometryEvidence:
            raise FluidGeometryEvidenceError("routes may contain only exact RouteGeometryEvidence records")
        route.validate_invariants()
        if route.segment_id in seen:
            raise FluidGeometryEvidenceError("duplicate segment geometry evidence")
        seen.add(route.segment_id)
        total += route.geometric_dead_volume_mL
    return total


def require_route_preflight_pass(routes: tuple[RouteGeometryEvidence, ...]) -> None:
    """Partial-route bend/service preflight. Never represents Iteration-28 topology closure."""
    route_set_dead_volume_mL(routes)
    for route in routes:
        if route.bend_margin_mm < 0.0:
            raise FluidGeometryEvidenceError(f"{route.segment_id}: realized bend radius violates controlled requirement")
        if route.service_margin_mm < 0.0:
            raise FluidGeometryEvidenceError(f"{route.segment_id}: service clearance violates controlled requirement")


def require_exact_route_coverage(
    routes: tuple[RouteGeometryEvidence, ...], expected_segment_ids: tuple[str, ...]
) -> None:
    """Fail closed unless the evidence set exactly covers a controlled manifest supplied by its owner.

    This function deliberately does not manufacture the Iteration-28 manifest. The topology authority
    must supply that manifest from the released artifact. Binding to its source SHA and canonical
    phase/source/destination identity remains a release blocker until that authority is exposed here.
    """
    if type(expected_segment_ids) is not tuple or not expected_segment_ids:
        raise FluidGeometryEvidenceError("expected_segment_ids must be a non-empty exact tuple")
    expected: set[str] = set()
    for segment_id in expected_segment_ids:
        _exact_text(segment_id, "expected segment_id")
        if segment_id in expected:
            raise FluidGeometryEvidenceError("controlled manifest contains duplicate segment identity")
        expected.add(segment_id)
    require_route_preflight_pass(routes)
    actual = {route.segment_id for route in routes}
    if actual != expected:
        missing = sorted(expected - actual)
        unknown = sorted(actual - expected)
        raise FluidGeometryEvidenceError(f"route coverage mismatch; missing={missing!r}; unknown={unknown!r}")
