from dataclasses import replace

import pytest

from masck_one import structural_frame_retention_root_capture_v11 as v11


def test_v11_binds_both_axial_tolerance_corners():
    evidence = v11.build_structural_frame_retention_root_capture_v11()
    assert evidence.minimum_axial_free_play_mm == pytest.approx(0.05)
    assert evidence.nominal_axial_free_play_mm == pytest.approx(0.15)
    assert evidence.maximum_axial_free_play_mm == pytest.approx(0.25)
    assert evidence.axial_free_play_window_mm == pytest.approx(0.20)
    assert evidence.axial_free_play_window_passes is True
    assert evidence.process_capability_validated is False
    assert evidence.physical_validation_eligible is False


def test_v11_fails_if_opposite_tolerance_corner_becomes_too_loose(monkeypatch):
    monkeypatch.setattr(v11.capture_v9, "CLIP_AXIAL_THICKNESS_BILATERAL_TOLERANCE_MM", 0.06)
    monkeypatch.setattr(v11.capture_v9, "GROOVE_WIDTH_BILATERAL_TOLERANCE_MM", 0.06)
    with pytest.raises(v11.StructuralFrameRetentionRootCaptureV11Error):
        v11.build_structural_frame_retention_root_capture_v11()


def test_v11_rejects_stale_maximum_free_play():
    evidence = v11.build_structural_frame_retention_root_capture_v11()
    stale = replace(evidence, maximum_axial_free_play_mm=evidence.maximum_axial_free_play_mm - 0.01)
    with pytest.raises(v11.StructuralFrameRetentionRootCaptureV11Error):
        stale.validate()


def test_v11_rejects_validation_promotion():
    evidence = v11.build_structural_frame_retention_root_capture_v11()
    with pytest.raises(v11.StructuralFrameRetentionRootCaptureV11Error):
        replace(evidence, physical_validation_eligible=True).validate()
