from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

import masck_one.whole_product_collision_release as release_module
from masck_one.whole_product_collision_matrix import (
    ROW_BLOCKED,
    ROW_CONSERVATIVE,
    ROW_EXACT,
    ROW_PROTECTED,
    WholeProductCollisionMatrixError,
)
from masck_one.whole_product_collision_release import (
    ADDITIONAL_BLOCKERS,
    PRODUCER_BLOBS,
    SCHEMA,
    build_current_main_collision_release,
)


@pytest.fixture(scope="module")
def release():
    return build_current_main_collision_release()


def test_release_binds_full_current_main_collision_producer_graph(release):
    assert len(PRODUCER_BLOBS) == 27
    assert release.producer_blobs == PRODUCER_BLOBS
    assert release.source_main_sha == "afe29ff78419b6625dca5594974b6351f6f80e1b"
    assert release.world_frame_id == "MASCK_ONE_AUTHORITY_WORLD_MM"
    for path, expected_blob in PRODUCER_BLOBS:
        payload = Path(path).read_bytes()
        actual = hashlib.sha1(f"blob {len(payload)}\0".encode("ascii") + payload).hexdigest()
        assert actual == expected_blob


def test_release_successor_has_no_silent_current_main_package_omissions(release):
    expected = {item[0] for item in ADDITIONAL_BLOCKERS}
    assert len(expected) == 12
    present = {item.interface_id for item in release.matrix.unresolved_interfaces}
    assert expected.issubset(present)
    assert {
        "STRUCTURAL_FRAME_MATERIAL_AND_SHELL_JOIN_GEOMETRY",
        "NASAL_INTERFACE_FINAL_MATERIAL_ATTACHMENT_AND_SERVICE_GEOMETRY",
        "WATER_RESERVOIR_REALIZED_BODY_PORT_SEAL_AND_SERVICE_GEOMETRY",
        "CLEANSER_STORAGE_BODY_PORT_AND_SERVICE_GEOMETRY",
        "FRESH_WATER_PUMP_PACKAGE_PLACEMENT_AND_SERVICE_GEOMETRY",
        "CLEANSER_PUMP_PACKAGE_PLACEMENT_AND_SERVICE_GEOMETRY",
        "WASTE_PUMP_PACKAGE_PLACEMENT_AND_SERVICE_GEOMETRY",
        "PASSIVE_BACKFLOW_PACKAGE_PLACEMENT_AND_SERVICE_GEOMETRY",
        "WASTE_CARTRIDGE_REALIZED_BODY_CAVITY_SEAL_AND_RETENTION_GEOMETRY",
        "BATTERY_REALIZED_PACKAGE_RETENTION_AND_SERVICE_GEOMETRY",
        "PCB_CHARGING_DRY_BAY_AND_CONNECTOR_GEOMETRY",
        "WARM_THERMAL_HARDWARE_AND_CLEARANCE_GEOMETRY",
    } == expected


def test_release_row_classes_preserve_measured_core_and_expand_blocked_truth(release):
    assert release.matrix.row_class_counts == {
        ROW_EXACT: 28,
        ROW_PROTECTED: 55,
        ROW_CONSERVATIVE: 24,
        ROW_BLOCKED: 25,
    }
    assert len(release.matrix.checks) == 132
    assert release.matrix.blocked_count == 25
    assert release.matrix.material_interference_count == 0
    assert release.matrix.reference_overlap_count == 1
    assert release.matrix.protected_conflict_count == 15
    assert release.matrix.matrix_status == "DIGITAL_CONFLICT_PRESENT_RELEASE_BLOCKED"


def test_added_rows_are_explicit_blocked_unknowns_without_fabricated_metrics(release):
    extra_ids = {item[0] for item in ADDITIONAL_BLOCKERS}
    rows = tuple(
        item for item in release.matrix.checks
        if item.row_class == ROW_BLOCKED and item.left_id in extra_ids
    )
    assert len(rows) == 12
    for row in rows:
        assert row.status == "BLOCKED_UNRESOLVED_GEOMETRY"
        assert row.method == "BLOCKED_NO_RELEASED_GEOMETRY"
        assert row.intersection_volume_mm3 is None
        assert row.minimum_distance_mm is None


def test_release_manifest_is_deterministic_and_keeps_physical_firewall(release):
    first = release.manifest()
    second = release.manifest()
    assert first == second
    assert first["schema"] == SCHEMA
    assert first["row_count"] == 132
    assert first["blocked_count"] == 25
    assert first["physical_validation_eligible"] is False
    assert first["release_sha256"] == release.release_sha256
    assert len(first["producer_blobs"]) == 27
    json.dumps(first, sort_keys=True, allow_nan=False)


def test_producer_binding_tamper_fails_closed(monkeypatch, release):
    monkeypatch.setattr(release_module, "PRODUCER_BLOBS", PRODUCER_BLOBS[:-1])
    with pytest.raises(WholeProductCollisionMatrixError, match="producer binding was altered"):
        release.validate()
