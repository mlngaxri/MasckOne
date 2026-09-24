from dataclasses import replace

import pytest

from masck_one import structural_frame_retention_root_service_v8 as v8


def test_v8_binds_local_operation_separation_and_symmetry():
    audit = v8.build_structural_frame_retention_root_service_v8()
    assert len(audit.local_operation_separations_mm) == 2
    assert min(distance for _, distance in audit.local_operation_separations_mm) >= v8.MIN_LOCAL_OPERATION_SEPARATION_MM
    assert abs(audit.local_operation_separations_mm[0][1] - audit.local_operation_separations_mm[1][1]) <= v8.SYMMETRY_TOLERANCE_MM
    assert audit.physical_validation_eligible is False
    assert audit.manifest()["whole_head_removal_status"] == "OPEN"


def test_v8_rejects_stale_v7_provenance():
    audit = v8.build_structural_frame_retention_root_service_v8()
    with pytest.raises(v8.StructuralFrameRetentionRootServiceV8Error, match="source V7"):
        replace(audit, source_v7_evidence_sha256="0" * 64).validate()


def test_v8_rejects_stale_local_records_and_digest():
    audit = v8.build_structural_frame_retention_root_service_v8()
    records = list(audit.local_operation_separations_mm)
    root_id, distance = records[0]
    records[0] = (root_id, distance + 0.01)
    with pytest.raises(v8.StructuralFrameRetentionRootServiceV8Error, match="evidence is stale"):
        replace(audit, local_operation_separations_mm=tuple(records)).validate()
    with pytest.raises(v8.StructuralFrameRetentionRootServiceV8Error, match="digest"):
        replace(audit, local_access_evidence_sha256="f" * 64).validate()


def test_v8_rejects_insufficient_local_separation(monkeypatch):
    monkeypatch.setattr(v8.v6, "_brep_distance", lambda first, second: v8.MIN_LOCAL_OPERATION_SEPARATION_MM - 0.01)
    with pytest.raises(v8.StructuralFrameRetentionRootServiceV8Error, match="insufficiently separated"):
        v8._local_access_evidence()


def test_v8_rejects_asymmetric_local_access(monkeypatch):
    values = iter((1.0, 1.01))
    monkeypatch.setattr(v8.v6, "_brep_distance", lambda first, second: next(values))
    with pytest.raises(v8.StructuralFrameRetentionRootServiceV8Error, match="mirror-equivalent"):
        v8._local_access_evidence()


def test_v8_rejects_physical_validation_promotion():
    audit = v8.build_structural_frame_retention_root_service_v8()
    with pytest.raises(v8.StructuralFrameRetentionRootServiceV8Error, match="not physical"):
        replace(audit, physical_validation_eligible=True).validate()
