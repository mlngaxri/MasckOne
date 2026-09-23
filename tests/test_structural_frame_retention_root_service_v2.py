from dataclasses import replace

import pytest

from masck_one import structural_frame_retention_root_service_v2 as v2


def test_v2_cross_side_service_packaging_is_clear() -> None:
    audit = v2.build_structural_frame_retention_root_service_v2()
    manifest = audit.manifest()
    assert audit.cross_component_max_intersection_mm3 == 0.0
    assert len(audit.cross_component_evidence_sha256) == 64
    assert manifest["whole_head_removal_status"] == "OPEN"
    assert manifest["physical_validation_eligible"] is False


def test_v2_rejects_stale_source_service_identity() -> None:
    audit = v2.build_structural_frame_retention_root_service_v2()
    with pytest.raises(v2.StructuralFrameRetentionRootServiceV2Error, match="source service architecture is stale"):
        replace(audit, source_service_sha256="0" * 64).validate()


def test_v2_rejects_positive_cross_component_collision_evidence() -> None:
    audit = v2.build_structural_frame_retention_root_service_v2()
    with pytest.raises(v2.StructuralFrameRetentionRootServiceV2Error, match="stale or colliding"):
        replace(audit, cross_component_max_intersection_mm3=0.01).validate()


def test_v2_rejects_stale_cross_component_digest() -> None:
    audit = v2.build_structural_frame_retention_root_service_v2()
    with pytest.raises(v2.StructuralFrameRetentionRootServiceV2Error, match="evidence digest is stale"):
        replace(audit, cross_component_evidence_sha256="0" * 64).validate()


def test_v2_cannot_promote_digital_geometry_to_physical_validation() -> None:
    audit = v2.build_structural_frame_retention_root_service_v2()
    with pytest.raises(v2.StructuralFrameRetentionRootServiceV2Error, match="not physical evidence"):
        replace(audit, physical_validation_eligible=True).validate()
