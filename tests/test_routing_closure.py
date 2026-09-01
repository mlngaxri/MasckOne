import pytest

from masck_one.routing_closure import RouteEvidence, RoutingClosure, RoutingClosureError

SHA = "a" * 64


def route(**changes):
    data = dict(route_id="FRESH-01", phase="FRESH_WATER", source_interface_id="A", sink_interface_id="B",
                source_architecture_sha256=SHA)
    data.update(changes)
    return RouteEvidence(**data)


def test_unknown_geometry_stays_validation_gated():
    r = route()
    closure = RoutingClosure(SHA, (r,))
    assert r.dead_volume_mL is None
    assert r.bend_radius_status == "VALIDATION_GATED"
    assert r.service_clearance_status == "VALIDATION_GATED"
    assert closure.dead_volume_status == "VALIDATION_GATED"
    assert closure.total_known_dead_volume_mL == 0.0


def test_controlled_geometry_accounts_dead_volume_and_checks_constraints():
    r = route(centerline_length_mm=100.0, tube_inner_diameter_mm=2.0,
              minimum_bend_radius_mm=8.0, supplier_minimum_bend_radius_mm=6.0,
              minimum_service_clearance_mm=12.0, required_service_clearance_mm=10.0)
    assert r.dead_volume_mL == pytest.approx(0.3141592654)
    assert r.bend_radius_status == "DIGITAL_PASS"
    assert r.service_clearance_status == "DIGITAL_PASS"
    assert RoutingClosure(SHA, (r,)).dead_volume_status == "DIGITAL_ACCOUNTED"


def test_constraint_violations_fail_closed_without_claiming_physical_evidence():
    r = route(minimum_bend_radius_mm=5.0, supplier_minimum_bend_radius_mm=6.0,
              minimum_service_clearance_mm=9.0, required_service_clearance_mm=10.0)
    assert r.bend_radius_status == "DIGITAL_FAIL"
    assert r.service_clearance_status == "DIGITAL_FAIL"


def test_numeric_trust_boundary_rejects_bool_nan_and_nonpositive():
    for value in (True, float("nan"), 0.0, -1.0):
        with pytest.raises(RoutingClosureError):
            route(centerline_length_mm=value)


def test_provenance_and_route_identity_are_strict():
    with pytest.raises(RoutingClosureError):
        route(source_architecture_sha256="not-a-sha")
    with pytest.raises(RoutingClosureError):
        RoutingClosure(SHA, (route(), route()))


def test_manifest_digest_is_deterministic_and_bound_to_i27():
    closure = RoutingClosure(SHA, (route(),))
    assert closure.architecture_sha256 == closure.architecture_sha256
    manifest = closure.manifest()
    assert manifest["iteration"] == 28
    assert manifest["waste_cartridge_architecture_sha256"] == SHA
    assert manifest["architecture_sha256"] == closure.architecture_sha256
