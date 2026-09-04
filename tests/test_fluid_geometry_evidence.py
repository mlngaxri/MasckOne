import math

import pytest

from masck_one.fluid_geometry_evidence import (
    ControlledEvidenceReference,
    ControlledEvidenceRegistry,
    FluidGeometryEvidenceError,
    PrimePurgeBound,
    RouteGeometryEvidence,
    circular_area_mm2,
    require_exact_route_coverage,
    require_route_preflight_pass,
    route_set_dead_volume_mL,
)


def evidence(
    record_id: str,
    provenance: str,
    *,
    revision: str = "R1",
    digest: str | None = None,
):
    return ControlledEvidenceReference(
        record_id=record_id,
        revision=revision,
        sha256=digest or (record_id[0].lower() if record_id[0].lower() in "abcdef" else "a") * 64,
        provenance=provenance,
    )


def registry():
    return ControlledEvidenceRegistry(
        (
            evidence("CAD-ROUTE-001", "CAD_MEASURED", digest="a" * 64),
            evidence("SUPPLIER-BEND-001", "SUPPLIER_CONTROLLED", digest="b" * 64),
            evidence("CAD-SERVICE-001", "CAD_MEASURED", digest="c" * 64),
        )
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
        geometry_evidence=evidence("CAD-ROUTE-001", "CAD_MEASURED", digest="a" * 64),
        bend_spec_evidence=evidence("SUPPLIER-BEND-001", "SUPPLIER_CONTROLLED", digest="b" * 64),
        service_envelope_evidence=evidence("CAD-SERVICE-001", "CAD_MEASURED", digest="c" * 64),
    )
    data.update(overrides)
    return RouteGeometryEvidence(**data)


def test_dead_volume_uses_centerline_times_internal_area_only():
    r = route(centerline_length_mm=125.0, internal_area_mm2=0.8)
    assert r.geometric_dead_volume_mL == pytest.approx(0.1)


def test_circular_area_is_explicit_geometry_conversion():
    assert circular_area_mm2(2.0) == pytest.approx(math.pi)


def test_registry_is_deterministic_and_rejects_duplicate_identity():
    first = registry()
    second = registry()
    assert first.manifest == second.manifest
    assert first.manifest_sha256 == second.manifest_sha256
    duplicate = ControlledEvidenceRegistry(
        (
            evidence("CAD-ROUTE-001", "CAD_MEASURED", digest="a" * 64),
            evidence("CAD-ROUTE-001", "CAD_MEASURED", digest="d" * 64),
        )
    )
    with pytest.raises(FluidGeometryEvidenceError, match="duplicate record identity"):
        duplicate.validate_invariants()


def test_route_requires_controlled_record_identity_revision_hash_and_provenance():
    route().validate_evidence_registry(registry())

    wrong_revision = route(
        geometry_evidence=evidence(
            "CAD-ROUTE-001",
            "CAD_MEASURED",
            revision="R2",
            digest="a" * 64,
        )
    )
    with pytest.raises(FluidGeometryEvidenceError, match="does not match"):
        wrong_revision.validate_evidence_registry(registry())

    wrong_hash = route(
        geometry_evidence=evidence(
            "CAD-ROUTE-001",
            "CAD_MEASURED",
            digest="d" * 64,
        )
    )
    with pytest.raises(FluidGeometryEvidenceError, match="does not match"):
        wrong_hash.validate_evidence_registry(registry())

    missing = route(
        geometry_evidence=evidence(
            "CAD-ROUTE-UNKNOWN",
            "CAD_MEASURED",
            digest="d" * 64,
        )
    )
    with pytest.raises(FluidGeometryEvidenceError, match="does not match"):
        missing.validate_evidence_registry(registry())


def test_provenance_category_cannot_substitute_for_record_identity():
    with pytest.raises(FluidGeometryEvidenceError, match="provenance"):
        route(
            geometry_evidence=evidence(
                "CAD-ROUTE-001",
                "PHYSICAL_MEASURED",
                digest="a" * 64,
            )
        ).validate_invariants()
    with pytest.raises(FluidGeometryEvidenceError, match="bend-spec"):
        route(
            bend_spec_evidence=evidence(
                "SUPPLIER-BEND-001",
                "CAD_MEASURED",
                digest="b" * 64,
            )
        ).validate_invariants()


