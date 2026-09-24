from dataclasses import replace

import pytest

from masck_one import structural_frame_retention_root_service_v6 as v6


def test_v6_binds_exact_brep_bilateral_service_clearance():
    audit = v6.build_structural_frame_retention_root_service_v6()
    assert audit.minimum_brep_service_clearance_mm >= v6.MIN_BREP_SERVICE_CLEARANCE_MM
    assert audit.physical_validation_eligible is False
    manifest = audit.manifest()
    assert manifest["source_v5_evidence_sha256"] == audit.source_v5_evidence_sha256
    assert manifest["whole_head_removal_status"] == "OPEN"


def test_v6_rejects_stale_v5_provenance():
    audit = v6.build_structural_frame_retention_root_service_v6()
    with pytest.raises(v6.StructuralFrameRetentionRootServiceV6Error, match="source V5"):
        replace(audit, source_v5_evidence_sha256="0" * 64).validate()


def test_v6_rejects_stale_minimum_and_digest():
    audit = v6.build_structural_frame_retention_root_service_v6()
    with pytest.raises(v6.StructuralFrameRetentionRootServiceV6Error, match="stale or insufficient"):
        replace(audit, minimum_brep_service_clearance_mm=audit.minimum_brep_service_clearance_mm + 0.01).validate()
    with pytest.raises(v6.StructuralFrameRetentionRootServiceV6Error, match="digest"):
        replace(audit, clearance_evidence_sha256="f" * 64).validate()


def test_v6_rejects_physical_validation_promotion():
    audit = v6.build_structural_frame_retention_root_service_v6()
    with pytest.raises(v6.StructuralFrameRetentionRootServiceV6Error, match="not physical"):
        replace(audit, physical_validation_eligible=True).validate()


def test_v6_rejects_insufficient_exact_clearance(monkeypatch):
    monkeypatch.setattr(v6, "_brep_distance", lambda first, second: 0.0)
    with pytest.raises(v6.StructuralFrameRetentionRootServiceV6Error, match="clearance is insufficient"):
        v6.build_structural_frame_retention_root_service_v6()


def test_v6_rejects_clearance_that_contradicts_v5(monkeypatch):
    source = v6.v5.build_structural_frame_retention_root_service_v5()
    contradictory = max(v6.MIN_BREP_SERVICE_CLEARANCE_MM, source.minimum_bilateral_service_separation_mm - 0.01)
    monkeypatch.setattr(v6, "_brep_distance", lambda first, second: contradictory)
    if contradictory < source.minimum_bilateral_service_separation_mm:
        with pytest.raises(v6.StructuralFrameRetentionRootServiceV6Error, match="contradicts V5"):
            v6.build_structural_frame_retention_root_service_v6()
