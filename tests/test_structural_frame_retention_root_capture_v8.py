from dataclasses import replace
import pytest

from masck_one.structural_frame_retention_root_capture_v8 import (
    StructuralFrameRetentionRootCaptureV8Error,
    build_structural_frame_retention_root_capture_v8,
)
from masck_one import structural_frame_retention_root_capture_v8 as capture_v8


def test_v8_preserves_positive_worst_case_margins():
    v8 = build_structural_frame_retention_root_capture_v8()
    assert v8.worst_case_stack_passes is True
    assert v8.worst_transition_margin_mm > 0.0
    assert v8.worst_radial_capture_margin_mm > 0.0
    assert v8.process_capability_validated is False
    assert v8.physical_validation_eligible is False


def test_v8_rejects_stale_v7_authority():
    v8 = build_structural_frame_retention_root_capture_v8()
    with pytest.raises(StructuralFrameRetentionRootCaptureV8Error):
        replace(v8, source_capture_v7_sha256="0" * 64).validate()


def test_v8_rejects_changed_worst_case_stack():
    v8 = build_structural_frame_retention_root_capture_v8()
    with pytest.raises(StructuralFrameRetentionRootCaptureV8Error):
        replace(v8, worst_transition_margin_mm=v8.worst_transition_margin_mm + 0.001).validate()


def test_v8_binds_each_interval_to_its_own_feature_tolerance(monkeypatch):
    """Unequal future allocations must not inherit the throat tolerance by accident."""
    real = capture_v8.capture_v7.build_structural_frame_retention_root_capture_v7()
    unequal = replace(
        real,
        throat_width_bilateral_tolerance_mm=0.010,
        clip_bore_diameter_bilateral_tolerance_mm=0.020,
        pin_diameter_bilateral_tolerance_mm=0.030,
    )
    monkeypatch.setattr(capture_v8.capture_v7, "build_structural_frame_retention_root_capture_v7", lambda: unequal)
    v2 = capture_v8.capture_v2.build_structural_frame_retention_root_capture_v2()
    intervals = capture_v8._intervals()
    assert intervals[0] == round(v2.retainer_throat_width_mm - 0.010, 12)
    assert intervals[2] == round(2.0 * v2.retainer_inner_radius_mm - 0.020, 12)
    assert intervals[4] == round(v2.pin_diameter_mm - 0.030, 12)
    assert intervals[6] == round((v2.retainer_throat_width_mm - 0.010 - (2.0 * v2.retainer_inner_radius_mm + 0.020)) / 2.0, 12)
    assert intervals[7] == round((v2.pin_diameter_mm - 0.030) - (v2.retainer_throat_width_mm + 0.010), 12)


def test_v8_rejects_validation_promotion():
    v8 = build_structural_frame_retention_root_capture_v8()
    with pytest.raises(StructuralFrameRetentionRootCaptureV8Error):
        replace(v8, process_capability_validated=True).validate()
    with pytest.raises(StructuralFrameRetentionRootCaptureV8Error):
        replace(v8, physical_validation_eligible=True).validate()
