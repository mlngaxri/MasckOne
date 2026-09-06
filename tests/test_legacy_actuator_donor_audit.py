from __future__ import annotations

from dataclasses import replace
import json
import math

import cadquery as cq
import pytest

import masck_one.legacy_actuator_donor_audit as donor
from masck_one.model import build_model


def _build():
    model = build_model()
    return model, donor.build_legacy_actuator_donor_audit(model=model)


def test_legacy_actuator_donor_audit_is_source_bound_reference_only_and_canonical():
    _model, audit = _build()
    manifest = audit.manifest()

    assert manifest["schema"] == "MASCK_ONE_LEGACY_ACTUATOR_DONOR_AUDIT_V1"
    assert manifest["authored_against_main_sha"] == "5c41702f23ffe5a602b8af363e8588867d9af2e0"
    assert manifest["authority_revision"] == "2026-08-30-R1"
    assert manifest["coordinate_frame_id"] == "MASCK_ONE_AUTHORITY_WORLD_MM"
    assert manifest["legacy_coordinate_frame_id"] == "MASCK_ONE_CANONICAL_XYZ"
    assert manifest["legacy_donor_pr"] == 63
    assert manifest["legacy_donor_head_sha"] == "23b942bbb7f335eac74b42fa1b1613900e5a9347"
    assert manifest["legacy_donor_structure_blob_sha"] == "28b069ea2fdfa445ec63c930c142c67f392c7b99"
    assert manifest["physical_assembly_inclusion"] is False
    assert manifest["physical_validation_eligible"] is False
    assert "NOT_CURRENT_MOUNT_ATTACHMENT" in manifest["evidence_status"]
    assert len(manifest["source_git_blob_identities"]) == 8
    assert all(len(item["git_blob_sha"]) == 40 for item in manifest["source_git_blob_identities"])


def test_live_authority_doe_and_four_zone_order_drive_every_collision_row():
    _model, audit = _build()

    assert audit.angle_doe_deg == (50.0, 55.0, 61.0, 67.0, 72.0)
    assert audit.baseline_angle_deg == 61.0
    assert donor.ZONE_IDS == (
        "ACTUATOR_ZONE_SUPERIOR_LEFT",
        "ACTUATOR_ZONE_SUPERIOR_RIGHT",
        "ACTUATOR_ZONE_INFERIOR_LEFT",
        "ACTUATOR_ZONE_INFERIOR_RIGHT",
    )
    assert len(audit.static_overlap_records) == 8
    assert len(audit.angle_doe_records) == 60

    by_zone_angle_target = {
        (record.zone_id, record.angle_deg, record.target_id): record
        for record in audit.angle_doe_records
    }
    for zone_id in donor.ZONE_IDS:
        for angle in audit.angle_doe_deg:
            assert sum(
                1
                for key in by_zone_angle_target
                if key[0] == zone_id and key[1] == angle
            ) == 3


def test_donor_static_collar_shoe_and_shoe_frame_overlap_is_never_attachment_evidence():
    _model, audit = _build()

    assert all(record.intersection_volume_mm3 > 0.0 for record in audit.static_overlap_records)
    assert all(record.classification == "FORBIDDEN_OVERLAP_AS_ATTACHMENT" for record in audit.static_overlap_records)
    assert all(record.forbidden_pattern_id == "FORBID_RAW_MATERIAL_OVERLAP_AS_ATTACHMENT" for record in audit.static_overlap_records)

    pattern = next(
        item for item in audit.forbidden_patterns
        if item.pattern_id == "FORBID_RAW_MATERIAL_OVERLAP_AS_ATTACHMENT"
    )
    assert set(pattern.evidence_record_ids) == {record.record_id for record in audit.static_overlap_records}
    assert pattern.disposition == "REJECT"


def test_fixed_baseline_closed_collar_fails_the_live_angle_doe_but_clears_at_baseline():
    _model, audit = _build()
    collar_rows = [record for record in audit.angle_doe_records if record.target_id.endswith("_MOUNT_COLLAR")]

    for zone_id in donor.ZONE_IDS:
        baseline = next(
            record for record in collar_rows
            if record.zone_id == zone_id and record.angle_deg == audit.baseline_angle_deg
        )
        assert baseline.intersection_volume_mm3 == 0.0
        assert baseline.classification == "CLEAR_REFERENCE_ONLY_NO_ATTACHMENT_PROVEN"

        off_baseline = [
            record for record in collar_rows
            if record.zone_id == zone_id and record.angle_deg != audit.baseline_angle_deg
        ]
        assert len(off_baseline) == 4
        assert any(record.intersection_volume_mm3 > 0.0 for record in off_baseline)
        assert all(
            record.classification in {
                "LEGACY_MOVING_ACTUATOR_COLLISION",
                "CLEAR_REFERENCE_ONLY_NO_ATTACHMENT_PROVEN",
            }
            for record in off_baseline
        )

    pattern = next(
        item for item in audit.forbidden_patterns
        if item.pattern_id == "FORBID_FIXED_BASELINE_COLLAR_AS_ANGLE_DOE_CLEARANCE_GEOMETRY"
    )
    assert pattern.evidence_record_ids
    assert "installed mechanism is not expected to articulate through the DOE" in pattern.successor_requirement


