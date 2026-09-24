from dataclasses import replace

import pytest

from masck_one import structural_frame_retention_root_service_v3 as v3


def test_v3_local_service_sequence_is_clear() -> None:
    audit = v3.build_structural_frame_retention_root_service_v3()
    manifest = audit.manifest()
    assert audit.local_sequence_max_intersection_mm3 == 0.0
    assert len(audit.local_sequence_evidence_sha256) == 64
    assert manifest["whole_head_removal_status"] == "OPEN"
    assert manifest["physical_validation_eligible"] is False


def test_v3_rejects_stale_v2_identity() -> None:
    audit = v3.build_structural_frame_retention_root_service_v3()
    with pytest.raises(v3.StructuralFrameRetentionRootServiceV3Error, match="source V2 service evidence is stale"):
        replace(audit, source_v2_evidence_sha256="0" * 64).validate()


def test_v3_rejects_positive_local_sequence_collision_evidence() -> None:
    audit = v3.build_structural_frame_retention_root_service_v3()
    with pytest.raises(v3.StructuralFrameRetentionRootServiceV3Error, match="stale or colliding"):
        replace(audit, local_sequence_max_intersection_mm3=0.01).validate()


def test_v3_rejects_stale_local_sequence_digest() -> None:
    audit = v3.build_structural_frame_retention_root_service_v3()
    with pytest.raises(v3.StructuralFrameRetentionRootServiceV3Error, match="evidence digest is stale"):
        replace(audit, local_sequence_evidence_sha256="0" * 64).validate()


def test_v3_cannot_promote_digital_geometry_to_physical_validation() -> None:
    audit = v3.build_structural_frame_retention_root_service_v3()
    with pytest.raises(v3.StructuralFrameRetentionRootServiceV3Error, match="not physical evidence"):
        replace(audit, physical_validation_eligible=True).validate()
