from dataclasses import replace
import math

import pytest

from masck_one.realized_waste_backbone import (
    CROSS_SECTION_PROVENANCE,
    GEOMETRY_PROVENANCE,
    HYDRAULIC_STATE,
    PHYSICAL_STATE,
    SERVICE_STATE,
    RealizedWasteBackboneError,
    build_cell4_waste_backbone,
)
from masck_one.realized_waste_backbone_release import (
    AUTHORED_AGAINST_MAIN_SHA,
    build_current_waste_routing_sources,
)
from masck_one.waste_acquisition import PHASE_MIXED_WASTE


@pytest.fixture(scope="module")
def sources():
    return build_current_waste_routing_sources()


@pytest.fixture(scope="module")
def backbone(sources):
    return build_cell4_waste_backbone(
        source_git_sha=AUTHORED_AGAINST_MAIN_SHA,
        source_waste_pump_architecture_sha256=sources.architecture.architecture_sha256,
        authority_revision=sources.architecture.source_authority_revision,
    )


def test_backbone_binds_segment_stage_phase_source_and_target_to_live_architecture(
    sources,
    backbone,
):
    actual = tuple(
        (
            route.segment_id,
            route.stage,
            route.fluid_identity,
            route.source_interface_id,
            route.target_interface_id,
        )
        for route in backbone.routes
    )
    expected = tuple(
        (
            route.route_id,
            route.stage,
            route.phase_semantics,
            route.source_interface_id,
            route.target_interface_id,
        )
        for route in sources.architecture.routes
    )
    assert actual == expected
    assert backbone.source_waste_pump_architecture_sha256 == sources.architecture.architecture_sha256
    assert backbone.authority_revision == sources.architecture.source_authority_revision


def test_backbone_preserves_mixed_waste_and_passive_barrier_boundary(sources, backbone):
    assert all(route.fluid_identity == PHASE_MIXED_WASTE for route in backbone.routes)
    assert backbone.routes[1].target_interface_id == sources.architecture.barrier.barrier_id
    assert backbone.routes[2].source_interface_id == sources.architecture.barrier.target_interface_id
    assert backbone.routes[1].target_interface_id != backbone.routes[2].source_interface_id


def test_world_centerlines_are_continuous_and_have_exact_bounds_and_arc_radii(backbone):
    for route in backbone.routes:
        route.validate()
        assert route.centerline_length_mm > 0.0
        bounds_min, bounds_max = route.bounds_xyz_mm
        assert all(lo <= hi for lo, hi in zip(bounds_min, bounds_max))
    assert backbone.routes[0].realized_min_bend_radius_mm is None
    assert backbone.routes[1].realized_min_bend_radius_mm == 8.0
    assert backbone.routes[2].realized_min_bend_radius_mm == 8.0


def test_geometric_dead_volume_is_derived_from_length_and_internal_area(backbone):
    expected = math.fsum(
        route.centerline_length_mm * route.internal_area_mm2 / 1000.0
        for route in backbone.routes
    )
    assert backbone.total_geometric_dead_volume_mL == pytest.approx(expected, abs=1e-12)
    assert backbone.total_geometric_dead_volume_mL == pytest.approx(
        0.29068329701259293,
        abs=1e-12,
    )


def test_provisional_service_envelope_stays_outside_authority_mouth_hard_envelope(
    sources,
    backbone,
):
    authority = sources.authority
    mouth_x, mouth_y = authority.pair("geometry", "mouth", "center_mm")
    mouth_w, mouth_h = authority.pair("geometry", "mouth", "visual_aperture_wh_mm")
    clearance = authority.number(
        "geometry",
        "mouth",
        "rigid_dynamic_keepout_clearance_mm",
    )
    hard_left_x = mouth_x - mouth_w / 2.0 - clearance
    hard_y_min = mouth_y - mouth_h / 2.0 - clearance
    hard_y_max = mouth_y + mouth_h / 2.0 + clearance

    for route in backbone.routes:
        for primitive in route.centerline:
            bounds_min, bounds_max = primitive.bounds_xyz_mm
            overlaps_mouth_y = not (
                bounds_max[1] < hard_y_min or bounds_min[1] > hard_y_max
            )
            if overlaps_mouth_y:
                assert bounds_max[0] + route.service_envelope_radius_mm <= hard_left_x


def test_provenance_and_evidence_firewall_remain_explicit(backbone):
    for route in backbone.routes:
        assert route.segment_id == route.route_id
        assert route.geometry_provenance == GEOMETRY_PROVENANCE
        assert route.cross_section_provenance == CROSS_SECTION_PROVENANCE
        assert route.minimum_bend_requirement_mm is None
        assert route.bend_margin_mm is None
        assert route.realized_service_clearance_mm is None
        assert route.service_margin_mm is None
        assert route.service_state == SERVICE_STATE
        assert route.physical_performance_state == PHYSICAL_STATE
        assert route.hydraulic_state == HYDRAULIC_STATE


def test_backbone_manifest_is_deterministic(sources):
    kwargs = {
        "source_git_sha": AUTHORED_AGAINST_MAIN_SHA,
        "source_waste_pump_architecture_sha256": sources.architecture.architecture_sha256,
        "authority_revision": sources.architecture.source_authority_revision,
    }
    first = build_cell4_waste_backbone(**kwargs)
    second = build_cell4_waste_backbone(**kwargs)
    assert first.manifest_sha256 == second.manifest_sha256


def test_stale_or_noncanonical_source_sha_is_rejected(sources):
    with pytest.raises(RealizedWasteBackboneError, match="Git SHA"):
        build_cell4_waste_backbone(
            source_git_sha="not-a-sha",
            source_waste_pump_architecture_sha256=sources.architecture.architecture_sha256,
            authority_revision=sources.architecture.source_authority_revision,
        )


def test_noncanonical_architecture_digest_is_rejected():
    with pytest.raises(RealizedWasteBackboneError, match="architecture digest"):
        build_cell4_waste_backbone(
            source_git_sha=AUTHORED_AGAINST_MAIN_SHA,
            source_waste_pump_architecture_sha256="not-a-digest",
        )


def test_controlled_stage_cannot_be_reassigned_to_another_segment(backbone):
    altered_route = replace(backbone.routes[1], stage=backbone.routes[0].stage)
    altered = replace(
        backbone,
        routes=(backbone.routes[0], altered_route, backbone.routes[2]),
    )
    with pytest.raises(RealizedWasteBackboneError, match="passive-backflow topology"):
        altered.validate()


def test_physical_performance_cannot_be_promoted_by_mutation(backbone):
    altered = replace(backbone.routes[0], physical_performance_state="VERIFIED")
    with pytest.raises(RealizedWasteBackboneError, match="cannot promote"):
        altered.validate()


def test_mixed_waste_identity_cannot_be_downgraded(backbone):
    altered = replace(backbone.routes[0], fluid_identity="FRESH_WATER")
    with pytest.raises(RealizedWasteBackboneError, match="mixed-waste"):
        altered.validate()


def test_supplier_bend_requirement_cannot_be_invented(backbone):
    altered = replace(backbone.routes[1], minimum_bend_requirement_mm=5.0)
    with pytest.raises(RealizedWasteBackboneError, match="cannot be invented"):
        altered.validate()
