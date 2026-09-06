from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path

import cadquery as cq
import pytest

from masck_one.whole_product_collision_matrix import (
    BLOCKED,
    CATEGORY_ROUTE,
    CLEAR,
    FINITE_ROLE_BY_ID,
    MATERIAL_INTERFERENCE,
    REFERENCE_OVERLAP,
    REVIEW,
    ROLE_BENCHMARK,
    ROLE_MATERIAL,
    ROLE_PACKAGE,
    ROW_BLOCKED,
    ROW_CONSERVATIVE,
    ROW_EXACT,
    ROW_PROTECTED,
    SOURCE_BLOBS,
    SOURCE_MAIN_SHA,
    WholeProductCollisionMatrix,
    WholeProductCollisionMatrixError,
    build_whole_product_collision_matrix,
    export_whole_product_collision_review,
)


@pytest.fixture(scope="module")
def matrix() -> WholeProductCollisionMatrix:
    return build_whole_product_collision_matrix()


def test_matrix_binds_current_main_and_all_collision_relevant_sources(matrix: WholeProductCollisionMatrix):
    assert SOURCE_MAIN_SHA == "afe29ff78419b6625dca5594974b6351f6f80e1b"
    assert matrix.binding.source_main_sha == SOURCE_MAIN_SHA
    assert len(SOURCE_BLOBS) == 11
    for path, expected_blob in SOURCE_BLOBS:
        payload = Path(path).read_bytes()
        actual = hashlib.sha1(f"blob {len(payload)}\0".encode("ascii") + payload).hexdigest()
        assert actual == expected_blob


def test_finite_role_boundary_is_exact_and_package_envelopes_are_not_material(matrix: WholeProductCollisionMatrix):
    finite = tuple(item for item in matrix.participants if item.geometry_role != CATEGORY_ROUTE)
    assert {item.participant_id: item.geometry_role for item in finite} == FINITE_ROLE_BY_ID
    assert FINITE_ROLE_BY_ID["rigid_shell"] == ROLE_MATERIAL
    assert FINITE_ROLE_BY_ID["waste_cartridge_envelope"] == ROLE_PACKAGE
    assert FINITE_ROLE_BY_ID["water_reservoir_envelope"] == ROLE_PACKAGE
    assert all(FINITE_ROLE_BY_ID[f"actuator_envelope_{index}"] == ROLE_PACKAGE for index in range(1, 5))
    assert FINITE_ROLE_BY_ID["battery_reference_envelope"] == ROLE_BENCHMARK


def test_exact_rows_cover_every_finite_pair_and_do_not_promote_reference_overlap(matrix: WholeProductCollisionMatrix):
    finite = tuple(item for item in matrix.participants if item.geometry_role != CATEGORY_ROUTE)
    rows = tuple(item for item in matrix.checks if item.row_class == ROW_EXACT)
    assert len(finite) == 8
    assert len(rows) == len(finite) * (len(finite) - 1) // 2 == 28
    assert all(item.status in {CLEAR, MATERIAL_INTERFERENCE, REFERENCE_OVERLAP, "TOUCHING_REVIEW_REQUIRED"} for item in rows)

    overlaps = tuple(item for item in rows if item.intersection_volume_mm3 and item.intersection_volume_mm3 > 0.0)
    assert len(overlaps) == 1
    overlap = overlaps[0]
    assert overlap.check_id == "BREP::rigid_shell::waste_cartridge_envelope"
    assert overlap.status == REFERENCE_OVERLAP
    assert overlap.intersection_volume_mm3 is not None and overlap.intersection_volume_mm3 > 900.0
    assert matrix.material_interference_count == 0
    assert matrix.reference_overlap_count == 1
    assert matrix.exact_overlap_count == 1


def test_conservative_route_rows_remain_broad_phase_only(matrix: WholeProductCollisionMatrix):
    finite = tuple(item for item in matrix.participants if item.geometry_role != CATEGORY_ROUTE)
    routes = tuple(item for item in matrix.participants if item.geometry_role == CATEGORY_ROUTE)
    rows = tuple(item for item in matrix.checks if item.row_class == ROW_CONSERVATIVE)
    assert len(routes) == 3
    assert len(rows) == len(routes) * len(finite) == 24
    assert all(item.status in {CLEAR, REVIEW} for item in rows)
    assert all("NARROW_PHASE_ROUTE_GEOMETRY_NOT_PRODUCT_INTERFERENCE_CLAIM" in item.evidence_status for item in rows)


def test_protected_rows_cover_every_participant_and_preserve_2p5d_semantics(matrix: WholeProductCollisionMatrix):
    rows = tuple(item for item in matrix.checks if item.row_class == ROW_PROTECTED)
    assert len(rows) == len(matrix.participants) * 5 == 55
    assert all(item.right_id.startswith("PROTECTED:MASCK_ONE-PROTECTED-") for item in rows)
    assert all("NOT_REGISTERED_DYNAMIC_3D_ANATOMY" in item.evidence_status for item in rows)
    assert matrix.protected_conflict_count == 15


def test_dynamic_protected_screen_retains_complete_worn_pose_set(matrix: WholeProductCollisionMatrix):
    assert len(matrix.dynamic_protected_screens) == 5
    pose_counts = {item.pose_count for item in matrix.dynamic_protected_screens}
    assert len(pose_counts) == 1 and next(iter(pose_counts)) > 100
    for item in matrix.dynamic_protected_screens:
        xmin, xmax, ymin, ymax, zmin, zmax = item.bounds_mm
        assert xmin < xmax and ymin < ymax and zmin <= zmax
        assert "DISCRETE_WORN_POSE" in item.evidence_status
        assert "Z_EXTENT_UNBOUNDED" in item.evidence_status


