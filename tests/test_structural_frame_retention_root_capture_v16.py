import pytest

from masck_one.structural_frame_retention_root_capture_v16 import (
    StructuralFrameRetentionRootCaptureV16Error,
    evaluate_axial_tolerance_allocation,
)


def test_equal_split_preserves_v13_stack_corners() -> None:
    result = evaluate_axial_tolerance_allocation(0.04, 0.04)
    assert result.minimum_clearance_mm == 0.07
    assert result.maximum_free_play_mm == 0.23


def test_unequal_feasible_allocations_preserve_stack_corners() -> None:
    for clip, groove in ((0.01, 0.07), (0.025, 0.055), (0.07, 0.01)):
        result = evaluate_axial_tolerance_allocation(clip, groove)
        assert result.minimum_clearance_mm == 0.07
        assert result.maximum_free_play_mm == 0.23


def test_rejects_budget_drift_even_when_each_feature_is_individually_in_range() -> None:
    with pytest.raises(StructuralFrameRetentionRootCaptureV16Error, match="conserve"):
        evaluate_axial_tolerance_allocation(0.03, 0.04)


def test_rejects_out_of_envelope_allocations() -> None:
    with pytest.raises(StructuralFrameRetentionRootCaptureV16Error, match="clip tolerance"):
        evaluate_axial_tolerance_allocation(0.0, 0.08)
    with pytest.raises(StructuralFrameRetentionRootCaptureV16Error, match="groove tolerance"):
        evaluate_axial_tolerance_allocation(0.08, 0.0)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -float("inf"), True])
def test_rejects_non_finite_or_non_numeric_like_values(bad) -> None:
    with pytest.raises(StructuralFrameRetentionRootCaptureV16Error):
        evaluate_axial_tolerance_allocation(bad, 0.04)
