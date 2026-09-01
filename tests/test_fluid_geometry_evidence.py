import math
import pytest

from masck_one.fluid_geometry_evidence import (
    FluidGeometryEvidenceError,
    PrimePurgeBound,
    RouteGeometryEvidence,
    circular_area_mm2,
    require_exact_route_coverage,
    require_route_preflight_pass,
    route_set_dead_volume_mL,
)


def route(**overrides):
    data = dict(
        segment_id="WATER_SOURCE_TO_PUMP",
        centerline_length_mm=100.0,
        internal_area_mm2=1.0,
        realized_minimum_bend_radius_mm=8.0,
        required_minimum_bend_radius_mm=6.0,
        service_clearance_mm=3.0,
        required_service_clearance_mm=2.0,
        geometry_provenance="CAD_MEASURED",
        bend_spec_provenance="SUPPLIER_CONTROLLED",
        service_envelope_provenance="CAD_MEASURED",
    )
    data.update(overrides)
    return RouteGeometryEvidence(**data)


def test_dead_volume_uses_centerline_times_internal_area_only():
    r = route(centerline_length_mm=125.0, internal_area_mm2=0.8)
    assert r.geometric_dead_volume_mL == pytest.approx(0.1)


def test_circular_area_is_explicit_geometry_conversion():
    assert circular_area_mm2(2.0) == pytest.approx(math.pi)


def test_route_set_rejects_duplicate_identity():
    with pytest.raises(FluidGeometryEvidenceError):
        route_set_dead_volume_mL((route(), route()))


def test_bend_and_service_fail_closed_independently():
    with pytest.raises(FluidGeometryEvidenceError):
        require_route_preflight_pass((route(realized_minimum_bend_radius_mm=5.9),))
    with pytest.raises(FluidGeometryEvidenceError):
        require_route_preflight_pass((route(service_clearance_mm=1.9),))


def test_prime_bound_does_not_alias_geometric_dead_volume():
    p = PrimePurgeBound(0.20, 0.05, 0.03, 0.02)
    assert p.conservative_prime_bound_mL == pytest.approx(0.30)


def test_unknown_provenance_and_nonfinite_geometry_rejected():
    with pytest.raises(FluidGeometryEvidenceError):
        route(geometry_provenance="ESTIMATED").validate_invariants()
    with pytest.raises(FluidGeometryEvidenceError):
        route(centerline_length_mm=math.inf).validate_invariants()


def test_cad_measurement_cannot_authorize_bend_requirement():
    with pytest.raises(FluidGeometryEvidenceError):
        route(bend_spec_provenance="CAD_MEASURED").validate_invariants()


def test_post_construction_corruption_fails_before_consumption():
    r = route()
    object.__setattr__(r, "internal_area_mm2", -1.0)
    with pytest.raises(FluidGeometryEvidenceError):
        _ = r.geometric_dead_volume_mL


def test_post_construction_identity_corruption_fails_before_set_consumption():
    r = route()
    object.__setattr__(r, "segment_id", " WATER_SOURCE_TO_PUMP")
    with pytest.raises(FluidGeometryEvidenceError):
        route_set_dead_volume_mL((r,))


def test_boolean_numeric_alias_rejected():
    with pytest.raises(FluidGeometryEvidenceError):
        route(centerline_length_mm=True).validate_invariants()


def test_signed_zero_is_canonicalized_for_nonnegative_prime_allowances():
    p = PrimePurgeBound(0.20, -0.0, -0.0, -0.0)
    p.validate_invariants()
    assert p.conservative_prime_bound_mL == pytest.approx(0.20)


def test_exact_coverage_rejects_incomplete_and_unknown_routes():
    manifest = ("WATER_SOURCE_TO_PUMP", "PUMP_TO_MANIFOLD")
    with pytest.raises(FluidGeometryEvidenceError):
        require_exact_route_coverage((route(),), manifest)
    with pytest.raises(FluidGeometryEvidenceError):
        require_exact_route_coverage((route(segment_id="INVENTED_SEGMENT"),), manifest)


def test_exact_coverage_accepts_only_one_to_one_manifest_identity():
    manifest = ("WATER_SOURCE_TO_PUMP", "PUMP_TO_MANIFOLD")
    routes = (route(), route(segment_id="PUMP_TO_MANIFOLD"))
    require_exact_route_coverage(routes, manifest)


def test_manifest_rejects_hostile_string_subclass_and_duplicates():
    class HostileStr(str):
        pass

    with pytest.raises(FluidGeometryEvidenceError):
        require_exact_route_coverage((route(),), (HostileStr("WATER_SOURCE_TO_PUMP"),))
    with pytest.raises(FluidGeometryEvidenceError):
        require_exact_route_coverage((route(),), ("WATER_SOURCE_TO_PUMP", "WATER_SOURCE_TO_PUMP"))
