from __future__ import annotations

import json
from pathlib import Path
import subprocess

import cadquery as cq
import pytest

from masck_one.whole_product_collision_matrix import (
    BLOCKED,
    CATEGORY_RIGID,
    CATEGORY_ROUTE,
    CLEAR,
    INTERFERENCE,
    METHOD_PROTECTED,
    METHOD_ROUTE,
    OBSERVED_CANDIDATES,
    PROTECTED_CONFLICT,
    REVIEW,
    SOURCE_BLOBS,
    SOURCE_MAIN_SHA,
    TOUCHING,
    WholeProductCollisionMatrix,
    build_whole_product_collision_matrix,
    export_whole_product_collision_review,
)


@pytest.fixture(scope="module")
def matrix() -> WholeProductCollisionMatrix:
    return build_whole_product_collision_matrix()


def _git(*args: str) -> str:
    return subprocess.check_output(("git", *args), text=True).strip()


def test_matrix_binds_exact_released_main_and_source_blobs():
    _git("cat-file", "-e", f"{SOURCE_MAIN_SHA}^{{commit}}")
    assert subprocess.run(("git", "merge-base", "--is-ancestor", SOURCE_MAIN_SHA, "HEAD"), check=False).returncode == 0
    for path, expected_blob in SOURCE_BLOBS:
        assert _git("hash-object", path) == expected_blob


def test_matrix_has_complete_released_participant_set(matrix: WholeProductCollisionMatrix):
    rigid = tuple(item for item in matrix.participants if item.category == CATEGORY_RIGID)
    routes = tuple(item for item in matrix.participants if item.category == CATEGORY_ROUTE)
    assert tuple(item.participant_id for item in rigid) == (
        "rigid_shell", "actuator_envelope_1", "actuator_envelope_2", "actuator_envelope_3",
        "actuator_envelope_4", "water_reservoir_envelope", "waste_cartridge_envelope",
        "battery_reference_envelope",
    )
    assert len(routes) == 3
    assert all(item.participant_id.startswith("WASTE_ROUTE_SERVICE::") for item in routes)
    assert all(item.geometry.val().isValid() for item in matrix.participants)
    assert all(len(item.brep_sha256) == 64 for item in matrix.participants)


def test_every_released_rigid_pair_is_exactly_screened(matrix: WholeProductCollisionMatrix):
    rigid = tuple(item for item in matrix.participants if item.category == CATEGORY_RIGID)
    rows = tuple(item for item in matrix.checks if item.check_id.startswith("BREP::"))
    assert len(rows) == len(rigid) * (len(rigid) - 1) // 2
    assert all(item.status in {CLEAR, INTERFERENCE, TOUCHING} for item in rows)
    for item in rows:
        assert item.intersection_volume_mm3 is not None and item.minimum_distance_mm is not None
        if item.status == INTERFERENCE:
            assert item.intersection_volume_mm3 > 0.0
        if item.status == CLEAR:
            assert item.intersection_volume_mm3 == 0.0 and item.minimum_distance_mm > 0.0


def test_route_service_aabb_overlap_is_review_not_exact_product_interference(matrix: WholeProductCollisionMatrix):
    rigid = tuple(item for item in matrix.participants if item.category == CATEGORY_RIGID)
    routes = tuple(item for item in matrix.participants if item.category == CATEGORY_ROUTE)
    rows = tuple(item for item in matrix.checks if item.method == METHOD_ROUTE)
    assert len(rows) == len(routes) * len(rigid)
    assert all(item.status in {CLEAR, REVIEW} for item in rows)
    assert all("NARROW_PHASE_ROUTE_GEOMETRY_NOT_PRODUCT_INTERFERENCE_CLAIM" in item.evidence_status for item in rows)
    for item in rows:
        assert item.intersection_volume_mm3 is not None and item.minimum_distance_mm is not None
        if item.intersection_volume_mm3 > 0.0 or item.minimum_distance_mm == 0.0:
            assert item.status == REVIEW
        else:
            assert item.status == CLEAR


def test_protected_rows_distinguish_2p5d_hard_envelope_from_finite_brep_collision(matrix: WholeProductCollisionMatrix):
    rows = tuple(item for item in matrix.checks if item.method == METHOD_PROTECTED)
    assert len(rows) == len(matrix.participants) * 5
    assert all(item.right_id.startswith("PROTECTED:MASCK_ONE-PROTECTED-") for item in rows)
    assert all(item.status in {CLEAR, PROTECTED_CONFLICT, TOUCHING, REVIEW} for item in rows)
    assert all("NOT_REGISTERED_DYNAMIC_3D_ANATOMY" in item.evidence_status for item in rows)
    route_ids = {item.participant_id for item in matrix.participants if item.category == CATEGORY_ROUTE}
    for item in rows:
        if item.left_id in route_ids and (item.intersection_volume_mm3 or item.minimum_distance_mm == 0.0):
            assert item.status == REVIEW
        if item.status == PROTECTED_CONFLICT:
            assert item.left_id not in route_ids
            assert item.intersection_volume_mm3 is not None and item.intersection_volume_mm3 > 0.0
            assert "SOURCE_PROTECTED_Z_POLICY_REMAINS_UNBOUNDED" in item.evidence_status