def test_donor_shoe_and_frame_material_intersect_actuator_motion_and_are_rejected():
    _model, audit = _build()
    shoe_rows = [record for record in audit.angle_doe_records if record.target_id.endswith("_REACTION_SHOE")]
    frame_rows = [
        record for record in audit.angle_doe_records
        if record.target_id == "LEGACY_PR63_FRAME_PERIMETER_REACTION_MEMBER"
    ]

    assert any(
        record.angle_deg == audit.baseline_angle_deg and record.intersection_volume_mm3 > 0.0
        for record in shoe_rows
    )
    assert any(record.intersection_volume_mm3 > 0.0 for record in frame_rows)
    assert all(
        record.classification == "LEGACY_MOVING_ACTUATOR_COLLISION"
        for record in shoe_rows + frame_rows
        if record.intersection_volume_mm3 > 0.0
    )

    shoe_pattern = next(
        item for item in audit.forbidden_patterns
        if item.pattern_id == "FORBID_REACTION_SHOE_IN_ACTUATOR_MOTION"
    )
    frame_pattern = next(
        item for item in audit.forbidden_patterns
        if item.pattern_id == "FORBID_FRAME_IN_ACTUATOR_MOTION"
    )
    assert shoe_pattern.evidence_record_ids
    assert frame_pattern.evidence_record_ids
    assert "Cell 6" in frame_pattern.successor_requirement


def test_only_single_axis_and_current_source_packaging_intent_are_salvaged():
    _model, audit = _build()
    decisions = {item.semantic_id: item for item in audit.semantic_decisions}

    assert decisions["FOUR_INDEPENDENT_ZONES"].disposition == "CURRENT_AUTHORITY_REFERENCE_NOT_DONOR_SALVAGE"
    assert decisions["SINGLE_LINEAR_AXIS_PER_ZONE"].disposition == "SALVAGE_COMPATIBLE_SINGLE_AXIS_SEMANTIC_ONLY"
    assert decisions["ANGLE_DOE_ROTATES_SAME_AXIS_NOT_SECOND_DOF"].disposition == "SALVAGE_COMPATIBLE_SINGLE_AXIS_SEMANTIC_ONLY"
    assert decisions["ACTUATOR_PACKAGE_REFERENCE_DIAMETER_LENGTH_MM"].disposition == "SALVAGE_CURRENT_SOURCE_PACKAGING_INTENT_ONLY"
    assert decisions["ACTUATOR_PACKAGE_REFERENCE_DIAMETER_LENGTH_MM"].legacy_value == [10.2, 18.7]
    assert decisions["COAXIAL_CARRIER_PACKAGING_INTENT"].disposition == "SALVAGE_CURRENT_SOURCE_PACKAGING_INTENT_ONLY"

    for rejected_id in (
        "DONOR_CLOSED_COLLAR_DIMENSIONS_MM",
        "DONOR_REACTION_SHOE_DIMENSIONS_MM",
        "DONOR_SIMPLE_FRAME_RING",
        "DONOR_WORLD_ZONE_ORIGINS",
    ):
        assert decisions[rejected_id].disposition == "REJECT"

    assert audit.current_model_package_reference_status == "MATCHES_CURRENT_MODEL_10P2_DIAMETER_X_18P7_LENGTH_REFERENCE_ONLY"
    assert audit.current_mount_resolution_status == "UNRESOLVED_PER_CURRENT_ACTUATOR_FRAMES_AND_COUPLING_SOURCES"


def test_current_model_package_reference_brep_matches_legacy_packaging_intent_only():
    model, audit = _build()
    expected_volume = math.pi * (10.2 / 2.0) ** 2 * 18.7

    assert audit.current_model_package_reference_status.endswith("REFERENCE_ONLY")
    assert tuple(component.status for component in model.actuator_envelopes) == ("ALPHA_PHYSICS_REFERENCE",) * 4
    for component in model.actuator_envelopes:
        assert abs(float(component.solid.val().Volume()) - expected_volume) <= donor.PACKAGE_VOLUME_TOLERANCE_MM3


def test_reference_parts_cannot_be_relabelled_as_physical_material():
    _model, audit = _build()
    part = audit.reference_parts[0]

    with pytest.raises(donor.LegacyActuatorDonorAuditError, match="cannot enter physical material"):
        replace(part, geometry_role="PHYSICAL_MATERIAL")


