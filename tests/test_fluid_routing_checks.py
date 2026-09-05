from dataclasses import replace

import pytest

from masck_one.boundary_release import build_verified_interface_boundary_topology
from masck_one.cleanser_storage import build_cleanser_storage_architecture
from masck_one.distribution_geometry import build_distribution_geometry_architecture
from masck_one.distribution_manifold import build_distribution_manifold_architecture
from masck_one.fluid_routing_checks import (
    ARCHITECTURE_EVIDENCE_STATUS,
    BEND_RADIUS_STATUS,
    DEAD_VOLUME_STATUS,
    QUANTITATIVE_CLOSURE_STATUS,
    SERVICE_CLEARANCE_STATUS,
    STAGE_FRESH_BRANCH_TO_OUTLET,
    STAGE_FRESH_MANIFOLD_BRANCH,
    STAGE_FRESH_OUTLET_TO_GROOVE,
    STAGE_FRESH_PUMP_TO_MANIFOLD,
    STAGE_FRESH_SOURCE_TO_PUMP,
    STAGE_WASTE_ACQUISITION_TO_PUMP,
    STAGE_WASTE_CARTRIDGE_TO_RETENTION,
    STAGE_WASTE_PASSIVE_BACKFLOW_BARRIER_TO_CARTRIDGE,
    STAGE_WASTE_PUMP_TO_PASSIVE_BACKFLOW_BARRIER,
    STAGE_WASTE_REGION_TO_PUMP_INLET,
    SYSTEM_FRESH,
    SYSTEM_WASTE,
    TOPOLOGY_STATUS,
    FluidRoutingClosureError,
    build_fluid_routing_closure_architecture,
)
from masck_one.fresh_pump_packaging import build_fresh_pump_packaging_architecture
from masck_one.interface_attachment import build_interface_attachment_architecture
from masck_one.model import build_model
from masck_one.structural_frame import build_structural_frame_topology
from masck_one.water_reservoir import build_water_reservoir_architecture
from masck_one.waste_acquisition import PHASE_MIXED_WASTE, build_waste_acquisition_architecture
from masck_one.waste_cartridge import build_waste_cartridge_architecture
from masck_one.waste_pump_packaging import build_waste_pump_packaging_architecture


@pytest.fixture(scope="module")
def built():
    model = build_model()
    boundaries = build_verified_interface_boundary_topology(
        model.authority,
        model.facial_surface,
        model.coverage_mesh,
        model.compliant_interface_topology,
    )
    attachment = build_interface_attachment_architecture(model.authority, boundaries)
    frame = build_structural_frame_topology(model.authority, attachment)
    water = build_water_reservoir_architecture(model.authority)
    cleanser = build_cleanser_storage_architecture(model.authority)
    fresh_pump = build_fresh_pump_packaging_architecture(
        model.authority,
        water,
        cleanser,
        frame,
    )
    manifold = build_distribution_manifold_architecture(
        model.authority,
        fresh_pump,
        water,
        cleanser,
        frame,
    )
    distribution = build_distribution_geometry_architecture(
        model.authority,
        manifold,
        fresh_pump,
        water,
        cleanser,
        frame,
        model.coverage_mesh,
        model.protected_volumes,
    )
    acquisition = build_waste_acquisition_architecture(model.authority, distribution)
    waste_pump = build_waste_pump_packaging_architecture(
        model.authority,
        acquisition,
        distribution,
        frame,
    )
    cartridge = build_waste_cartridge_architecture(
        model.authority,
        waste_pump,
        acquisition,
        distribution,
        frame,
    )
    routing = build_fluid_routing_closure_architecture(
        model.authority,
        water,
        cleanser,
        fresh_pump,
        manifold,
        distribution,
        model.coverage_mesh,
        model.protected_volumes,
        acquisition,
        waste_pump,
        cartridge,
        frame,
    )
    return (
        model,
        frame,
        water,
        cleanser,
        fresh_pump,
        manifold,
        distribution,
        acquisition,
        waste_pump,
        cartridge,
        routing,
    )


