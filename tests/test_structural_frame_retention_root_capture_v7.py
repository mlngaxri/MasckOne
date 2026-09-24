from dataclasses import replace

import pytest

from masck_one.structural_frame_retention_root_capture_v7 import (
    StructuralFrameRetentionRootCaptureV7Error,
    build_structural_frame_retention_root_capture_v7,
)


def test_capture_v7_allocates_feature_tolerances_with_two_x_geometric_reserve() -> None:
    audit = build_structural_frame_retention_root_capture_v7()
    assert audit.throat_width_bilateral_tolerance_mm == pytest.approx(0.0675)
    assert audit.clip_bore_diameter_bilateral_tolerance_mm == pytest.approx(0.0675)
    assert audit.pin_diameter_bilateral_tolerance_mm == pytest.approx(0.0675)
    assert audit.transition_budget_consumed_mm == pytest.approx(0.0675)
    assert audit.transition_budget_reserve_mm == pytest.approx(0.0675)
    assert audit.radial_escape_budget_consumed_mm == pytest.approx(0.135)
    assert audit.radial_escape_budget_reserve_mm == pytest.approx(0.135)
    assert audit.geometric_reserve_factor == pytest.approx(2.0)
    assert audit.process_capability_validated is False
    assert audit.physical_validation_eligible is False
    assert audit.manifest()["allocation_status"] == "DRAWING_TARGET_WITH_GEOMETRIC_RESERVE_PROCESS_CAPABILITY_REQUIRED"


@pytest.mark.parametrize(
    "field,value",
    [
        ("source_capture_v6_sha256", "0" * 64),
        ("throat_width_bilateral_tolerance_mm", 0.068),
        ("clip_bore_diameter_bilateral_tolerance_mm", 0.068),
        ("pin_diameter_bilateral_tolerance_mm", 0.068),
        ("transition_budget_reserve_mm", 0.06),
        ("radial_escape_budget_reserve_mm", 0.12),
        ("geometric_reserve_factor", 1.9),
        ("evidence_sha256", "1" * 64),
        ("drawing_tolerance_allocation_defined", False),
    ],
)
def test_capture_v7_fails_closed_on_stale_or_waived_allocation(field: str, value: object) -> None:
    audit = build_structural_frame_retention_root_capture_v7()
    with pytest.raises(StructuralFrameRetentionRootCaptureV7Error):
        replace(audit, **{field: value}).validate()


@pytest.mark.parametrize("field", ["process_capability_validated", "physical_validation_eligible"])
def test_capture_v7_cannot_promote_drawing_target(field: str) -> None:
    audit = build_structural_frame_retention_root_capture_v7()
    with pytest.raises(StructuralFrameRetentionRootCaptureV7Error):
        replace(audit, **{field: True}).validate()
