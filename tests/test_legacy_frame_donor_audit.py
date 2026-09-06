from __future__ import annotations

from dataclasses import replace
import json
import math

import cadquery as cq
import pytest

from masck_one import legacy_frame_donor_audit as donor_module
from masck_one.legacy_frame_donor_audit import (
    DONOR_FRAME_DEPTH_MM,
    DONOR_FRAME_MEMBER_RADIAL_MM,
    EVIDENCE_STATUS,
    LEGACY_DONOR_HEAD_SHA,
    LEGACY_DONOR_STRUCTURE_BLOB_SHA,
    REFERENCE_ROLE,
    SALVAGE_DATUM_ORDER,
    WORLD_FRAME_ID,
    DonorOverlapRecord,
    LegacyFrameDonorAuditError,
    build_legacy_frame_donor_audit,
    export_legacy_frame_donor_review,
)
from masck_one.model import build_model


@pytest.fixture(scope="module")
def donor_audit():
    model = build_model()
    return build_legacy_frame_donor_audit(model=model)


def _max_collision(audit, *, angle_deg: float, target_fragment: str) -> float:
    marker = f"_AT_{angle_deg:g}_DEG"
    values = [
        record.intersection_volume_mm3
        for record in audit.actuator_collision_records
        if marker in record.source_id and target_fragment in record.target_id
    ]
    assert values
    return max(values)


def test_legacy_pr63_reconstruction_is_reference_only_and_source_bound(donor_audit):
    audit = donor_audit
    assert audit.coordinate_frame_id == WORLD_FRAME_ID
    assert audit.legacy_coordinate_frame_id != WORLD_FRAME_ID
    assert audit.physical_validation_eligible is False
    assert audit.evidence_status == EVIDENCE_STATUS
    assert audit.manifest()["legacy_donor_head_sha"] == LEGACY_DONOR_HEAD_SHA
    assert audit.manifest()["legacy_donor_structure_blob_sha"] == LEGACY_DONOR_STRUCTURE_BLOB_SHA
    assert all(part.geometry_role == REFERENCE_ROLE for part in audit.reference_parts)

    frame = next(
        part
        for part in audit.reference_parts
        if part.part_id == "LEGACY_PR63_FRAME_PERIMETER_REACTION_MEMBER"
    )
    frame_manifest = frame.manifest()
    assert frame_manifest["bbox_mm"] == pytest.approx(
        [-77.5, -101.0, -4.0, 77.5, 101.0, -1.6], abs=2e-6
    )
    assert frame_manifest["volume_mm3"] > 0.0


def test_legacy_overlap_join_defects_are_quantified_not_promoted(donor_audit):
    audit = donor_audit
    frame_overlap_records = [
        record
        for record in audit.overlap_records
        if record.target_id == "LEGACY_PR63_FRAME_PERIMETER_REACTION_MEMBER"
    ]
    assert len(frame_overlap_records) == 5
    assert all(record.intersection_volume_mm3 > 0.0 for record in frame_overlap_records)
    assert all("NOT_ATTACHMENT" in record.interpretation for record in frame_overlap_records)

    expected = {
        "LEGACY_PR63_FRAME_SHELL_BRIDGE_WEARER_LEFT": 24.87162293,
        "LEGACY_PR63_FRAME_SHELL_BRIDGE_WEARER_RIGHT": 24.87162293,
        "LEGACY_PR63_FRAME_SHELL_BRIDGE_SUPERIOR": 24.04501919,
        "LEGACY_PR63_RETENTION_LEFT_FRAME_CLEVIS": 144.04693105,
        "LEGACY_PR63_RETENTION_RIGHT_FRAME_SOCKET": 70.90540976,
    }
    observed = {record.source_id: record.intersection_volume_mm3 for record in frame_overlap_records}
    assert set(observed) == set(expected)
    for part_id, expected_volume in expected.items():
        assert observed[part_id] == pytest.approx(expected_volume, abs=2e-6)

    assert audit.positive_join_status == (
        "UNRESOLVED_LEGACY_POSITIVE_INTERSECTION_IS_NOT_TYPED_ATTACHMENT"
    )
    assert audit.tool_access_status == (
        "UNPROVEN_NO_FASTENER_BOSS_INSERT_TOOL_OR_PROCESS_ACCESS_GEOMETRY"
    )
    assert audit.continuous_assembly_status == (
        "UNPROVEN_SAMPLED_WAYPOINTS_ARE_NOT_CONTINUOUS_SWEEPS"
    )