def _validate_current(built, routing):
    (
        model,
        frame,
        water,
        cleanser,
        fresh_pump,
        manifold,
        distribution,
        acquisition,
        waste_pump,
        cartridge,
        _,
    ) = built
    routing.validate_current_sources(
        authority=model.authority,
        water=water,
        cleanser=cleanser,
        fresh_pump=fresh_pump,
        manifold=manifold,
        distribution=distribution,
        coverage=model.coverage_mesh,
        protected=model.protected_volumes,
        acquisition=acquisition,
        waste_pump=waste_pump,
        cartridge=cartridge,
        frame=frame,
    )


def test_complete_operational_route_ledger_has_63_unique_segments(built):
    *_, routing = built
    assert len(routing.segments) == 63
    assert len({item.segment_id for item in routing.segments}) == 63
    assert sum(item.system == SYSTEM_FRESH for item in routing.segments) == 54
    assert sum(item.system == SYSTEM_WASTE for item in routing.segments) == 9


def test_stage_ledger_matches_controlled_complete_topology(built):
    *_, routing = built
    expected = {
        STAGE_FRESH_SOURCE_TO_PUMP: 2,
        STAGE_FRESH_PUMP_TO_MANIFOLD: 2,
        STAGE_FRESH_MANIFOLD_BRANCH: 2,
        STAGE_FRESH_BRANCH_TO_OUTLET: 24,
        STAGE_FRESH_OUTLET_TO_GROOVE: 24,
        STAGE_WASTE_REGION_TO_PUMP_INLET: 5,
        STAGE_WASTE_ACQUISITION_TO_PUMP: 1,
        STAGE_WASTE_PUMP_TO_PASSIVE_BACKFLOW_BARRIER: 1,
        STAGE_WASTE_PASSIVE_BACKFLOW_BARRIER_TO_CARTRIDGE: 1,
        STAGE_WASTE_CARTRIDGE_TO_RETENTION: 1,
    }
    actual = {
        stage: sum(item.stage == stage for item in routing.segments)
        for stage in expected
    }
    assert actual == expected


def test_fresh_and_waste_phase_semantics_never_cross(built):
    *_, routing = built
    for item in routing.segments:
        if item.system == SYSTEM_FRESH:
            assert item.phase_identity in {"FRESH_WATER", "CLEANSER"}
        else:
            assert item.phase_identity == PHASE_MIXED_WASTE


def test_every_segment_confirms_digital_continuity_but_blocks_quantitative_geometry(built):
    *_, routing = built
    for item in routing.segments:
        assert item.topology_status == TOPOLOGY_STATUS
        assert item.bend_radius_status == BEND_RADIUS_STATUS
        assert item.dead_volume_status == DEAD_VOLUME_STATUS
        assert item.service_clearance_status == SERVICE_CLEARANCE_STATUS
        assert item.centerline_length_mm is None
        assert item.inner_diameter_mm is None
        assert item.minimum_bend_radius_spec_mm is None
        assert item.realized_minimum_bend_radius_mm is None
        assert item.dead_volume_mL is None
        assert item.service_clearance_mm is None


def test_route_level_bend_radius_dead_volume_and_clearance_cannot_be_invented(built):
    *_, routing = built
    segment = routing.segments[0]
    for changes in (
        {"centerline_length_mm": 12.0},
        {"inner_diameter_mm": 0.8},
        {"minimum_bend_radius_spec_mm": 4.0},
        {"realized_minimum_bend_radius_mm": 5.0},
        {"dead_volume_mL": 0.01},
        {"service_clearance_mm": 2.0},
    ):
        with pytest.raises(FluidRoutingClosureError, match="cannot invent route length"):
            replace(segment, **changes)


