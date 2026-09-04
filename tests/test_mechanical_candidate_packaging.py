import hashlib
import json

import pytest

from masck_one.authority import load_authority
from masck_one.mechanical_candidate_packaging import (
    ACTUATOR_SUPERSESSION,
    BASELINE_EXTERNAL_PACKAGE_IDS,
    SCHEMA,
    build_mechanical_candidate_package_audit,
)
from masck_one.mechanical_integration import build_mechanical_realization
from masck_one.mechanical_structure import build_manual_a_mechanical_structure
from masck_one.whole_product_interference import build_whole_product_interference_audit
from masck_one.model import build_model


@pytest.fixture(scope="module")
def audit():
    return build_mechanical_candidate_package_audit(load_authority())


def test_candidate_package_audit_is_stable_and_bound_to_realization(audit):
    assert audit.manifest()["schema"] == SCHEMA
    payload = audit.manifest(include_sha=False)
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    assert audit.audit_sha256 == digest
    assert len(audit.realization_sha256) == 64
    assert tuple(item.package_id for item in audit.baseline_external_packages) == BASELINE_EXTERNAL_PACKAGE_IDS


def test_actuator_repackaging_explicitly_supersedes_all_four_released_positions(audit):
    assert tuple(
        (record.baseline_package_id, record.candidate_part_id)
        for record in audit.actuator_supersession
    ) == ACTUATOR_SUPERSESSION
    assert all(record.displacement_magnitude_mm > 0.0 for record in audit.actuator_supersession)
    assert all("REPACKAGING_CANDIDATE" in record.status for record in audit.actuator_supersession)


def test_candidate_manual_a_parts_including_release_guard_clear_released_packages(audit):
    failures = [check.manifest() for check in audit.required_clear_failures]
    assert not failures, f"Manual A candidate has cross-package conflicts: {failures}"
    guard_checks = tuple(
        check for check in audit.cross_package_checks
        if check.candidate_part_id == "QUICK-RELEASE-GUARD"
    )
    assert len(guard_checks) == len(BASELINE_EXTERNAL_PACKAGE_IDS)
    assert all(check.required_clear for check in guard_checks)
    assert all(check.passes for check in guard_checks)


def test_candidate_relocation_resolves_released_upper_actuator_eye_screen_conflict():
    authority = load_authority()
    model = build_model(authority)
    baseline = build_whole_product_interference_audit(model)
    realization = build_mechanical_realization(authority)
    structure = build_manual_a_mechanical_structure(authority, model)

    baseline_intrusions = {
        (record.package_id, record.screen_id): record.intersection_mm3
        for record in baseline.protected_intrusions
    }
    assert baseline_intrusions[("ACTUATOR_1", "PROTECTED-SCREEN-EYE-LEFT")] > 0.0
    assert baseline_intrusions[("ACTUATOR_2", "PROTECTED-SCREEN-EYE-RIGHT")] > 0.0

    # The integration projection must consume the canonical structure result rather
    # than re-authoring a second actuator/keepout coordinate system.
    assert realization.source_structure_sha256 == structure.package_sha256
    assert structure.all_required_clear, structure.conflict_ids
    left_checks = tuple(
        item for item in structure.clearance_results
        if item.moving_id == "ACTUATOR_ZONE_SUPERIOR_LEFT"
        and item.obstacle_id == "MASCK_ONE-PROTECTED-EYE-LEFT"
    )
    right_checks = tuple(
        item for item in structure.clearance_results
        if item.moving_id == "ACTUATOR_ZONE_SUPERIOR_RIGHT"
        and item.obstacle_id == "MASCK_ONE-PROTECTED-EYE-RIGHT"
    )
    assert left_checks and all(item.passes for item in left_checks)
    assert right_checks and all(item.passes for item in right_checks)


def test_other_lane_geometry_remains_explicitly_unresolved(audit):
    assert "FRESH_FLUID_REALIZED_CENTERLINES" in audit.unresolved_external_classes
    assert "WASTE_FLUID_REALIZED_CENTERLINES_AND_BACKFLOW_DEVICE" in audit.unresolved_external_classes
    assert "PCB_DRY_BAY_AND_HARNESS" in audit.unresolved_external_classes
    assert "PHYSICAL_HMI" in audit.unresolved_external_classes
    assert "WARM_HARDWARE" in audit.unresolved_external_classes
    assert "COOL_RESERVATION" in audit.unresolved_external_classes
    assert "NOT_PHYSICAL_VALIDATION" in audit.evidence_status