def test_legacy_reaction_shoes_use_large_raw_frame_overlap_not_typed_joins(donor_audit):
    frame = next(
        part
        for part in donor_audit.reference_parts
        if part.part_id == "LEGACY_PR63_FRAME_PERIMETER_REACTION_MEMBER"
    )
    shoes = {
        part.part_id: donor_module._intersection_volume(part.solid, frame.solid)
        for part in donor_audit.reference_parts
        if "REACTION_SHOE" in part.part_id
    }
    expected = {
        "LEGACY_PR63_ACTUATOR_ZONE_SUPERIOR_LEFT_REACTION_SHOE": 127.34208317,
        "LEGACY_PR63_ACTUATOR_ZONE_SUPERIOR_RIGHT_REACTION_SHOE": 127.34208319,
        "LEGACY_PR63_ACTUATOR_ZONE_INFERIOR_LEFT_REACTION_SHOE": 193.45192844,
        "LEGACY_PR63_ACTUATOR_ZONE_INFERIOR_RIGHT_REACTION_SHOE": 193.45192732,
    }
    assert set(shoes) == set(expected)
    for part_id, expected_volume in expected.items():
        assert shoes[part_id] == pytest.approx(expected_volume, abs=2e-6)
        assert shoes[part_id] > 0.0


def test_legacy_actuator_collisions_reproduce_exact_source_defect_scale(donor_audit):
    audit = donor_audit
    baseline = audit.donor_baseline_angle_deg
    assert baseline == 61.0

    baseline_shoe = _max_collision(audit, angle_deg=baseline, target_fragment="REACTION_SHOE")
    baseline_frame = _max_collision(audit, angle_deg=baseline, target_fragment="FRAME_PERIMETER")
    doe_shoe = max(
        record.intersection_volume_mm3
        for record in audit.actuator_collision_records
        if "REACTION_SHOE" in record.target_id
    )
    doe_frame = max(
        record.intersection_volume_mm3
        for record in audit.actuator_collision_records
        if "FRAME_PERIMETER" in record.target_id
    )

    assert baseline_shoe == pytest.approx(21.993454, abs=2e-4)
    assert baseline_frame == pytest.approx(2.664932, abs=2e-4)
    assert doe_shoe == pytest.approx(43.628465, abs=2e-4)
    assert doe_frame == pytest.approx(8.185202, abs=2e-4)
    assert any(
        record.intersection_volume_mm3 > 0.0
        and record.interpretation == "LEGACY_ACTUATOR_MATERIAL_COLLISION"
        for record in audit.actuator_collision_records
    )


def test_only_2p4_mm_axial_depth_survives_as_provisional_donor_seed(donor_audit):
    decisions = donor_audit.salvage_decisions
    assert tuple(item.datum_id for item in decisions) == SALVAGE_DATUM_ORDER
    depth = next(item for item in decisions if item.datum_id == "FRAME_AXIAL_DEPTH_MM")
    radial = next(item for item in decisions if item.datum_id == "FRAME_RADIAL_WIDTH_MM")
    functional = next(item for item in decisions if item.datum_id == "FRAME_FUNCTIONAL_XY_MM")

    assert depth.legacy_value == DONOR_FRAME_DEPTH_MM
    assert depth.disposition == "PROVISIONAL_SEED_ONLY"
    assert radial.legacy_value == DONOR_FRAME_MEMBER_RADIAL_MM
    assert radial.disposition == "REJECT"
    assert functional.disposition == "CURRENT_AUTHORITY_REFERENCE_NOT_DONOR_SALVAGE"
    assert sum(item.disposition == "PROVISIONAL_SEED_ONLY" for item in decisions) == 1