def test_positive_overlap_cannot_be_relabelled_clear_or_attachment():
    _model, audit = _build()
    positive = next(record for record in audit.static_overlap_records if record.intersection_volume_mm3 > 0.0)

    with pytest.raises(donor.LegacyActuatorDonorAuditError, match="positive donor intersection"):
        replace(positive, classification="CLEAR_REFERENCE_ONLY_NO_ATTACHMENT_PROVEN")

    with pytest.raises(donor.LegacyActuatorDonorAuditError, match="positive donor intersection"):
        replace(positive, classification="POSITIVE_ATTACHMENT")


def test_nonfinite_or_negative_intersection_values_fail_closed():
    _model, audit = _build()
    record = audit.angle_doe_records[0]

    with pytest.raises(donor.LegacyActuatorDonorAuditError, match="finite"):
        replace(record, intersection_volume_mm3=float("nan"))
    with pytest.raises(donor.LegacyActuatorDonorAuditError, match="cannot be negative"):
        replace(record, intersection_volume_mm3=-1.0)


def test_current_source_blob_movement_invalidates_audit(monkeypatch):
    bad = list(donor.SOURCE_GIT_BLOB_IDENTITIES)
    bad[0] = (bad[0][0], "0" * 40)
    monkeypatch.setattr(donor, "SOURCE_GIT_BLOB_IDENTITIES", tuple(bad))

    with pytest.raises(donor.LegacyActuatorDonorAuditError, match="current source moved"):
        donor.build_legacy_actuator_donor_audit()


def test_world_frame_mount_and_physical_evidence_promotions_fail_closed():
    _model, audit = _build()

    with pytest.raises(donor.LegacyActuatorDonorAuditError, match="canonical authority world"):
        replace(audit, coordinate_frame_id="LEGACY_LOCAL")
    with pytest.raises(donor.LegacyActuatorDonorAuditError, match="cannot promote unresolved current actuator mounts"):
        replace(audit, current_mount_resolution_status="RESOLVED_FROM_DONOR")
    with pytest.raises(donor.LegacyActuatorDonorAuditError, match="cannot enter physical assembly"):
        replace(audit, physical_assembly_inclusion=True)
    with pytest.raises(donor.LegacyActuatorDonorAuditError, match="cannot be physical validation evidence"):
        replace(audit, physical_validation_eligible=True)
    with pytest.raises(donor.LegacyActuatorDonorAuditError, match="evidence firewall drifted"):
        replace(audit, evidence_status="PHYSICAL_VALIDATED")


def test_unknown_forbidden_pattern_evidence_and_semantic_reorder_fail_closed():
    _model, audit = _build()
    first_pattern = audit.forbidden_patterns[0]
    bad_pattern = replace(first_pattern, evidence_record_ids=("UNKNOWN_RECORD",))

    with pytest.raises(donor.LegacyActuatorDonorAuditError, match="unknown measurement evidence"):
        replace(audit, forbidden_patterns=(bad_pattern, *audit.forbidden_patterns[1:]))
    with pytest.raises(donor.LegacyActuatorDonorAuditError, match="semantic decision order changed"):
        replace(audit, semantic_decisions=tuple(reversed(audit.semantic_decisions)))


def test_manifest_identity_is_deterministic_for_same_current_sources():
    model = build_model()
    first = donor.build_legacy_actuator_donor_audit(model=model)
    second = donor.build_legacy_actuator_donor_audit(model=model)

    assert first.reference_geometry_sha256 == second.reference_geometry_sha256
    assert first.audit_sha256 == second.audit_sha256
    assert first.manifest() == second.manifest()


def test_reference_only_step_and_json_review_artifacts_round_trip(tmp_path):
    model = build_model()
    manifest = donor.export_legacy_actuator_donor_review(tmp_path, model=model)

    fixed_step = tmp_path / "legacy_pr63_actuator_mount_reference_only.step"
    doe_step = tmp_path / "legacy_pr63_actuator_angle_doe_reference_only.step"
    manifest_path = tmp_path / "legacy_pr63_actuator_donor_audit.json"
    assert fixed_step.is_file()
    assert doe_step.is_file()
    assert manifest_path.is_file()

    fixed_shape = cq.importers.importStep(str(fixed_step)).val()
    doe_shape = cq.importers.importStep(str(doe_step)).val()
    assert fixed_shape.isValid()
    assert doe_shape.isValid()
    assert float(fixed_shape.Volume()) > 0.0
    assert float(doe_shape.Volume()) > 0.0

    on_disk = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert on_disk["audit_sha256"] == manifest["audit_sha256"]
    assert on_disk["reference_geometry_sha256"] == manifest["reference_geometry_sha256"]
    assert on_disk["review_artifact_role"] == donor.REFERENCE_ROLE
    assert on_disk["physical_assembly_inclusion"] is False
    assert on_disk["review_step_files"] == [
        "legacy_pr63_actuator_mount_reference_only.step",
        "legacy_pr63_actuator_angle_doe_reference_only.step",
    ]
