from dataclasses import replace

import pytest

from masck_one import structural_frame_retention_root_capture_v15 as v15


def test_v15_proves_allocation_boundaries_preserve_axial_corners():
    evidence = v15.build_structural_frame_retention_root_capture_v15()
    assert evidence.nominal_axial_clearance_mm == pytest.approx(0.15)
    assert evidence.allocation_budget_mm == pytest.approx(0.08)
    assert evidence.clip_min_allocation_min_clearance_mm == pytest.approx(0.07)
    assert evidence.clip_min_allocation_max_free_play_mm == pytest.approx(0.23)
    assert evidence.clip_max_allocation_min_clearance_mm == pytest.approx(0.07)
    assert evidence.clip_max_allocation_max_free_play_mm == pytest.approx(0.23)
    assert evidence.allocation_corner_spread_mm == pytest.approx(0.0)


def test_v15_rejects_stale_v14_identity():
    evidence = v15.build_structural_frame_retention_root_capture_v15()
    with pytest.raises(v15.StructuralFrameRetentionRootCaptureV15Error, match="current V14 authority"):
        replace(evidence, source_capture_v14_sha256="0" * 64).validate()


def test_v15_rejects_allocation_dependent_corner_drift():
    evidence = v15.build_structural_frame_retention_root_capture_v15()
    with pytest.raises(v15.StructuralFrameRetentionRootCaptureV15Error):
        replace(evidence, clip_max_allocation_max_free_play_mm=0.24).validate()


def test_v15_rejects_lost_v13_corner_authority():
    evidence = v15.build_structural_frame_retention_root_capture_v15()
    with pytest.raises(v15.StructuralFrameRetentionRootCaptureV15Error):
        replace(evidence, clip_min_allocation_min_clearance_mm=0.06).validate()


def test_v15_preserves_evidence_firewall():
    evidence = v15.build_structural_frame_retention_root_capture_v15()
    with pytest.raises(v15.StructuralFrameRetentionRootCaptureV15Error):
        replace(evidence, process_capability_validated=True).validate()
    with pytest.raises(v15.StructuralFrameRetentionRootCaptureV15Error):
        replace(evidence, physical_validation_eligible=True).validate()