def test_quantitative_status_cannot_be_spoofed_to_pass(built):
    *_, routing = built
    segment = routing.segments[0]
    with pytest.raises(FluidRoutingClosureError, match="bend-radius status"):
        replace(segment, bend_radius_status="PASS")
    with pytest.raises(FluidRoutingClosureError, match="dead-volume status"):
        replace(segment, dead_volume_status="PASS")
    with pytest.raises(FluidRoutingClosureError, match="service-clearance status"):
        replace(segment, service_clearance_status="PASS")
    with pytest.raises(FluidRoutingClosureError, match="routing topology status"):
        replace(segment, topology_status="PHYSICALLY_VERIFIED")


def test_system_level_quantitative_totals_remain_blocked(built):
    *_, routing = built
    assert routing.total_route_dead_volume_mL is None
    assert routing.minimum_route_service_clearance_mm is None
    assert routing.quantitative_closure_status == QUANTITATIVE_CLOSURE_STATUS
    with pytest.raises(FluidRoutingClosureError, match="total route dead volume"):
        replace(routing, total_route_dead_volume_mL=0.25)
    with pytest.raises(FluidRoutingClosureError, match="minimum route service clearance"):
        replace(routing, minimum_route_service_clearance_mm=1.0)
    with pytest.raises(FluidRoutingClosureError, match="quantitative routing closure status"):
        replace(routing, quantitative_closure_status="PASS")


def test_initial_prime_is_carried_only_as_validation_gated_requirement(built):
    *_, routing = built
    assert routing.maximum_initial_prime_mL == 0.40
    assert routing.maximum_initial_prime_status == "VALIDATION_GATED"
    with pytest.raises(FluidRoutingClosureError, match="maximum initial prime status"):
        replace(routing, maximum_initial_prime_status="VERIFIED")


def test_missing_reordered_mutable_or_duplicated_segment_ledgers_fail_closed(built):
    *_, routing = built
    with pytest.raises(FluidRoutingClosureError, match="stale, incomplete, reordered"):
        shortened = replace(routing, segments=routing.segments[:-1])
        _validate_current(built, shortened)
    with pytest.raises(FluidRoutingClosureError, match="stale, incomplete, reordered"):
        reordered = replace(routing, segments=tuple(reversed(routing.segments)))
        _validate_current(built, reordered)
    with pytest.raises(FluidRoutingClosureError, match="immutable nonempty tuple"):
        replace(routing, segments=list(routing.segments))
    duplicated = routing.segments + (routing.segments[-1],)
    with pytest.raises(FluidRoutingClosureError, match="cannot repeat"):
        replace(routing, segments=duplicated)


def test_crossed_or_aliased_segment_interfaces_fail_closed(built):
    *_, routing = built
    first = routing.segments[0]
    crossed = replace(first, target_interface_id=routing.segments[1].target_interface_id)
    candidate = replace(routing, segments=(crossed,) + routing.segments[1:])
    with pytest.raises(FluidRoutingClosureError, match="stale, incomplete, reordered"):
        _validate_current(built, candidate)
    with pytest.raises(FluidRoutingClosureError, match="cannot alias"):
        replace(first, target_interface_id=first.source_interface_id)


def test_stale_upstream_hash_authority_revision_and_prime_requirement_fail_closed(built):
    *_, routing = built
    with pytest.raises(FluidRoutingClosureError, match="stale for current upstream architecture hashes"):
        _validate_current(built, replace(routing, source_waste_cartridge_sha256="a" * 64))
    with pytest.raises(FluidRoutingClosureError, match="stale for current authority revision"):
        _validate_current(built, replace(routing, source_authority_revision="STALE-REVISION"))
    with pytest.raises(FluidRoutingClosureError, match="initial-prime requirement is stale"):
        _validate_current(
            built,
            replace(routing, maximum_initial_prime_mL=routing.maximum_initial_prime_mL + 0.01),
        )


