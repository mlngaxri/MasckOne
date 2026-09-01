from dataclasses import replace

import pytest

from masck_one.fluid_routing_closure import (
    ARCHITECTURE_EVIDENCE_STATUS,
    FluidRoutingClosureError,
    ROUTE_IDS,
    build_fluid_routing_closure,
)

SHA_A = "a" * 64
SHA_B = "b" * 64
SHA_C = "c" * 64


def build():
    return build_fluid_routing_closure(
        fresh_architecture_sha256=SHA_A,
        waste_pump_architecture_sha256=SHA_B,
        waste_cartridge_architecture_sha256=SHA_C,
    )


def test_closure_contains_every_route_and_stays_evidence_safe():
    closure = build()
    assert tuple(route.route_id for route in closure.routes) == ROUTE_IDS
    assert closure.architecture_evidence_status == ARCHITECTURE_EVIDENCE_STATUS
    assert all(route.dead_volume_mL is None for route in closure.routes)
    assert all(route.minimum_bend_radius_mm is None for route in closure.routes)
    assert all(route.minimum_service_clearance_mm is None for route in closure.routes)
    assert len(closure.manifest()["architecture_sha256"]) == 64


def test_rejects_invented_route_geometry_or_dead_volume():
    route = build().routes[0]
    with pytest.raises(FluidRoutingClosureError):
        replace(route, centerline_length_mm=100.0)
    with pytest.raises(FluidRoutingClosureError):
        replace(route, dead_volume_mL=0.5)
    with pytest.raises(FluidRoutingClosureError):
        replace(route, minimum_bend_radius_mm=4.0)


def test_rejects_promoted_status_and_bad_provenance():
    route = build().routes[0]
    with pytest.raises(FluidRoutingClosureError):
        replace(route, hydraulic_status="PASS")
    with pytest.raises(FluidRoutingClosureError):
        build_fluid_routing_closure(
            fresh_architecture_sha256="not-a-sha",
            waste_pump_architecture_sha256=SHA_B,
            waste_cartridge_architecture_sha256=SHA_C,
        )


def test_rejects_missing_duplicate_or_unknown_routes():
    closure = build()
    with pytest.raises(FluidRoutingClosureError):
        replace(closure, routes=closure.routes[:-1])
    duplicated = closure.routes[:-1] + (closure.routes[0],)
    with pytest.raises(FluidRoutingClosureError):
        replace(closure, routes=duplicated)
    with pytest.raises(FluidRoutingClosureError):
        replace(closure.routes[0], route_id="UNCONTROLLED-ROUTE")