def test_legacy_reference_parts_stay_out_of_current_hard_protected_envelopes(donor_audit):
    assert donor_audit.protected_conflict_records
    assert all(
        record.intersection_volume_mm3 == 0.0
        for record in donor_audit.protected_conflict_records
    )


def test_review_export_is_explicitly_reference_only_and_step_round_trips(donor_audit, tmp_path):
    result = export_legacy_frame_donor_review(tmp_path, audit=donor_audit)
    assert result["physical_assembly_inclusion"] is False

    manifest_path = tmp_path / result["manifest_file"]
    step_path = tmp_path / result["step_file"]
    assert manifest_path.is_file() and step_path.is_file()
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert payload["review_artifact_role"] == REFERENCE_ROLE
    assert payload["physical_assembly_inclusion"] is False
    assert payload["audit_sha256"] == donor_audit.audit_sha256
    assert payload["reference_geometry_sha256"] == donor_audit.reference_geometry_sha256

    imported = cq.importers.importStep(str(step_path))
    assert imported.val().isValid()
    assert len(imported.val().Solids()) >= len(donor_audit.reference_parts)


def test_manifest_identity_is_deterministic_for_same_realized_audit(donor_audit):
    first = donor_audit.manifest()
    second = donor_audit.manifest()
    assert first == second
    assert json.dumps(first, sort_keys=True, separators=(",", ":"), allow_nan=False) == json.dumps(
        second, sort_keys=True, separators=(",", ":"), allow_nan=False
    )


def test_stale_current_source_binding_fails_closed(donor_audit, monkeypatch):
    bindings = list(donor_module.SOURCE_GIT_BLOB_IDENTITIES)
    path, _sha = bindings[-1]
    bindings[-1] = (path, "0" * 40)
    monkeypatch.setattr(donor_module, "SOURCE_GIT_BLOB_IDENTITIES", tuple(bindings))
    with pytest.raises(LegacyFrameDonorAuditError, match="current source moved"):
        build_legacy_frame_donor_audit()


def test_illegal_material_or_evidence_promotion_is_rejected(donor_audit):
    with pytest.raises(LegacyFrameDonorAuditError, match="canonical authority world"):
        replace(donor_audit, coordinate_frame_id="LEGACY_FRAME")
    with pytest.raises(LegacyFrameDonorAuditError, match="physical validation"):
        replace(donor_audit, physical_validation_eligible=True)

    part = donor_audit.reference_parts[0]
    with pytest.raises(LegacyFrameDonorAuditError, match="cannot enter physical material"):
        replace(part, geometry_role="PHYSICAL_STRUCTURAL_MATERIAL")


def test_positive_overlap_cannot_be_relabelled_as_attachment_and_nonfinite_is_rejected():
    with pytest.raises(LegacyFrameDonorAuditError, match="non-attachment or collision"):
        DonorOverlapRecord("A", "B", 1.0, "POSITIVE_ATTACHMENT")
    with pytest.raises(LegacyFrameDonorAuditError, match="finite"):
        DonorOverlapRecord("A", "B", math.nan, "LEGACY_COLLISION")


def test_only_controlled_seed_cannot_drift_to_other_legacy_dimensions(donor_audit):
    decisions = list(donor_audit.salvage_decisions)
    radial_index = next(
        index
        for index, item in enumerate(decisions)
        if item.datum_id == "FRAME_RADIAL_WIDTH_MM"
    )
    decisions[radial_index] = replace(
        decisions[radial_index],
        disposition="PROVISIONAL_SEED_ONLY",
    )
    with pytest.raises(LegacyFrameDonorAuditError, match="no other legacy frame datum"):
        replace(donor_audit, salvage_decisions=tuple(decisions))
