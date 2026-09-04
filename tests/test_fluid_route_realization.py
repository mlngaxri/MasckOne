import math
from dataclasses import replace

import pytest

from masck_one.fluid_geometry_evidence import (
    ControlledEvidenceReference,
    ControlledEvidenceRegistry,
)
from masck_one.fluid_route_realization import (
    ITERATION_28_RELEASE_COMMIT_SHA,
    FluidRouteRealizationError,
    RealizedRouteGeometry,
    build_routing_authority_binding,
    realized_route_set_dead_volume_mL,
    require_topology_binding,
)
from masck_one.fluid_routing_checks import (
    ARCHITECTURE_EVIDENCE_STATUS,
    BEND_RADIUS_STATUS,
    DEAD_VOLUME_STATUS,
    QUANTITATIVE_CLOSURE_STATUS,
    SERVICE_CLEARANCE_STATUS,
    SYSTEM_FRESH,
    TOPOLOGY_STATUS,
    FluidRoutingClosureArchitecture,
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


def second_segment():
    return segment(
        segment_id="ROUTE-WATER-PUMP-TO-MANIFOLD-I23",
        source_interface_id="PUMP-OUTLET-WATER",
        target_interface_id="MANIFOLD-INLET-WATER",
        stage="FRESH_PUMP_TO_MANIFOLD",
    )


def routing():
    return FluidRoutingClosureArchitecture(
        source_fresh_pump_sha256="1" * 64,
        source_manifold_sha256="2" * 64,
        source_distribution_sha256="3" * 64,
        source_waste_acquisition_sha256="4" * 64,
        source_waste_pump_sha256="5" * 64,
        source_waste_cartridge_sha256="6" * 64,
        source_structural_frame_sha256="7" * 64,
        source_authority_revision="AUTH-R1",
        maximum_initial_prime_mL=0.40,
        maximum_initial_prime_status="VALIDATION_GATED",
        segments=(segment(), second_segment()),
        total_route_dead_volume_mL=None,
        minimum_route_service_clearance_mm=None,
        quantitative_closure_status=QUANTITATIVE_CLOSURE_STATUS,
        physical_validation_eligible=False,
        evidence_status=ARCHITECTURE_EVIDENCE_STATUS,
    )


def evidence():
    return ControlledEvidenceReference(
        record_id="CAD-ROUTING-RELEASE-001",
        revision="CAD-ROUTING-R1",
        sha256="a" * 64,
        provenance="CAD_MEASURED",
    )


def evidence_registry():
    return ControlledEvidenceRegistry((evidence(),))


def route_for(seg=None, **overrides):
    seg = seg or segment()
    authority = build_routing_authority_binding(routing())
    data = dict(
        segment_id=seg.segment_id,
        system=seg.system,
        phase_identity=seg.phase_identity,
        source_interface_id=seg.source_interface_id,
        target_interface_id=seg.target_interface_id,
        centerline_points_mm=((0.0, 0.0, 0.0), (30.0, 40.0, 0.0), (30.0, 40.0, 20.0)),
        span_internal_area_mm2=(1.0, 2.0),
        maximum_tessellation_chord_error_mm=0.05,
        geometry_provenance="CAD_MEASURED",
        source_geometry_revision="CAD-ROUTING-R1",
        geometry_evidence=evidence(),
        routing_release_commit_sha=authority.release_commit_sha,
        routing_authority_sha256=authority.routing_architecture_sha256,
        routing_authority_revision=authority.source_authority_revision,
    )
    data.update(overrides)
    return RealizedRouteGeometry(**data)


def test_centerline_length_is_derived_from_explicit_xyz_vertices():
    r = route_for()
    assert r.span_lengths_mm == pytest.approx((50.0, 20.0))
    assert r.centerline_length_mm == pytest.approx(70.0)


def test_dead_volume_integrates_each_realized_span_area():
    assert route_for().geometric_dead_volume_mL == pytest.approx(0.09)


def test_authority_binding_uses_exact_release_commit_architecture_sha_and_revision():
    controlled = routing()
    authority = build_routing_authority_binding(controlled)
    assert authority.release_commit_sha == ITERATION_28_RELEASE_COMMIT_SHA
    assert authority.routing_architecture_sha256 == controlled.architecture_sha256
    assert authority.source_authority_revision == controlled.source_authority_revision
    second = build_routing_authority_binding(controlled)
    assert authority.manifest == second.manifest
    assert authority.manifest_sha256 == second.manifest_sha256


def test_stale_or_spoofed_authority_binding_fails_closed():
    controlled = routing()
    authority = build_routing_authority_binding(controlled)

    with pytest.raises(FluidRouteRealizationError, match="release commit"):
        replace(authority, release_commit_sha="b" * 64)

    with pytest.raises(FluidRouteRealizationError, match="architecture SHA"):
        replace(authority, routing_architecture_sha256="b" * 64).validate_against(controlled)

    with pytest.raises(FluidRouteRealizationError, match="authority revision"):
        replace(authority, source_authority_revision="STALE").validate_against(controlled)


def test_geometry_evidence_requires_controlled_identity_revision_and_hash():
    r = route_for()
    r.validate_evidence_registry(evidence_registry())

    wrong_revision = route_for(
        geometry_evidence=ControlledEvidenceReference(
            "CAD-ROUTING-RELEASE-001",
            "CAD-ROUTING-R2",
            "a" * 64,
            "CAD_MEASURED",
        ),
        source_geometry_revision="CAD-ROUTING-R2",
    )
    with pytest.raises(FluidRouteRealizationError, match="not authenticated"):
        wrong_revision.validate_evidence_registry(evidence_registry())

    wrong_hash = route_for(
        geometry_evidence=ControlledEvidenceReference(
            "CAD-ROUTING-RELEASE-001",
            "CAD-ROUTING-R1",
            "b" * 64,
            "CAD_MEASURED",
        )
    )
    with pytest.raises(FluidRouteRealizationError, match="not authenticated"):
        wrong_hash.validate_evidence_registry(evidence_registry())


def test_realized_route_binds_exact_phase_source_target_and_authenticated_segment():
    controlled = routing()
    authority = build_routing_authority_binding(controlled)
    seg = controlled.segments[0]
    require_topology_binding(
        route_for(seg),
        seg,
        authority=authority,
        routing=controlled,
        evidence_registry=evidence_registry(),
    )
    with pytest.raises(FluidRouteRealizationError, match="topology identity"):
        require_topology_binding(
            route_for(seg, phase_identity="CLEANSER"),
            seg,
            authority=authority,
            routing=controlled,
        )
    with pytest.raises(FluidRouteRealizationError, match="topology identity"):
        require_topology_binding(
            route_for(seg, target_interface_id="OTHER"),
            seg,
            authority=authority,
            routing=controlled,
        )


def test_route_cannot_carry_stale_release_architecture_or_revision_binding():
    controlled = routing()
    authority = build_routing_authority_binding(controlled)
    seg = controlled.segments[0]
    for changes in (
        {"routing_release_commit_sha": "b" * 64},
        {"routing_authority_sha256": "b" * 64},
        {"routing_authority_revision": "STALE"},
    ):
        with pytest.raises(FluidRouteRealizationError):
            require_topology_binding(
                route_for(seg, **changes),
                seg,
                authority=authority,
                routing=controlled,
            )


def test_route_set_requires_exact_one_to_one_authenticated_coverage():
    controlled = routing()
    authority = build_routing_authority_binding(controlled)
    r1 = route_for(controlled.segments[0])
    r2 = route_for(controlled.segments[1])
    assert realized_route_set_dead_volume_mL(
        (r1, r2),
        authority=authority,
        routing=controlled,
        evidence_registry=evidence_registry(),
    ) == pytest.approx(0.18)

    with pytest.raises(FluidRouteRealizationError, match="exactly cover"):
        realized_route_set_dead_volume_mL(
            (r1,),
            authority=authority,
            routing=controlled,
        )

    with pytest.raises(FluidRouteRealizationError, match="duplicate"):
        realized_route_set_dead_volume_mL(
            (r1, r1),
            authority=authority,
            routing=controlled,
        )

    invented = route_for(
        controlled.segments[1],
        segment_id="INVENTED-SEGMENT",
    )
    with pytest.raises(FluidRouteRealizationError, match="unknown"):
        realized_route_set_dead_volume_mL(
            (r1, invented),
            authority=authority,
            routing=controlled,
        )


def test_nested_geometry_evidence_is_revalidated_before_aggregate():
    controlled = routing()
    authority = build_routing_authority_binding(controlled)
    r1 = route_for(controlled.segments[0])
    r2 = route_for(controlled.segments[1])
    object.__setattr__(r2.geometry_evidence, "sha256", "b" * 64)
    with pytest.raises(FluidRouteRealizationError, match="not authenticated"):
        realized_route_set_dead_volume_mL(
            (r1, r2),
            authority=authority,
            routing=controlled,
            evidence_registry=evidence_registry(),
        )


def test_post_construction_routing_segment_mutation_invalidates_authority():
    controlled = routing()
    authority = build_routing_authority_binding(controlled)
    object.__setattr__(controlled.segments[0], "source_interface_id", "CORRUPTED")
    with pytest.raises(FluidRouteRealizationError):
        authority.validate_against(controlled)


def test_zero_length_nonfinite_bool_mutable_and_negative_signed_zero_fail_closed():
    with pytest.raises(FluidRouteRealizationError):
        route_for(centerline_points_mm=((0.0, 0.0, 0.0), (0.0, 0.0, 0.0))).validate_invariants()
    with pytest.raises(FluidRouteRealizationError):
        route_for(centerline_points_mm=((0.0, 0.0, 0.0), (math.inf, 0.0, 0.0))).validate_invariants()
    with pytest.raises(FluidRouteRealizationError):
        route_for(centerline_points_mm=[(0.0, 0.0, 0.0), (1.0, 0.0, 0.0)]).validate_invariants()
    with pytest.raises(FluidRouteRealizationError):
        route_for(span_internal_area_mm2=[1.0, 2.0]).validate_invariants()
    with pytest.raises(FluidRouteRealizationError):
        route_for(maximum_tessellation_chord_error_mm=True).validate_invariants()
    with pytest.raises(FluidRouteRealizationError, match="negative signed zero"):
        route_for(centerline_points_mm=((-0.0, 0.0, 0.0), (1.0, 0.0, 0.0))).validate_invariants()


def test_hostile_reference_subclass_and_post_construction_identity_corruption_fail():
    class HostileEvidence(ControlledEvidenceReference):
        pass

    hostile = HostileEvidence(
        "CAD-ROUTING-RELEASE-001",
        "CAD-ROUTING-R1",
        "a" * 64,
        "CAD_MEASURED",
    )
    with pytest.raises(FluidRouteRealizationError, match="ControlledEvidenceReference"):
        route_for(geometry_evidence=hostile).validate_invariants()

    r = route_for()
    object.__setattr__(r, "source_interface_id", "OTHER")
    controlled = routing()
    authority = build_routing_authority_binding(controlled)
    with pytest.raises(FluidRouteRealizationError, match="topology identity"):
        require_topology_binding(
            r,
            controlled.segments[0],
            authority=authority,
            routing=controlled,
        )
