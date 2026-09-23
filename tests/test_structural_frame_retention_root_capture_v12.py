from dataclasses import replace

import pytest

from masck_one import structural_frame_retention_root_capture_v12 as v12


def test_v12_binds_positive_capture_and_maximum_axial_free_play():
    evidence = v12.build_structural_frame_retention_root_capture_v12()
    assert evidence.governing_positive_margin_mm == pytest.approx(0.05)
    assert evidence.maximum_axial_free_play_mm == pytest.approx(0.25)
    assert evidence.maximum_axial_free_play_limit_mm == pytest.approx(0.25)
    assert evidence.axial_free_play_headroom_mm == pytest.approx(0.0)
    assert evidence.complete_capture_closure_passes is True
    assert evidence.process_capability_validated is False
    assert evidence.physical_validation_eligible is False


def test_v12_rejects_stale_v10_authority():
    evidence = v12.build_structural_frame_retention_root_capture_v12()
    with pytest.raises(v12.StructuralFrameRetentionRootCaptureV12Error):
        replace(evidence, source_capture_v10_sha256="0" * 64).validate()


def test_v12_rejects_stale_v11_authority():
    evidence = v12.build_structural_frame_retention_root_capture_v12()
    with pytest.raises(v12.StructuralFrameRetentionRootCaptureV12Error):
        replace(evidence, source_capture_v11_sha256="0" * 64).validate()


def test_v12_fails_if_maximum_free_play_exceeds_bound(monkeypatch):
    monkeypatch.setattr(v12.capture_v11, "MAX_WORST_CASE_AXIAL_FREE_PLAY_MM", 0.24)
    with pytest.raises(v12.capture_v11.StructuralFrameRetentionRootCaptureV11Error):
        v12.build_structural_frame_retention_root_capture_v12()


def test_v12_rejects_validation_promotion():
    evidence = v12.build_structural_frame_retention_root_capture_v12()
    with pytest.raises(v12.StructuralFrameRetentionRootCaptureV12Error):
        replace(evidence, process_capability_validated=True).validate()
