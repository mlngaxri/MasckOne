from dataclasses import replace

import pytest

from masck_one.structural_frame_retention_root_capture_v4 import (
    StructuralFrameRetentionRootCaptureV4Error,
    build_structural_frame_retention_root_capture_v4,
)


def test_capture_v4_exposes_positive_nominal_residual_section() -> None:
    audit = build_structural_frame_retention_root_capture_v4()
    assert audit.inner_radius_mm == pytest.approx(1.08)
    assert audit.outer_radius_mm == pytest.approx(1.90)
    assert audit.radial_annulus_mm == pytest.approx(0.82)
    assert audit.throat_side_stock_mm == pytest.approx(0.80)
    assert audit.axial_stock_mm == pytest.approx(0.75)
    assert audit.residual_section_present is True
    assert audit.manifest()["section_status"] == "POSITIVE_NOMINAL_SECTION_STRENGTH_UNVALIDATED"


@pytest.mark.parametrize(
    "field,value",
    [
        ("source_capture_v3_sha256", "0" * 64),
        ("inner_radius_mm", 1.00),
        ("outer_radius_mm", 1.80),
        ("radial_annulus_mm", 0.70),
        ("throat_side_stock_mm", 0.70),
        ("axial_stock_mm", 0.65),
        ("evidence_sha256", "1" * 64),
        ("residual_section_present", False),
    ],
)
def test_capture_v4_fails_closed_on_stale_section_evidence(field: str, value: object) -> None:
    audit = build_structural_frame_retention_root_capture_v4()
    with pytest.raises(StructuralFrameRetentionRootCaptureV4Error):
        replace(audit, **{field: value}).validate()


@pytest.mark.parametrize("field", ["strength_validated", "fatigue_validated", "physical_validation_eligible"])
def test_capture_v4_cannot_promote_geometry_to_physical_validation(field: str) -> None:
    audit = build_structural_frame_retention_root_capture_v4()
    with pytest.raises(StructuralFrameRetentionRootCaptureV4Error):
        replace(audit, **{field: True}).validate()
