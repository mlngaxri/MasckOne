import pytest

from masck_one import structural_frame_retention_root_capture_v17 as v17


def test_equal_allocation_enumerates_all_physical_size_corners() -> None:
    result = v17.enumerate_axial_tolerance_corners(0.04, 0.04)
    assert result.clearances_mm == (0.15, 0.07, 0.23, 0.15)
    assert result.minimum_clearance_mm == 0.07
    assert result.maximum_free_play_mm == 0.23


def test_unequal_allocations_keep_same_adverse_extrema_but_change_mixed_corners() -> None:
    left = v17.enumerate_axial_tolerance_corners(0.01, 0.07)
    right = v17.enumerate_axial_tolerance_corners(0.07, 0.01)
    assert (left.minimum_clearance_mm, left.maximum_free_play_mm) == (0.07, 0.23)
    assert (right.minimum_clearance_mm, right.maximum_free_play_mm) == (0.07, 0.23)
    assert left.clearances_mm != right.clearances_mm


def test_corner_sweep_inherits_v16_fail_closed_budget_gate() -> None:
    with pytest.raises(ValueError, match="conserve"):
        v17.enumerate_axial_tolerance_corners(0.03, 0.04)


def test_corner_sweep_inherits_v16_envelope_gate() -> None:
    with pytest.raises(ValueError, match="outside"):
        v17.enumerate_axial_tolerance_corners(0.0, 0.08)
