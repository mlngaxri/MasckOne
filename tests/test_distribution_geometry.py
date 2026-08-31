from dataclasses import replace
import math

import pytest

from masck_one.boundary_release import build_verified_interface_boundary_topology
from masck_one.cleanser_storage import build_cleanser_storage_architecture
from masck_one.distribution_geometry import (
    ACTIVE_REGION_IDS,
    ARCHITECTURE_EVIDENCE_STATUS,
    DIRECTION_RULE,
    GROOVE_EVIDENCE_STATUS,
    GROOVE_SURFACE_STATUS,
    OUTLET_EVIDENCE_STATUS,
    PLACEMENT_STATUS,
    DistributionGeometryError,
    _protected_clearance_mm,
    build_distribution_geometry_architecture,
)
from masck_one.distribution_manifold import build_distribution_manifold_architecture
from masck_one.fresh_pump_packaging import (
    FLUID_CLEANSER,
    FLUID_FRESH_WATER,
    build_fresh_pump_packaging_architecture,
)
from masck_one.interface_attachment import build_interface_attachment_architecture
from masck_one.model import build_model
from masck_one.spatial import Point2
from masck_one.structural_frame import build_structural_frame_topology
from masck_one.water_reservoir import build_water_reservoir_architecture


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
    pump = build_fresh_pump_packaging_architecture(
        model.authority,
        water,
        cleanser,
        frame,
    )
    manifold = build_distribution_manifold_architecture(
        model.authority,
        pump,
        water,
        cleanser,
        frame,
    )
    geometry = build_distribution_geometry_architecture(
        model.authority,
        manifold,
        pump,
        water,
        cleanser,
        frame,
        model.coverage_mesh,
        model.protected_volumes,
    )
    return model, water, cleanser, frame, pump, manifold, geometry


def _validate(built, geometry):
    model, water, cleanser, frame, pump, manifold, _ = built
    geometry.validate_current_sources(
        authority=model.authority,
        manifold=manifold,
        pump=pump,
        water=water,
        cleanser=cleanser,
        frame=frame,
        coverage=model.coverage_mesh,
        protected=model.protected_volumes,
    )


def test_all_manifold_outlets_receive_unique_active_target_placements(built):
    model, *_, manifold, geometry = built
    assert tuple(item.outlet_id for item in geometry.placements) == tuple(
        item.outlet_id for item in manifold.outlets
    )
    assert len(geometry.placements) == 24
    assert len({item.source_triangle_index for item in geometry.placements}) == 24
    assert geometry.eligible_candidate_count >= 24
    for placement in geometry.placements:
        triangle = model.coverage_mesh.triangles[placement.source_triangle_index]
        assert triangle.is_target
        assert placement.region_id in ACTIVE_REGION_IDS
        assert placement.region_id == triangle.region_id
        assert placement.center_xyz_mm == triangle.centroid.as_tuple()


def test_fluid_identity_and_each_active_region_are_preserved(built):
    *_, geometry = built
    assert tuple(item.fluid_identity for item in geometry.placements[:18]) == (
        FLUID_FRESH_WATER,
    ) * 18
    assert tuple(item.fluid_identity for item in geometry.placements[18:]) == (
        FLUID_CLEANSER,
    ) * 6
    for fluid in (FLUID_FRESH_WATER, FLUID_CLEANSER):
        assert {item.region_id for item in geometry.placements if item.fluid_identity == fluid} == set(
            ACTIVE_REGION_IDS
        )


def test_protected_margin_and_lateral_direction_rules_hold(built):
    *_, geometry = built
    assert math.isclose(geometry.required_clearance_mm, 0.6875, abs_tol=1e-12)
    for placement in geometry.placements:
        assert placement.protected_clearance_mm >= placement.required_clearance_mm
        assert placement.placement_status == PLACEMENT_STATUS
        assert placement.direction_rule == DIRECTION_RULE
        assert placement.evidence_status == OUTLET_EVIDENCE_STATUS
        assert math.isclose(
            math.sqrt(sum(value * value for value in placement.lateral_direction_xyz)),
            1.0,
            abs_tol=1e-12,
        )
        assert placement.lateral_direction_xyz[2] == 0.0


def test_off_axis_ellipse_clearance_uses_nearest_boundary_not_center_ray(built):
    model, *_, geometry = built
    for triangle_index in (10259, 10373):
        triangle = model.coverage_mesh.triangles[triangle_index]
        clearance = _protected_clearance_mm(
            Point2(triangle.centroid.x, triangle.centroid.y),
            model.protected_volumes,
        )
        assert clearance == pytest.approx(0.6704478550479708, abs=1e-12)
        assert clearance < geometry.required_clearance_mm


def test_grooves_bind_one_to_one_without_invented_dimensions(built):
    *_, geometry = built
    assert len(geometry.grooves) == len(geometry.placements)
    for placement, groove in zip(geometry.placements, geometry.grooves, strict=True):
        assert groove.outlet_id == placement.outlet_id
        assert groove.origin_xyz_mm == placement.center_xyz_mm
        assert groove.lateral_direction_xyz == placement.lateral_direction_xyz
        assert groove.width_mm is None
        assert groove.depth_mm is None
        assert groove.length_mm is None
        assert groove.surface_status == GROOVE_SURFACE_STATUS
        assert groove.evidence_status == GROOVE_EVIDENCE_STATUS


def test_invented_or_face_directed_geometry_fails_closed(built):
    *_, geometry = built
    placement = geometry.placements[0]
    groove = geometry.grooves[0]
    with pytest.raises(DistributionGeometryError, match="development XY plane"):
        replace(placement, lateral_direction_xyz=(0.0, 0.0, 1.0))
    with pytest.raises(DistributionGeometryError, match="violates protected-region"):
        replace(placement, protected_clearance_mm=0.1)
    with pytest.raises(DistributionGeometryError, match="cannot invent"):
        replace(groove, width_mm=0.4)


