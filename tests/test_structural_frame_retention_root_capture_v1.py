from dataclasses import replace

import pytest

from masck_one.structural_frame_retention_root_capture_v1 import (
    StructuralFrameRetentionRootCaptureError,
    build_structural_frame_retention_root_capture_v1,
)


def test_nominal_split_retainer_has_positive_pin_shoulder_capture() -> None:
    audit = build_structural_frame_retention_root_capture_v1()
    assert audit.radial_shoulder_engagement_mm > 0.0
    assert audit.axial_groove_coverage_mm > 0.0
    assert len(audit.capture_evidence_sha256) == 64
    assert audit.accidental_release_validated is False
    assert audit.physical_validation_eligible is False
    assert audit.manifest()["capture_status"] == "NOMINAL_POSITIVE_AXIAL_CAPTURE_GEOMETRY_PROVEN"


@pytest.mark.parametrize(
    "field,value",
    [
        ("source_root_architecture_sha256", "0" * 64),
        ("source_service_v3_evidence_sha256", "1" * 64),
        ("radial_shoulder_engagement_mm", 0.0),
        ("axial_groove_coverage_mm", 0.0),
        ("capture_evidence_sha256", "2" * 64),
    ],
)
def test_capture_audit_fails_closed_on_stale_authority(field: str, value: object) -> None:
    audit = build_structural_frame_retention_root_capture_v1()
    with pytest.raises(StructuralFrameRetentionRootCaptureError):
        replace(audit, **{field: value}).validate()


def test_digital_capture_cannot_be_promoted_to_accidental_release_validation() -> None:
    audit = build_structural_frame_retention_root_capture_v1()
    with pytest.raises(StructuralFrameRetentionRootCaptureError):
        replace(audit, accidental_release_validated=True).validate()
    with pytest.raises(StructuralFrameRetentionRootCaptureError):
        replace(audit, physical_validation_eligible=True).validate()