def test_dynamic_user_protected_screen_retains_full_worn_pose_set(matrix: WholeProductCollisionMatrix):
    assert len(matrix.dynamic_protected_screens) == 5
    pose_counts = {item.pose_count for item in matrix.dynamic_protected_screens}
    assert len(pose_counts) == 1 and next(iter(pose_counts)) > 100
    for item in matrix.dynamic_protected_screens:
        xmin, xmax, ymin, ymax, zmin, zmax = item.bounds_mm
        assert xmin < xmax and ymin < ymax and zmin <= zmax
        assert "DISCRETE_WORN_POSE" in item.evidence_status
        assert "Z_EXTENT_UNBOUNDED" in item.evidence_status


def test_missing_mechanism_retention_harness_cartridge_hmi_and_hand_keepouts_fail_closed(matrix: WholeProductCollisionMatrix):
    blocked = tuple(item for item in matrix.checks if item.status == BLOCKED)
    assert len(blocked) == 8
    text = "\n".join(item.check_id for item in blocked)
    for required in (
        "RIGHT_RELEASE_OPERATIONAL_MOTION",
        "RIGHT_RELEASE_FACTORY_MOTION",
        "RETENTION_OCCIPITAL_AND_FIT_MOTION",
        "RETENTION_HAIR_PINCH_KEEP_OUTS",
        "HARNESS",
        "CARTRIDGE_SERVICE_MOTION",
        "USER_HAND_SERVICE_KEEP_OUT",
        "PHYSICAL_HMI",
    ):
        assert required in text
    unresolved = {item.interface_id: item for item in matrix.unresolved_interfaces}
    for required in (
        "RIGHT_RELEASE_OPERATIONAL_MOTION",
        "RETENTION_OCCIPITAL_AND_FIT_MOTION",
        "RETENTION_HAIR_PINCH_KEEP_OUTS",
        "HARNESS",
        "CARTRIDGE_SERVICE_MOTION",
        "USER_HAND_SERVICE_KEEP_OUT",
        "PHYSICAL_HMI",
    ):
        assert required in unresolved
    assert all(item.blocker for item in unresolved.values())


def test_candidate_heads_are_navigation_only_not_consumed_geometry(matrix: WholeProductCollisionMatrix):
    assert matrix.observed_candidates == OBSERVED_CANDIDATES
    manifest = matrix.manifest()
    assert all(item["geometry_consumed"] is False for item in manifest["observed_candidates"])
    assert {item["pr"] for item in manifest["observed_candidates"]} == {70, 71, 80, 83, 84, 85, 87, 88, 89}


def test_current_source_bound_matrix_counts_are_deterministic(matrix: WholeProductCollisionMatrix):
    # Exact for the released source graph bound above. Future accepted source movement
    # requires an explicit rebind and review rather than silently changing these truths.
    assert matrix.exact_interference_count == 1
    assert matrix.protected_conflict_count == 15
    assert matrix.review_required_count == 3
    assert matrix.blocked_count == 8
    assert len(matrix.checks) == 115


def test_matrix_manifest_is_deterministic_and_never_promotes_physical_validation(matrix: WholeProductCollisionMatrix):
    first, second = matrix.manifest(), matrix.manifest()
    assert first == second
    assert len(first["matrix_sha256"]) == 64 and first["matrix_sha256"] == matrix.matrix_sha256
    assert first["physical_validation_eligible"] is False
    assert "NOT_FIT_COMFORT_ANATOMICAL_SERVICE" in first["evidence_status"]
    assert first["exact_interference_count"] == 1
    assert first["protected_conflict_count"] == 15
    assert first["review_required_count"] == 3
    assert first["blocked_count"] == 8
    assert first["matrix_status"] == "DIGITAL_CONFLICT_PRESENT_RELEASE_BLOCKED"


def test_review_exports_round_trip_as_valid_reference_geometry(tmp_path: Path, matrix: WholeProductCollisionMatrix):
    paths = export_whole_product_collision_review(tmp_path, matrix)
    by_name = {path.name: path for path in paths}
    assert set(by_name) == {
        "whole_product_collision_rigid_package_reference.step",
        "whole_product_collision_waste_service_aabbs_reference.step",
        "whole_product_collision_protected_prisms_reference.step",
        "whole_product_collision_matrix_v1.json",
    }
    rigid = cq.importers.importStep(str(by_name["whole_product_collision_rigid_package_reference.step"])).val()
    routes = cq.importers.importStep(str(by_name["whole_product_collision_waste_service_aabbs_reference.step"])).val()
    protected = cq.importers.importStep(str(by_name["whole_product_collision_protected_prisms_reference.step"])).val()
    assert rigid.isValid() and len(rigid.Solids()) == 8
    assert routes.isValid() and len(routes.Solids()) == 3
    assert protected.isValid() and len(protected.Solids()) == 5
    manifest = json.loads(by_name["whole_product_collision_matrix_v1.json"].read_text(encoding="utf-8"))
    assert manifest["schema"] == "MASCK_ONE_WHOLE_PRODUCT_COLLISION_MATRIX_V1"
    assert manifest["matrix_sha256"] == matrix.matrix_sha256
    assert manifest["physical_validation_eligible"] is False