def test_duplicate_positions_and_broken_groove_binding_fail_closed(built):
    *_, geometry = built
    placements = list(geometry.placements)
    placements[1] = replace(
        placements[1],
        source_triangle_index=placements[0].source_triangle_index,
    )
    with pytest.raises(DistributionGeometryError, match="cannot share source triangles"):
        replace(geometry, placements=tuple(placements))
    grooves = list(geometry.grooves)
    grooves[0] = replace(grooves[0], origin_xyz_mm=(0.0, 0.0, 0.0))
    with pytest.raises(DistributionGeometryError, match="bind exactly"):
        replace(geometry, grooves=tuple(grooves))


def test_stale_manifold_coverage_and_protected_hashes_fail_closed(built):
    *_, geometry = built
    with pytest.raises(DistributionGeometryError, match="stale for current manifold"):
        _validate(built, replace(geometry, source_manifold_architecture_sha256="a" * 64))
    with pytest.raises(DistributionGeometryError, match="stale for current coverage"):
        _validate(built, replace(geometry, source_coverage_segmentation_sha256="a" * 64))
    with pytest.raises(DistributionGeometryError, match="stale for current protected"):
        _validate(built, replace(geometry, source_protected_volumes_sha256="a" * 64))


def test_mutated_position_margin_and_direction_are_rechecked_against_sources(built):
    *_, geometry = built
    placement = geometry.placements[0]
    placements = list(geometry.placements)
    placements[0] = replace(
        placement,
        center_xyz_mm=(placement.center_xyz_mm[0] + 1.0, *placement.center_xyz_mm[1:]),
    )
    grooves = list(geometry.grooves)
    grooves[0] = replace(grooves[0], origin_xyz_mm=placements[0].center_xyz_mm)
    with pytest.raises(DistributionGeometryError, match="stale for current target triangle"):
        _validate(built, replace(geometry, placements=tuple(placements), grooves=tuple(grooves)))

    placements = list(geometry.placements)
    placements[0] = replace(
        placement,
        protected_clearance_mm=placement.protected_clearance_mm + 1.0,
    )
    with pytest.raises(DistributionGeometryError, match="margin is stale"):
        _validate(built, replace(geometry, placements=tuple(placements)))

    x, y, _ = placement.lateral_direction_xyz
    placements = list(geometry.placements)
    placements[0] = replace(placement, lateral_direction_xyz=(-x, -y, 0.0))
    grooves = list(geometry.grooves)
    grooves[0] = replace(grooves[0], lateral_direction_xyz=(-x, -y, 0.0))
    with pytest.raises(DistributionGeometryError, match="no longer follows"):
        _validate(built, replace(geometry, placements=tuple(placements), grooves=tuple(grooves)))


def test_candidate_ledger_triangle_bounds_and_fluid_identity_fail_closed(built):
    *_, geometry = built
    with pytest.raises(DistributionGeometryError, match="candidate ledger is stale"):
        _validate(built, replace(geometry, eligible_candidate_count=geometry.eligible_candidate_count + 1))
    placements = list(geometry.placements)
    placements[0] = replace(placements[0], source_triangle_index=999_999)
    with pytest.raises(DistributionGeometryError, match="outside current coverage"):
        _validate(built, replace(geometry, placements=tuple(placements)))
    with pytest.raises(DistributionGeometryError, match="fluid identity is not controlled"):
        replace(geometry.placements[0], fluid_identity="WATER")


def test_status_promotions_hostile_strings_and_mutable_containers_fail_closed(built):
    *_, geometry = built
    placement = geometry.placements[0]
    groove = geometry.grooves[0]
    with pytest.raises(DistributionGeometryError, match="placement status"):
        replace(placement, placement_status="ANATOMICALLY_REGISTERED")
    with pytest.raises(DistributionGeometryError, match="direction rule"):
        replace(placement, direction_rule="DIRECT_FACE_JET_VALIDATED")
    with pytest.raises(DistributionGeometryError, match="groove surface status"):
        replace(groove, surface_status="REGISTERED_SURFACE_VALIDATED")
    with pytest.raises(DistributionGeometryError, match="evidence status"):
        replace(geometry, evidence_status="PHYSICALLY_VALIDATED")

    class LyingStr(str):
        pass

    with pytest.raises(DistributionGeometryError, match="outlet placement ID"):
        replace(placement, outlet_id=LyingStr(placement.outlet_id))
    with pytest.raises(DistributionGeometryError, match="source manifold"):
        replace(
            geometry,
            source_manifold_architecture_sha256=LyingStr("a" * 64),
        )
    with pytest.raises(DistributionGeometryError, match="immutable tuple"):
        replace(geometry, placements=list(geometry.placements))
    with pytest.raises(DistributionGeometryError, match="immutable tuple"):
        replace(geometry, grooves=list(geometry.grooves))


def test_manifest_is_deterministic_and_not_physical_evidence(built):
    model, water, cleanser, frame, pump, manifold, geometry = built
    second = build_distribution_geometry_architecture(
        model.authority,
        manifold,
        pump,
        water,
        cleanser,
        frame,
        model.coverage_mesh,
        model.protected_volumes,
    )
    assert geometry.manifest() == second.manifest()
    assert geometry.architecture_sha256 == second.architecture_sha256
    assert geometry.physical_validation_eligible is False
    assert geometry.evidence_status == ARCHITECTURE_EVIDENCE_STATUS
