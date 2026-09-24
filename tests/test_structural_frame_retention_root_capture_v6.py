from dataclasses import replace

import pytest

from masck_one.structural_frame_retention_root_capture_v6 import (
    StructuralFrameRetentionRootCaptureV6Error,
    build_structural_frame_retention_root_capture_v6,
)


def test_capture_v6_exposes_governing_aggregate_dimensional_budget() -> None:
    audit = build_structural_frame_retention_root_capture_v6()
    assert audit.transition_combined_error_budget_mm == pytest.approx(0.135)
    assert audit.radial_escape_combined_error_budget_mm == pytest.approx(0.27)
    assert audit.governing_combined_error_budget_mm == pytest.approx(0.135)
    assert audit.governing_budget_fraction_of_throat == pytest.approx(0.135 / 2.43)
    assert audit.manufacturing_tolerance_allocation_required is True
    assert audit.process_capability_validated is False
    assert audit.physical_validation_eligible is False
    assert audit.manifest()["budget_status"] == "AGGREGATE_BOUND_ONLY_TOLERANCE_ALLOCATION_REQUIRED"


@pytest.mark.parametrize(
    "field,value",
    [
        ("source_capture_v5_sha256", "0" * 64),
        ("transition_combined_error_budget_mm", 0.134),
        ("radial_escape_combined_error_budget_mm", 0.269),
        ("governing_combined_error_budget_mm", 0.134),
        ("governing_budget_fraction_of_throat", 0.05),
        ("evidence_sha256", "1" * 64),
        ("manufacturing_tolerance_allocation_required", False),
    ],
)
def test_capture_v6_fails_closed_on_stale_or_waived_budget_evidence(field: str, value: object) -> None:
    audit = build_structural_frame_retention_root_capture_v6()
    with pytest.raises(StructuralFrameRetentionRootCaptureV6Error):
        replace(audit, **{field: value}).validate()


@pytest.mark.parametrize("field", ["process_capability_validated", "physical_validation_eligible"])
def test_capture_v6_cannot_promote_aggregate_budget(field: str) -> None:
    audit = build_structural_frame_retention_root_capture_v6()
    with pytest.raises(StructuralFrameRetentionRootCaptureV6Error):
        replace(audit, **{field: True}).validate()
