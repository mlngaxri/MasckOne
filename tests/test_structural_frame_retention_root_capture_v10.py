from dataclasses import replace

import pytest

from masck_one import structural_frame_retention_root_capture_v10 as v10


def test_v10_binds_radial_and_axial_capture_margins():
    evidence = v10.build_structural_frame_retention_root_capture_v10()
    assert evidence.worst_transition_margin_mm > 0.0
    assert evidence.worst_radial_capture_margin_mm > 0.0
    assert evidence.worst_axial_clearance_mm == pytest.approx(0.05)
    assert evidence.governing_margin_mm == pytest.approx(
        min(
            evidence.worst_transition_margin_mm,
            evidence.worst_radial_capture_margin_mm,
            evidence.worst_axial_clearance_mm,
        )
    )
    assert evidence.integrated_dimensional_closure_passes is True
    assert evidence.process_capability_validated is False
    assert evidence.physical_validation_eligible is False


def test_v10_fails_if_radial_authority_goes_stale(monkeypatch):
    original = v10.capture_v8.build_structural_frame_retention_root_capture_v8
    radial = original()
    monkeypatch.setattr(
        v10.capture_v8,
        "build_structural_frame_retention_root_capture_v8",
        lambda: replace(radial, evidence_sha256="0" * 64),
    )
    with pytest.raises(Exception):
        v10.build_structural_frame_retention_root_capture_v10()


def test_v10_fails_if_axial_stack_loses_positive_clearance(monkeypatch):
    monkeypatch.setattr(v10.capture_v9, "CLIP_AXIAL_THICKNESS_BILATERAL_TOLERANCE_MM", 0.08)
    monkeypatch.setattr(v10.capture_v9, "GROOVE_WIDTH_BILATERAL_TOLERANCE_MM", 0.08)
    with pytest.raises(Exception):
        v10.build_structural_frame_retention_root_capture_v10()


def test_v10_rejects_validation_promotion():
    evidence = v10.build_structural_frame_retention_root_capture_v10()
    promoted = replace(evidence, process_capability_validated=True)
    with pytest.raises(v10.StructuralFrameRetentionRootCaptureV10Error):
        promoted.validate()
