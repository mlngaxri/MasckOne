from dataclasses import replace

import pytest

from masck_one import structural_frame_retention_root_service_v5 as v5


def test_v5_binds_positive_bilateral_service_separation():
    audit = v5.build_structural_frame_retention_root_service_v5()
    assert audit.minimum_bilateral_service_separation_mm >= v5.MIN_BILATERAL_SERVICE_SEPARATION_MM
    assert audit.physical_validation_eligible is False
    manifest = audit.manifest()
    assert manifest["source_v4_evidence_sha256"] == audit.source_v4_evidence_sha256
    assert manifest["whole_head_removal_status"] == "OPEN"


def test_v5_rejects_stale_v4_provenance():
    audit = v5.build_structural_frame_retention_root_service_v5()
    with pytest.raises(v5.StructuralFrameRetentionRootServiceV5Error, match="source V4"):
        replace(audit, source_v4_evidence_sha256="0" * 64).validate()


def test_v5_rejects_stale_minimum_and_digest():
    audit = v5.build_structural_frame_retention_root_service_v5()
    with pytest.raises(v5.StructuralFrameRetentionRootServiceV5Error, match="stale or insufficient"):
        replace(audit, minimum_bilateral_service_separation_mm=audit.minimum_bilateral_service_separation_mm + 0.01).validate()
    with pytest.raises(v5.StructuralFrameRetentionRootServiceV5Error, match="digest"):
        replace(audit, separation_evidence_sha256="f" * 64).validate()


def test_v5_rejects_physical_validation_promotion():
    audit = v5.build_structural_frame_retention_root_service_v5()
    with pytest.raises(v5.StructuralFrameRetentionRootServiceV5Error, match="not physical"):
        replace(audit, physical_validation_eligible=True).validate()


def test_v5_rejects_insufficient_axis_separation(monkeypatch):
    monkeypatch.setattr(v5, "_axis_separation", lambda first, second: (0.0, 0.0, 0.0))
    with pytest.raises(v5.StructuralFrameRetentionRootServiceV5Error, match="reserve is insufficient"):
        v5.build_structural_frame_retention_root_service_v5()
