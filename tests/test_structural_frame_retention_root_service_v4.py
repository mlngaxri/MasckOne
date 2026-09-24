from dataclasses import replace

import pytest

from masck_one import structural_frame_retention_root_service_v4 as v4


def test_v4_bilateral_service_corridors_are_mutually_clear() -> None:
    audit = v4.build_structural_frame_retention_root_service_v4()
    assert audit.bilateral_corridor_max_intersection_mm3 == 0.0
    assert len(audit.bilateral_corridor_evidence_sha256) == 64
    assert audit.manifest()["whole_head_removal_status"] == "OPEN"


def test_v4_rejects_stale_v3_provenance() -> None:
    audit = v4.build_structural_frame_retention_root_service_v4()
    stale = replace(audit, source_v3_evidence_sha256="0" * 64)
    with pytest.raises(v4.StructuralFrameRetentionRootServiceV4Error, match="source V3"):
        stale.validate()


def test_v4_rejects_stale_collision_evidence() -> None:
    audit = v4.build_structural_frame_retention_root_service_v4()
    stale = replace(audit, bilateral_corridor_max_intersection_mm3=0.01)
    with pytest.raises(v4.StructuralFrameRetentionRootServiceV4Error, match="stale or colliding"):
        stale.validate()


def test_v4_rejects_digest_corruption() -> None:
    audit = v4.build_structural_frame_retention_root_service_v4()
    stale = replace(audit, bilateral_corridor_evidence_sha256="f" * 64)
    with pytest.raises(v4.StructuralFrameRetentionRootServiceV4Error, match="digest"):
        stale.validate()


def test_v4_preserves_evidence_firewall() -> None:
    audit = v4.build_structural_frame_retention_root_service_v4()
    promoted = replace(audit, physical_validation_eligible=True)
    with pytest.raises(v4.StructuralFrameRetentionRootServiceV4Error, match="not physical"):
        promoted.validate()
