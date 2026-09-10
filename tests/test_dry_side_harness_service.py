from __future__ import annotations

import pytest

from masck_one.dry_side_harness_service import (
    CLIP_CENTERS_WORLD_MM,
    DRY_BAY_BOUNDS_WORLD_MM,
    PCB_HANDOFF_DATUM_WORLD_MM,
    ROUTE_POINTS_WORLD_MM,
    SOURCE_MAIN_SHA,
    DrySideHarnessError,
    DrySideHarnessService,
    build_dry_side_harness_service,
)

EXPECTED_RELEASE_SHA = "ac59fcd59f50b019cb972bfc526c2daea784bd17"


def test_harness_route_is_current_release_bound_and_one_valid_solid() -> None:
    harness = build_dry_side_harness_service()
    assert SOURCE_MAIN_SHA == EXPECTED_RELEASE_SHA
    solid = harness.route_envelope.val()
    assert solid.isValid()
    assert len(solid.Solids()) == 1
    assert solid.Volume() > 0.0


def test_harness_route_stays_inside_dry_bay_and_has_both_supports() -> None:
    harness = build_dry_side_harness_service()
    xmin, xmax, ymin, ymax, zmin, zmax = DRY_BAY_BOUNDS_WORLD_MM
    bb = harness.route_envelope.val().BoundingBox()
    assert bb.xmin >= xmin
    assert bb.xmax <= xmax
    assert bb.ymin >= ymin
    assert bb.ymax <= ymax
    assert bb.zmin >= zmin
    assert bb.zmax <= zmax
    assert len(harness.clip_reservations) == len(CLIP_CENTERS_WORLD_MM) == 2
    for clip in harness.clip_reservations:
        assert harness.route_envelope.val().intersect(clip.val()).Volume() > 0.0


def test_harness_manifest_preserves_service_and_evidence_firewalls() -> None:
    manifest = build_dry_side_harness_service().manifest()
    assert manifest["route_points_world_mm"] == [list(point) for point in ROUTE_POINTS_WORLD_MM]
    assert manifest["pcb_handoff_datum_world_mm"] == list(PCB_HANDOFF_DATUM_WORLD_MM)
    assert manifest["route_path_length_mm"] >= manifest["service_loop_extra_path_mm"]
    assert manifest["connector_selected"] is False
    assert manifest["conductor_selected"] is False
    assert manifest["electrical_ratings_selected"] is False
    assert manifest["ingress_validated"] is False
    assert manifest["emc_validated"] is False
    assert manifest["bend_life_validated"] is False
    assert manifest["physical_service_validated"] is False


def test_hostile_disconnected_route_is_rejected() -> None:
    valid = build_dry_side_harness_service()
    moved_points = (ROUTE_POINTS_WORLD_MM[0],) + ROUTE_POINTS_WORLD_MM[2:]
    hostile = DrySideHarnessService(
        route_envelope=valid.route_envelope,
        clip_reservations=valid.clip_reservations,
        route_points_world_mm=moved_points,
    )
    with pytest.raises(DrySideHarnessError):
        hostile.validate()


def test_hostile_route_escaping_dry_bay_is_rejected() -> None:
    valid = build_dry_side_harness_service()
    escaped = valid.route_envelope.translate((20.0, 0.0, 0.0))
    hostile = DrySideHarnessService(
        route_envelope=escaped,
        clip_reservations=valid.clip_reservations,
        route_points_world_mm=valid.route_points_world_mm,
    )
    with pytest.raises(DrySideHarnessError, match="escapes current dry-bay"):
        hostile.validate()


def test_hostile_support_detached_inside_dry_bay_is_rejected_for_non_engagement() -> None:
    valid = build_dry_side_harness_service()
    detached = valid.clip_reservations[0].translate((-30.0, 0.0, 0.0))
    detached_bb = detached.val().BoundingBox()
    xmin, xmax, ymin, ymax, zmin, zmax = DRY_BAY_BOUNDS_WORLD_MM
    assert detached_bb.xmin >= xmin and detached_bb.xmax <= xmax
    assert detached_bb.ymin >= ymin and detached_bb.ymax <= ymax
    assert detached_bb.zmin >= zmin and detached_bb.zmax <= zmax
    assert valid.route_envelope.val().intersect(detached.val()).Volume() <= 1e-9
    hostile = DrySideHarnessService(
        route_envelope=valid.route_envelope,
        clip_reservations=(detached, valid.clip_reservations[1]),
        route_points_world_mm=valid.route_points_world_mm,
    )
    with pytest.raises(
        DrySideHarnessError,
        match="harness support reservation must engage the route envelope",
    ):
        hostile.validate()
