from dataclasses import replace

import pytest

from masck_one import structural_frame_retention_root_capture_v14 as v14


def test_v14_bounds_unequal_axial_tolerance_allocations():
    evidence = v14.build_structural_frame_retention_root_capture_v14()
    assert evidence.required_combined_tolerance_budget_mm == pytest.approx(0.08)
    assert evidence.minimum_feature_tolerance_mm == pytest.approx(0.01)
    assert evidence.clip_tolerance_min_mm == pytest.approx(0.01)
    assert evidence.clip_tolerance_max_mm == pytest.approx(0.07)
    assert evidence.groove_tolerance_min_mm == pytest.approx(0.01)
    assert evidence.groove_tolerance_max_mm == pytest.approx(0.07)
    assert evidence.allocation_span_mm == pytest.approx(0.06)
    assert evidence.nominal_geometry_unchanged is True


def test_v14_rejects_stale_v13_identity():
    evidence = v14.build_structural_frame_retention_root_capture_v14()
    with pytest.raises(v14.StructuralFrameRetentionRootCaptureV14Error, match="current V13 authority"):
        replace(evidence, source_capture_v13_sha256="0" * 64).validate()


def test_v14_rejects_nonconserving_allocation_boundary():
    evidence = v14.build_structural_frame_retention_root_capture_v14()
    with pytest.raises(v14.StructuralFrameRetentionRootCaptureV14Error):
        replace(evidence, clip_tolerance_max_mm=0.06).validate()


def test_v14_rejects_stale_allocation_span():
    evidence = v14.build_structural_frame_retention_root_capture_v14()
    with pytest.raises(v14.StructuralFrameRetentionRootCaptureV14Error):
        replace(evidence, allocation_span_mm=0.05).validate()


def test_v14_preserves_evidence_firewall():
    evidence = v14.build_structural_frame_retention_root_capture_v14()
    with pytest.raises(v14.StructuralFrameRetentionRootCaptureV14Error):
        replace(evidence, process_capability_validated=True).validate()
    with pytest.raises(v14.StructuralFrameRetentionRootCaptureV14Error):
        replace(evidence, physical_validation_eligible=True).validate()
