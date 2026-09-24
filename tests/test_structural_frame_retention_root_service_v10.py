from dataclasses import replace

import pytest

from masck_one import structural_frame_retention_root_service_v10 as v10


def test_v10_closes_authored_service_travel_without_overshoot():
    audit = v10.build_structural_frame_retention_root_service_v10()
    assert len(audit.travel_error_mm) == 2
    for _, pin_error, retainer_error in audit.travel_error_mm:
        assert abs(pin_error) <= v10.TRAVEL_TOLERANCE_MM
        assert abs(retainer_error) <= v10.TRAVEL_TOLERANCE_MM
    assert audit.manifest()["whole_head_removal_status"] == "OPEN"
    assert audit.physical_validation_eligible is False


def test_v10_rejects_stale_v9_provenance_and_records():
    audit = v10.build_structural_frame_retention_root_service_v10()
    with pytest.raises(v10.StructuralFrameRetentionRootServiceV10Error, match="source V9"):
        replace(audit, source_v9_reach_evidence_sha256="0" * 64).validate()
    records = list(audit.travel_error_mm)
    root_id, pin_error, retainer_error = records[0]
    records[0] = (root_id, pin_error + 0.001, retainer_error)
    with pytest.raises(v10.StructuralFrameRetentionRootServiceV10Error, match="closure evidence is stale"):
        replace(audit, travel_error_mm=tuple(records)).validate()


def test_v10_rejects_digest_corruption():
    audit = v10.build_structural_frame_retention_root_service_v10()
    with pytest.raises(v10.StructuralFrameRetentionRootServiceV10Error, match="digest"):
        replace(audit, travel_closure_evidence_sha256="f" * 64).validate()


def test_v10_rejects_pin_corridor_overshoot(monkeypatch):
    source = v10.v9.build_structural_frame_retention_root_service_v9()
    records = list(source.service_reach_mm)
    root_id, pin_reach, retainer_reach = records[0]
    records[0] = (root_id, pin_reach + 0.01, retainer_reach)
    monkeypatch.setattr(v10.v9, "build_structural_frame_retention_root_service_v9", lambda: replace(source, service_reach_mm=tuple(records)))
    with pytest.raises(v10.StructuralFrameRetentionRootServiceV10Error, match="pin corridor exceeds"):
        v10._travel_closure_evidence()


def test_v10_rejects_retainer_corridor_overshoot(monkeypatch):
    source = v10.v9.build_structural_frame_retention_root_service_v9()
    records = list(source.service_reach_mm)
    root_id, pin_reach, retainer_reach = records[0]
    records[0] = (root_id, pin_reach, retainer_reach + 0.01)
    monkeypatch.setattr(v10.v9, "build_structural_frame_retention_root_service_v9", lambda: replace(source, service_reach_mm=tuple(records)))
    with pytest.raises(v10.StructuralFrameRetentionRootServiceV10Error, match="retainer corridor exceeds"):
        v10._travel_closure_evidence()


def test_v10_rejects_physical_validation_promotion():
    audit = v10.build_structural_frame_retention_root_service_v10()
    with pytest.raises(v10.StructuralFrameRetentionRootServiceV10Error, match="not physical"):
        replace(audit, physical_validation_eligible=True).validate()
