import pytest

from masck_one import structural_frame_retention_root_capture_v9 as v9


def test_v9_closes_axial_clearance_at_worst_case():
    evidence = v9.build_structural_frame_retention_root_capture_v9()
    assert evidence.nominal_axial_clearance_mm == pytest.approx(0.15)
    assert evidence.clip_thickness_min_mm == pytest.approx(0.55)
    assert evidence.clip_thickness_max_mm == pytest.approx(0.65)
    assert evidence.groove_width_min_mm == pytest.approx(0.70)
    assert evidence.groove_width_max_mm == pytest.approx(0.80)
    assert evidence.worst_case_axial_clearance_mm == pytest.approx(0.05)
    assert evidence.drawing_tolerance_stack_passes is True
    assert evidence.process_capability_validated is False
    assert evidence.physical_validation_eligible is False


def test_v9_fails_if_axial_tolerance_allocation_consumes_clearance(monkeypatch):
    monkeypatch.setattr(v9, "CLIP_AXIAL_THICKNESS_BILATERAL_TOLERANCE_MM", 0.08)
    monkeypatch.setattr(v9, "GROOVE_WIDTH_BILATERAL_TOLERANCE_MM", 0.08)
    with pytest.raises(v9.StructuralFrameRetentionRootCaptureV9Error):
        v9.build_structural_frame_retention_root_capture_v9()


def test_v9_keeps_clip_and_groove_tolerances_independent(monkeypatch):
    monkeypatch.setattr(v9, "CLIP_AXIAL_THICKNESS_BILATERAL_TOLERANCE_MM", 0.02)
    monkeypatch.setattr(v9, "GROOVE_WIDTH_BILATERAL_TOLERANCE_MM", 0.03)
    evidence = v9.build_structural_frame_retention_root_capture_v9()
    assert evidence.clip_thickness_min_mm == pytest.approx(0.58)
    assert evidence.clip_thickness_max_mm == pytest.approx(0.62)
    assert evidence.groove_width_min_mm == pytest.approx(0.72)
    assert evidence.groove_width_max_mm == pytest.approx(0.78)
    assert evidence.worst_case_axial_clearance_mm == pytest.approx(0.10)


def test_v9_rejects_validation_promotion():
    evidence = v9.build_structural_frame_retention_root_capture_v9()
    with pytest.raises(v9.StructuralFrameRetentionRootCaptureV9Error):
        v9.StructuralFrameRetentionRootCaptureV9(
            evidence.source_capture_v2_sha256,
            evidence.clip_thickness_min_mm,
            evidence.clip_thickness_max_mm,
            evidence.groove_width_min_mm,
            evidence.groove_width_max_mm,
            evidence.worst_case_axial_clearance_mm,
            evidence.nominal_axial_clearance_mm,
            evidence.evidence_sha256,
            True,
            True,
            False,
        ).validate()
