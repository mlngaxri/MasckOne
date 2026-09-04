from masck_one.authority import load_authority
from masck_one.model import build_model
from masck_one.whole_product_interference import (
    KERNEL_ZERO_VOLUME_MM3,
    PROTECTED_SCREEN_Z_MAX_MM,
    PROTECTED_SCREEN_Z_MIN_MM,
    SCHEMA,
    build_whole_product_interference_audit,
)
from masck_one.whole_product_package import KNOWN_PACKAGE_IDS


def _audit():
    return build_whole_product_interference_audit(build_model(load_authority()))


def test_exact_interference_audit_is_deterministic_and_bound_to_package_registry():
    first = _audit()
    second = _audit()
    assert first.manifest()["schema"] == SCHEMA
    assert first.audit_sha256 == second.audit_sha256
    assert first.package_sha256 == second.package_sha256
    expected_pairs = len(KNOWN_PACKAGE_IDS) * (len(KNOWN_PACKAGE_IDS) - 1) // 2
    assert len(first.package_pairs) == expected_pairs


def test_exact_shape_work_runs_only_after_broad_phase_candidate_overlap():
    audit = _audit()
    for record in audit.package_pairs:
        if record.broad_phase_overlap_mm3 == 0.0:
            assert record.exact_intersection_mm3 == 0.0
            assert record.status == "EXACT_BREP_CLEAR_DIGITAL_ONLY"
        if record.exact_intersection_mm3 > 0.0:
            assert record.broad_phase_overlap_mm3 > 0.0


def test_current_released_actuator_baseline_exposes_eye_keepout_conflict_instead_of_hiding_it():
    audit = _audit()
    intrusion = {
        (record.package_id, record.screen_id): record
        for record in audit.protected_intrusions
    }
    left = intrusion[("ACTUATOR_1", "PROTECTED-SCREEN-EYE-LEFT")]
    right = intrusion[("ACTUATOR_2", "PROTECTED-SCREEN-EYE-RIGHT")]
    assert left.intersection_mm3 > KERNEL_ZERO_VOLUME_MM3
    assert right.intersection_mm3 > KERNEL_ZERO_VOLUME_MM3
    assert "REQUIRES_REPACKAGING" in left.status
    assert "REQUIRES_REPACKAGING" in right.status


def test_protected_screens_are_explicit_conservative_xy_extrusions_not_fake_anatomy():
    audit = _audit()
    assert len(audit.protected_screens) == 5
    assert PROTECTED_SCREEN_Z_MIN_MM < 0.0 < PROTECTED_SCREEN_Z_MAX_MM
    assert all("CONSERVATIVE_AUTHORITY_XY_RIGID_KEEPOUT_EXTRUSION" in screen.evidence_status for screen in audit.protected_screens)
    assert all("NOT_REGISTERED_3D_ANATOMY" in screen.evidence_status for screen in audit.protected_screens)


def test_every_service_motion_is_refined_against_every_other_released_package_shape():
    audit = _audit()
    motions = {record.motion_id for record in audit.service_sweep_records}
    assert len(motions) == 3
    for motion_id in motions:
        records = tuple(record for record in audit.service_sweep_records if record.motion_id == motion_id)
        assert len(records) == len(KNOWN_PACKAGE_IDS) - 1
        assert all(len(record.sample_intersection_mm3) >= 3 for record in records)
        assert all("DIGITAL" in record.status or "REQUIRES_REAL_OPENING_OR_REPACKAGING" in record.status for record in records)


def test_audit_never_promotes_digital_clearance_to_physical_validation():
    audit = _audit()
    assert "NOT_PHYSICAL_VALIDATION" in audit.evidence_status
    assert all(
        record.status != "PHYSICAL_PASS"
        for record in (*audit.package_pairs, *audit.protected_intrusions, *audit.service_sweep_records)
    )
