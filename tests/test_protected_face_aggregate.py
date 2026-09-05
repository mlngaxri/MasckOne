from __future__ import annotations

import json
import subprocess

import pytest

from masck_one.model import build_model
from masck_one.protected_face_aggregate import (
    AUTHORITY_REVISION,
    DIRECTION_BLOCKED,
    DIGITAL_ONLY,
    FLUID_CLEAR,
    FLUID_CONFLICT,
    MOVING_BLOCKED,
    SOURCE_BLOBS,
    SOURCE_MAIN_SHA,
    STATIC_CLEAR,
    STATIC_CONFLICT,
    STATIC_TOUCHING,
    WORLD_FRAME_ID,
    build_protected_face_aggregate_precheck,
)


@pytest.fixture(scope="module")
def aggregate():
    return build_protected_face_aggregate_precheck(build_model())


def test_binds_exact_released_sources_and_five_authority_zones(aggregate):
    assert aggregate.binding.source_main_sha == SOURCE_MAIN_SHA
    assert aggregate.binding.authority_revision == AUTHORITY_REVISION
    assert aggregate.binding.world_frame_id == WORLD_FRAME_ID
    assert aggregate.binding.source_blobs == SOURCE_BLOBS
    assert aggregate.worn_pose_manifest["pose_count"] == 459
    assert aggregate.worn_pose_manifest["translation_radial_max_mm"] == 5.0
    assert aggregate.worn_pose_manifest["rotation_max_deg"] == 4.0
    zones = aggregate.protected_manifest["zones"]
    assert [zone["zone_id"] for zone in zones] == [
        "MASCK_ONE-PROTECTED-EYE-LEFT",
        "MASCK_ONE-PROTECTED-EYE-RIGHT",
        "MASCK_ONE-PROTECTED-MOUTH",
        "MASCK_ONE-PROTECTED-NOSTRIL-LEFT",
        "MASCK_ONE-PROTECTED-NOSTRIL-RIGHT",
    ]
    assert all(zone["z_policy"] == "UNBOUNDED_UNTIL_REGISTERED_ANATOMICAL_SURFACE" for zone in zones)
    assert all(zone["anatomical_validation_eligible"] is False for zone in zones)


def test_every_direct_source_blob_matches_current_checkout():
    for path, expected in SOURCE_BLOBS:
        actual = subprocess.run(
            ["git", "hash-object", path],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        assert actual == expected, path


def test_static_screen_is_complete_exact_and_digital_only(aggregate):
    zone_ids = {zone["zone_id"] for zone in aggregate.protected_manifest["zones"]}
    component_ids = {item.component_id for item in aggregate.static_checks}
    assert component_ids
    assert len(aggregate.static_checks) == len(component_ids) * len(zone_ids)
    assert {(item.component_id, item.zone_id) for item in aggregate.static_checks} == {
        (component_id, zone_id)
        for component_id in component_ids
        for zone_id in zone_ids
    }
    assert {item.status for item in aggregate.static_checks} <= {
        STATIC_CLEAR,
        STATIC_CONFLICT,
        STATIC_TOUCHING,
    }
    assert aggregate.static_conflict_count > 0
    shell_eye_rows = [
        item
        for item in aggregate.static_checks
        if item.component_id == "rigid_shell" and "EYE" in item.zone_id
    ]
    assert len(shell_eye_rows) == 2
    assert all(item.status == STATIC_CONFLICT for item in shell_eye_rows)
    assert all(len(item.component_brep_sha256) == 64 for item in aggregate.static_checks)


def test_all_24_fluid_outlets_are_screened_over_every_worn_pose(aggregate):
    assert len(aggregate.fluid_checks) == 24
    assert len({item.outlet_id for item in aggregate.fluid_checks}) == 24
    assert {item.status for item in aggregate.fluid_checks} <= {FLUID_CLEAR, FLUID_CONFLICT}
    for item in aggregate.fluid_checks:
        assert item.sampled_pose_count == 459
        assert item.required_clearance_mm == pytest.approx(0.6875, abs=1e-12)
        assert item.outlet_position_sensitivity_mm == pytest.approx(0.5, abs=1e-12)
        assert item.outlet_radius_mm == pytest.approx(0.1875, abs=1e-12)
        assert item.outlet_direction_sensitivity_deg == pytest.approx(5.0, abs=1e-12)
        assert item.minimum_sampled_clearance_mm <= item.nominal_protected_clearance_mm + 1e-12
        assert item.direction_path_status == DIRECTION_BLOCKED
    assert aggregate.fluid_sampled_conflict_count > 0


def test_moving_mechanisms_fail_closed_until_released_sweeps_exist(aggregate):
    domains = {item.domain_id: item for item in aggregate.moving_mechanisms}
    assert set(domains) == {"ACTUATION_SWEEP", "RETENTION_AND_EMERGENCY_RELEASE_SWEEP"}
    assert all(item.status == MOVING_BLOCKED for item in domains.values())
    assert all(item.released_sweep_geometry_available is False for item in domains.values())
    assert domains["ACTUATION_SWEEP"].source_contract_sha256 == aggregate.actuation_displacement_contract_sha256
    assert domains["RETENTION_AND_EMERGENCY_RELEASE_SWEEP"].source_contract_sha256 is None


def test_manifest_is_deterministic_and_preserves_evidence_firewall(aggregate):
    first = aggregate.manifest()
    second = aggregate.manifest()
    assert first == second
    assert first["aggregate_sha256"] == aggregate.aggregate_sha256
    assert first["physical_validation_eligible"] is False
    assert first["evidence_status"] == DIGITAL_ONLY
    assert first["precheck_status"] == "DIGITAL_PROTECTED_FACE_CONFLICT_PRESENT_RELEASE_BLOCKED"
    assert json.dumps(first, sort_keys=True, separators=(",", ":"), allow_nan=False)