def test_builder_revalidates_stale_waste_dependency_chain(built):
    (
        model,
        frame,
        water,
        cleanser,
        fresh_pump,
        manifold,
        distribution,
        acquisition,
        waste_pump,
        cartridge,
        _,
    ) = built
    stale_cartridge = replace(cartridge, source_waste_pump_sha256="a" * 64)
    with pytest.raises(FluidRoutingClosureError, match="waste routing source chain is stale"):
        build_fluid_routing_closure_architecture(
            model.authority,
            water,
            cleanser,
            fresh_pump,
            manifold,
            distribution,
            model.coverage_mesh,
            model.protected_volumes,
            acquisition,
            waste_pump,
            stale_cartridge,
            frame,
        )


def test_builder_revalidates_stale_fresh_dependency_chain(built):
    (
        model,
        frame,
        water,
        cleanser,
        fresh_pump,
        manifold,
        distribution,
        acquisition,
        waste_pump,
        cartridge,
        _,
    ) = built
    stale_manifold = replace(manifold, source_pump_architecture_sha256="a" * 64)
    with pytest.raises(FluidRoutingClosureError, match="fresh-fluid routing source chain is stale"):
        build_fluid_routing_closure_architecture(
            model.authority,
            water,
            cleanser,
            fresh_pump,
            stale_manifold,
            distribution,
            model.coverage_mesh,
            model.protected_volumes,
            acquisition,
            waste_pump,
            cartridge,
            frame,
        )


def test_hostile_string_aliases_and_token_spoofing_fail_closed(built):
    class Alias(str):
        pass

    *_, routing = built
    with pytest.raises(FluidRoutingClosureError, match="canonical lowercase SHA-256"):
        replace(routing, source_manifold_sha256=Alias("a" * 64))
    with pytest.raises(FluidRoutingClosureError, match="routing segment system"):
        replace(routing.segments[0], system=Alias(SYSTEM_FRESH))
    with pytest.raises(FluidRoutingClosureError, match="routing topology status"):
        replace(routing.segments[0], topology_status=Alias(TOPOLOGY_STATUS))
    with pytest.raises(FluidRoutingClosureError, match="routing closure evidence status"):
        replace(routing, evidence_status=Alias(ARCHITECTURE_EVIDENCE_STATUS))


def test_nonfinite_boolean_and_huge_prime_values_fail_closed(built):
    *_, routing = built
    for value in (float("nan"), float("inf"), float("-inf"), True, 10**10000):
        with pytest.raises(FluidRoutingClosureError):
            replace(routing, maximum_initial_prime_mL=value)


def test_manifest_is_deterministic_and_revalidates_nested_corruption(built):
    (
        model,
        frame,
        water,
        cleanser,
        fresh_pump,
        manifold,
        distribution,
        acquisition,
        waste_pump,
        cartridge,
        routing,
    ) = built
    second = build_fluid_routing_closure_architecture(
        model.authority,
        water,
        cleanser,
        fresh_pump,
        manifold,
        distribution,
        model.coverage_mesh,
        model.protected_volumes,
        acquisition,
        waste_pump,
        cartridge,
        frame,
    )
    assert routing.manifest() == second.manifest()
    assert routing.architecture_sha256 == second.architecture_sha256
    object.__setattr__(second.segments[0], "dead_volume_status", "PASS")
    with pytest.raises(FluidRoutingClosureError, match="dead-volume status"):
        _ = second.architecture_sha256


def test_physical_evidence_promotion_is_rejected(built):
    *_, routing = built
    assert routing.physical_validation_eligible is False
    assert routing.evidence_status == ARCHITECTURE_EVIDENCE_STATUS
    with pytest.raises(FluidRoutingClosureError, match="not physical validation evidence"):
        replace(routing, physical_validation_eligible=True)
    with pytest.raises(FluidRoutingClosureError, match="routing closure evidence status"):
        replace(routing, evidence_status="PHYSICALLY_VERIFIED")