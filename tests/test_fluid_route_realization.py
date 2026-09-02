import math
import pytest

from masck_one.fluid_route_realization import (
    FluidRouteRealizationError,
    RealizedRouteGeometry,
    realized_route_set_dead_volume_mL,
    require_topology_binding,
)
from masck_one.fluid_routing_checks import (
    BEND_RADIUS_STATUS,
    DEAD_VOLUME_STATUS,
    SERVICE_CLEARANCE_STATUS,
    SYSTEM_FRESH,
    TOPOLOGY_STATUS,
    RoutingSegmentCheck,
)


def segment(**overrides):
    data = dict(
        segment_id="ROUTE-WATER-RESERVOIR-TO-PUMP",
        system=SYSTEM_FRESH,
        phase_identity="FRESH_WATER",
        stage="FRESH_SOURCE_TO_PUMP",
        source_interface_id="WATER-PICKUP",
        target_interface_id="PUMP-STATION-WATER",
        centerline_length_mm=None,
        inner_diameter_mm=None,
        minimum_bend_radius_spec_mm=None,
        realized_minimum_bend_radius_mm=None,
        dead_volume_mL=None,
        service_clearance_mm=None,
        topology_status=TOPOLOGY_STATUS,
        bend_radius_status=BEND_RADIUS_STATUS,
        dead_volume_status=DEAD_VOLUME_STATUS,
        service_clearance_status=SERVICE_CLEARANCE_STATUS,
    )
    data.update(overrides)
    return RoutingSegmentCheck(**data)


def route(**overrides):
    data = dict(
        segment_id="ROUTE-WATER-RESERVOIR-TO-PUMP",
        system=SYSTEM_FRESH,
        phase_identity="FRESH_WATER",
        source_interface_id="WATER-PICKUP",
        target_interface_id="PUMP-STATION-WATER",
        centerline_points_mm=((0.0, 0.0, 0.0), (30.0, 40.0, 0.0), (30.0, 40.0, 20.0)),
        span_internal_area_mm2=(1.0, 2.0),
        maximum_tessellation_chord_error_mm=0.05,
        geometry_provenance="CAD_MEASURED",
        source_geometry_revision="CAD-ROUTING-R1",
    )
    data.update(overrides)
    return RealizedRouteGeometry(**data)


def test_centerline_length_is_derived_from_explicit_xyz_vertices():
    r = route()
    assert r.span_lengths_mm == pytest.approx((50.0, 20.0))
    assert r.centerline_length_mm == pytest.approx(70.0)


def test_dead_volume_integrates_each_realized_span_area():
    # 50 mm * 1 mm2 + 20 mm * 2 mm2 = 90 mm3 = 0.09 mL.
    assert route().geometric_dead_volume_mL == pytest.approx(0.09)


def test_zero_length_and_nonfinite_geometry_fail_closed():
    with pytest.raises(FluidRouteRealizationError):
        route(centerline_points_mm=((0.0, 0.0, 0.0), (0.0, 0.0, 0.0))).validate_invariants()
    with pytest.raises(FluidRouteRealizationError):
        route(centerline_points_mm=((0.0, 0.0, 0.0), (math.inf, 0.0, 0.0))).validate_invariants()


def test_span_area_count_must_match_centerline_spans():
    with pytest.raises(FluidRouteRealizationError):
        route(span_internal_area_mm2=(1.0,)).validate_invariants()


def test_scalar_and_hostile_container_aliases_are_rejected():
    with pytest.raises(FluidRouteRealizationError):
        route(centerline_points_mm=[(0.0, 0.0, 0.0), (1.0, 0.0, 0.0)]).validate_invariants()
    with pytest.raises(FluidRouteRealizationError):
        route(span_internal_area_mm2=[1.0, 2.0]).validate_invariants()
    with pytest.raises(FluidRouteRealizationError):
        route(maximum_tessellation_chord_error_mm=True).validate_invariants()


def test_realized_route_binds_exact_phase_and_interfaces_to_topology():
    require_topology_binding(route(), segment())
    with pytest.raises(FluidRouteRealizationError):
        require_topology_binding(route(phase_identity="CLEANSER"), segment())
    with pytest.raises(FluidRouteRealizationError):
        require_topology_binding(route(target_interface_id="OTHER"), segment())


def test_post_construction_identity_corruption_fails_before_binding():
    r = route()
    object.__setattr__(r, "source_interface_id", "OTHER")
    with pytest.raises(FluidRouteRealizationError):
        require_topology_binding(r, segment())


def test_route_set_requires_exact_one_to_one_topology_coverage():
    s1 = segment()
    s2 = segment(
        segment_id="ROUTE-WATER-PUMP-TO-MANIFOLD-I23",
        source_interface_id="PUMP-OUTLET-WATER",
        target_interface_id="MANIFOLD-INLET-WATER",
        stage="FRESH_PUMP_TO_MANIFOLD",
    )
    r1 = route()
    r2 = route(
        segment_id=s2.segment_id,
        source_interface_id=s2.source_interface_id,
        target_interface_id=s2.target_interface_id,
    )
    assert realized_route_set_dead_volume_mL((r1, r2), (s1, s2)) == pytest.approx(0.18)
    with pytest.raises(FluidRouteRealizationError):
        realized_route_set_dead_volume_mL((r1,), (s1, s2))
    with pytest.raises(FluidRouteRealizationError):
        realized_route_set_dead_volume_mL((r1, r1), (s1, s2))


def test_geometry_provenance_must_be_realized_evidence():
    with pytest.raises(FluidRouteRealizationError):
        route(geometry_provenance="ESTIMATED").validate_invariants()