def test_successor_matrix_closes_cell5_completeness_omissions_without_inventing_geometry(matrix: WholeProductCollisionMatrix):
    blocked = tuple(item for item in matrix.checks if item.row_class == ROW_BLOCKED)
    assert len(blocked) == 13
    assert all(item.status == BLOCKED for item in blocked)
    blocked_ids = {item.left_id for item in blocked}
    required = {
        "RIGHT_RELEASE_OPERATIONAL_MOTION",
        "RIGHT_RELEASE_FACTORY_MOTION",
        "RETENTION_OCCIPITAL_AND_FIT_MOTION",
        "RETENTION_HAIR_PINCH_KEEP_OUTS",
        "HARNESS",
        "CARTRIDGE_SERVICE_MOTION",
        "USER_HAND_SERVICE_KEEP_OUT",
        "PHYSICAL_HMI",
        "ACTUATOR_OPERATIONAL_SWEEP_AND_FINAL_STOPS",
        "ACTUATOR_CARRIER_REACTION_AND_SERVICE_GEOMETRY",
        "FRESH_FLUID_ROUTE_CENTERLINES_AND_CROSS_SECTIONS",
        "FRESH_MANIFOLD_BODY_BRANCH_AND_JOIN_GEOMETRY",
        "DISTRIBUTION_GROOVE_AND_OUTLET_PATH_GEOMETRY",
    }
    assert blocked_ids == required
    unresolved_ids = {item.interface_id for item in matrix.unresolved_interfaces}
    assert unresolved_ids == required
    assert all(item.intersection_volume_mm3 is None and item.minimum_distance_mm is None for item in blocked)


def test_row_classes_are_complete_and_deterministic(matrix: WholeProductCollisionMatrix):
    assert matrix.row_class_counts == {
        ROW_EXACT: 28,
        ROW_PROTECTED: 55,
        ROW_CONSERVATIVE: 24,
        ROW_BLOCKED: 13,
    }
    assert len(matrix.checks) == 120
    assert matrix.exact_overlap_count == 1
    assert matrix.material_interference_count == 0
    assert matrix.reference_overlap_count == 1
    assert matrix.protected_conflict_count == 15
    assert matrix.review_required_count == 4
    assert matrix.blocked_count == 13
    assert matrix.matrix_status == "DIGITAL_CONFLICT_PRESENT_RELEASE_BLOCKED"


def test_manifest_is_deterministic_and_never_promotes_physical_validation(matrix: WholeProductCollisionMatrix):
    first = matrix.manifest()
    second = matrix.manifest()
    assert first == second
    assert first["schema"] == "MASCK_ONE_WHOLE_PRODUCT_COLLISION_MATRIX_V2"
    assert first["row_count"] == 120
    assert first["physical_validation_eligible"] is False
    assert "NOT_FIT_COMFORT_ANATOMICAL_SERVICE" in first["evidence_status"]
    assert len(first["matrix_sha256"]) == 64
    assert first["matrix_sha256"] == matrix.matrix_sha256


def test_role_spoofing_fails_closed(matrix: WholeProductCollisionMatrix):
    finite = list(matrix.participants)
    shell_index = next(index for index, item in enumerate(finite) if item.participant_id == "rigid_shell")
    finite[shell_index] = replace(finite[shell_index], geometry_role=ROLE_PACKAGE)
    hostile = replace(matrix, participants=tuple(finite))
    with pytest.raises(WholeProductCollisionMatrixError, match="role map moved or was spoofed"):
        hostile.validate()


def test_nonfinite_geometric_metric_is_rejected(matrix: WholeProductCollisionMatrix):
    exact_index = next(index for index, item in enumerate(matrix.checks) if item.row_class == ROW_EXACT)
    with pytest.raises(WholeProductCollisionMatrixError, match="finite and nonnegative"):
        replace(matrix.checks[exact_index], minimum_distance_mm=float("nan"))


def test_review_exports_round_trip_as_valid_reference_geometry(tmp_path: Path, matrix: WholeProductCollisionMatrix):
    paths = export_whole_product_collision_review(tmp_path, matrix)
    by_name = {path.name: path for path in paths}
    assert set(by_name) == {
        "whole_product_collision_finite_reference.step",
        "whole_product_collision_waste_service_aabbs_reference.step",
        "whole_product_collision_protected_prisms_reference.step",
        "whole_product_collision_matrix_v2.json",
    }

    finite = cq.importers.importStep(str(by_name["whole_product_collision_finite_reference.step"])).val()
    routes = cq.importers.importStep(str(by_name["whole_product_collision_waste_service_aabbs_reference.step"])).val()
    protected = cq.importers.importStep(str(by_name["whole_product_collision_protected_prisms_reference.step"])).val()
    assert finite.isValid() and len(finite.Solids()) == 8
    assert routes.isValid() and len(routes.Solids()) == 3
    assert protected.isValid() and len(protected.Solids()) == 5

    manifest = json.loads(by_name["whole_product_collision_matrix_v2.json"].read_text(encoding="utf-8"))
    assert manifest["matrix_sha256"] == matrix.matrix_sha256
    assert manifest["row_class_counts"] == {
        ROW_EXACT: 28,
        ROW_PROTECTED: 55,
        ROW_CONSERVATIVE: 24,
        ROW_BLOCKED: 13,
    }
