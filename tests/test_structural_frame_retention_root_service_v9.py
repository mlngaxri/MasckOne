from dataclasses import replace

import pytest

from masck_one import structural_frame_retention_root_service_v9 as v9


def test_v9_binds_full_service_reach_and_symmetry():
    audit = v9.build_structural_frame_retention_root_service_v9()
    assert len(audit.service_reach_mm) == 2
    for _, pin_reach, retainer_reach in audit.service_reach_mm:
        assert pin_reach >= v9.v1.PIN_WITHDRAW_EXTENSION_MM
        assert retainer_reach >= v9.v1.CLIP_RADIAL_EXTENSION_MM
    assert audit.physical_validation_eligible is False
    assert audit.manifest()["whole_head_removal_status"] == "OPEN"


def test_v9_rejects_stale_v8_provenance_and_records():
    audit = v9.build_structural_frame_retention_root_service_v9()
    with pytest.raises(v9.StructuralFrameRetentionRootServiceV9Error, match="source V8"):
        replace(audit, source_v8_evidence_sha256="0" * 64).validate()
    records = list(audit.service_reach_mm)
    root_id, pin_reach, retainer_reach = records[0]
    records[0] = (root_id, pin_reach + 0.01, retainer_reach)
    with pytest.raises(v9.StructuralFrameRetentionRootServiceV9Error, match="reach evidence is stale"):
        replace(audit, service_reach_mm=tuple(records)).validate()


def test_v9_rejects_digest_corruption():
    audit = v9.build_structural_frame_retention_root_service_v9()
    with pytest.raises(v9.StructuralFrameRetentionRootServiceV9Error, match="digest"):
        replace(audit, reach_evidence_sha256="f" * 64).validate()


def test_v9_rejects_truncated_pin_reach(monkeypatch):
    original = v9._axis_span
    monkeypatch.setattr(v9, "_axis_span", lambda shape, axis: v9.v1.PIN_WITHDRAW_EXTENSION_MM - 0.01 if axis == "y" else original(shape, axis))
    with pytest.raises(v9.StructuralFrameRetentionRootServiceV9Error, match="pin service corridor is truncated"):
        v9._reach_evidence()


def test_v9_rejects_truncated_retainer_reach(monkeypatch):
    original = v9._axis_span
    monkeypatch.setattr(v9, "_axis_span", lambda shape, axis: v9.v1.CLIP_RADIAL_EXTENSION_MM - 0.01 if axis == "z" else original(shape, axis))
    with pytest.raises(v9.StructuralFrameRetentionRootServiceV9Error, match="retainer service corridor is truncated"):
        v9._reach_evidence()


def test_v9_rejects_physical_validation_promotion():
    audit = v9.build_structural_frame_retention_root_service_v9()
    with pytest.raises(v9.StructuralFrameRetentionRootServiceV9Error, match="not physical"):
        replace(audit, physical_validation_eligible=True).validate()
