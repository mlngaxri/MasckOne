from dataclasses import replace

import pytest

from masck_one import structural_frame_retention_root_service_v7 as v7


def test_v7_binds_all_pairwise_clearances_and_crossed_symmetry():
    audit = v7.build_structural_frame_retention_root_service_v7()
    assert len(audit.pairwise_clearances_mm) == 4
    assert min(distance for _, distance in audit.pairwise_clearances_mm) >= v7.v6.MIN_BREP_SERVICE_CLEARANCE_MM
    distances = dict(audit.pairwise_clearances_mm)
    assert abs(
        distances["left_pin_withdraw_vs_right_clip_install"]
        - distances["left_clip_install_vs_right_pin_withdraw"]
    ) <= v7.SYMMETRY_TOLERANCE_MM
    assert audit.physical_validation_eligible is False
    assert audit.manifest()["whole_head_removal_status"] == "OPEN"


def test_v7_rejects_stale_v6_provenance():
    audit = v7.build_structural_frame_retention_root_service_v7()
    with pytest.raises(v7.StructuralFrameRetentionRootServiceV7Error, match="source V6"):
        replace(audit, source_v6_evidence_sha256="0" * 64).validate()


def test_v7_rejects_stale_pairwise_records_and_digest():
    audit = v7.build_structural_frame_retention_root_service_v7()
    records = list(audit.pairwise_clearances_mm)
    label, distance = records[0]
    records[0] = (label, distance + 0.01)
    with pytest.raises(v7.StructuralFrameRetentionRootServiceV7Error, match="evidence is stale"):
        replace(audit, pairwise_clearances_mm=tuple(records)).validate()
    with pytest.raises(v7.StructuralFrameRetentionRootServiceV7Error, match="digest"):
        replace(audit, pairwise_evidence_sha256="f" * 64).validate()


def test_v7_rejects_crossed_asymmetry(monkeypatch):
    values = iter((10.0, 10.0, 5.0, 5.01))
    monkeypatch.setattr(v7.v6, "_brep_distance", lambda first, second: next(values))
    with pytest.raises(v7.StructuralFrameRetentionRootServiceV7Error, match="mirror-equivalent"):
        v7._pairwise_evidence()


def test_v7_rejects_physical_validation_promotion():
    audit = v7.build_structural_frame_retention_root_service_v7()
    with pytest.raises(v7.StructuralFrameRetentionRootServiceV7Error, match="not physical"):
        replace(audit, physical_validation_eligible=True).validate()
