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
_ALLOWED_PROVENANCE = {
    PROVENANCE_CAD_MEASURED,
    PROVENANCE_SUPPLIER_CONTROLLED,
    PROVENANCE_PHYSICAL_MEASURED,
}


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
        if type(self.segment_id) is not str or not self.segment_id.strip() or self.segment_id != self.segment_id.strip():
            raise FluidGeometryEvidenceError("segment_id must be exact nonblank text")
        _positive(self.centerline_length_mm, "centerline_length_mm")
        _positive(self.internal_area_mm2, "internal_area_mm2")
        _positive(self.realized_minimum_bend_radius_mm, "realized_minimum_bend_radius_mm")
        _positive(self.required_minimum_bend_radius_mm, "required_minimum_bend_radius_mm")
        _nonnegative(self.service_clearance_mm, "service_clearance_mm")
        _nonnegative(self.required_service_clearance_mm, "required_service_clearance_mm")
        for label, value in (
            ("geometry_provenance", self.geometry_provenance),
            ("bend_spec_provenance", self.bend_spec_provenance),
            ("service_envelope_provenance", self.service_envelope_provenance),
        ):
            if type(value) is not str or value not in _ALLOWED_PROVENANCE:
                raise FluidGeometryEvidenceError(f"{label} is not controlled provenance")

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
    """Fail closed on bend/service geometry. Does not assert leakage or hydraulic performance."""
    route_set_dead_volume_mL(routes)
    for route in routes:
        if route.bend_margin_mm < 0.0:
            raise FluidGeometryEvidenceError(f"{route.segment_id}: realized bend radius violates controlled requirement")
        if route.service_margin_mm < 0.0:
            raise FluidGeometryEvidenceError(f"{route.segment_id}: service clearance violates controlled requirement")