def test_route_set_rejects_duplicate_identity_and_revalidates_registry():
    with pytest.raises(FluidGeometryEvidenceError, match="duplicate"):
        route_set_dead_volume_mL((route(), route()), evidence_registry=registry())
    assert route_set_dead_volume_mL((route(),), evidence_registry=registry()) == pytest.approx(0.1)


def test_bend_and_service_fail_closed_independently():
    with pytest.raises(FluidGeometryEvidenceError, match="bend radius"):
        require_route_preflight_pass(
            (route(realized_minimum_bend_radius_mm=5.9),),
            evidence_registry=registry(),
        )
    with pytest.raises(FluidGeometryEvidenceError, match="service clearance"):
        require_route_preflight_pass(
            (route(service_clearance_mm=1.9),),
            evidence_registry=registry(),
        )


def test_prime_bound_does_not_alias_geometric_dead_volume():
    p = PrimePurgeBound(0.20, 0.05, 0.03, 0.02)
    assert p.conservative_prime_bound_mL == pytest.approx(0.30)


def test_unknown_provenance_nonfinite_boolean_and_bad_sha_are_rejected():
    with pytest.raises(FluidGeometryEvidenceError):
        route(geometry_provenance="ESTIMATED").validate_invariants()
    with pytest.raises(FluidGeometryEvidenceError):
        route(centerline_length_mm=math.inf).validate_invariants()
    with pytest.raises(FluidGeometryEvidenceError):
        route(centerline_length_mm=True).validate_invariants()
    bad = evidence("CAD-ROUTE-001", "CAD_MEASURED", digest="a" * 64)
    object.__setattr__(bad, "sha256", "not-a-sha")
    with pytest.raises(FluidGeometryEvidenceError, match="SHA-256"):
        bad.validate_invariants()


def test_cad_measurement_cannot_authorize_bend_requirement():
    candidate = route(
        bend_spec_provenance="CAD_MEASURED",
        bend_spec_evidence=evidence("SUPPLIER-BEND-001", "CAD_MEASURED", digest="b" * 64),
    )
    with pytest.raises(FluidGeometryEvidenceError):
        candidate.validate_invariants()


def test_post_construction_nested_evidence_corruption_fails_before_consumption():
    r = route()
    object.__setattr__(r.geometry_evidence, "sha256", "d" * 64)
    with pytest.raises(FluidGeometryEvidenceError, match="does not match"):
        route_set_dead_volume_mL((r,), evidence_registry=registry())


def test_hostile_subclasses_and_mutable_containers_fail_closed():
    class HostileStr(str):
        pass

    hostile = evidence("CAD-ROUTE-001", "CAD_MEASURED", digest="a" * 64)
    object.__setattr__(hostile, "record_id", HostileStr("CAD-ROUTE-001"))
    with pytest.raises(FluidGeometryEvidenceError):
        hostile.validate_invariants()
    with pytest.raises(FluidGeometryEvidenceError):
        ControlledEvidenceRegistry(list(registry().records)).validate_invariants()


def test_signed_zero_prime_allowances_are_canonical_nonnegative_inputs():
    p = PrimePurgeBound(0.20, -0.0, -0.0, -0.0)
    p.validate_invariants()
    assert p.conservative_prime_bound_mL == pytest.approx(0.20)


def test_exact_coverage_remains_partial_helper_not_authority_closure():
    manifest = ("WATER_SOURCE_TO_PUMP", "PUMP_TO_MANIFOLD")
    with pytest.raises(FluidGeometryEvidenceError):
        require_exact_route_coverage((route(),), manifest, evidence_registry=registry())
    routes = (
        route(),
        route(segment_id="PUMP_TO_MANIFOLD"),
    )
    require_exact_route_coverage(routes, manifest, evidence_registry=registry())
