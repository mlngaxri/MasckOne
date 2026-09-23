from dataclasses import replace
import pytest

from masck_one.structural_frame_retention_root_capture_v8 import (
    StructuralFrameRetentionRootCaptureV8Error,
    build_structural_frame_retention_root_capture_v8,
)


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


def test_v8_rejects_validation_promotion():
    v8 = build_structural_frame_retention_root_capture_v8()
    with pytest.raises(StructuralFrameRetentionRootCaptureV8Error):
        replace(v8, process_capability_validated=True).validate()
    with pytest.raises(StructuralFrameRetentionRootCaptureV8Error):
        replace(v8, physical_validation_eligible=True).validate()
