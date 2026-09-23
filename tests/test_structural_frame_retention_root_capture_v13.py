from dataclasses import replace

import pytest

from masck_one import structural_frame_retention_root_capture_v13 as v13


def test_v13_quantifies_zero_headroom_recovery_without_changing_nominal_geometry():
    evidence = v13.build_structural_frame_retention_root_capture_v13()
    assert evidence.current_headroom_mm == pytest.approx(0.0)
    assert evidence.target_headroom_mm == pytest.approx(0.02)
    assert evidence.additional_headroom_required_mm == pytest.approx(0.02)
    assert evidence.combined_bilateral_tolerance_reduction_required_mm == pytest.approx(0.02)
    assert evidence.equal_split_reduction_per_feature_mm == pytest.approx(0.01)
    assert evidence.candidate_clip_tolerance_mm == pytest.approx(0.04)
    assert evidence.candidate_groove_tolerance_mm == pytest.approx(0.04)
    assert evidence.candidate_maximum_axial_free_play_mm == pytest.approx(0.23)
    assert evidence.nominal_geometry_unchanged is True


def test_v13_rejects_stale_upstream_evidence():
    evidence = v13.build_structural_frame_retention_root_capture_v13()
    with pytest.raises(v13.StructuralFrameRetentionRootCaptureV13Error):
        replace(evidence, source_capture_v12_sha256="0" * 64).validate()


def test_v13_rejects_under_recovered_candidate():
    evidence = v13.build_structural_frame_retention_root_capture_v13()
    with pytest.raises(v13.StructuralFrameRetentionRootCaptureV13Error):
        replace(evidence, candidate_maximum_axial_free_play_mm=0.24).validate()


def test_v13_preserves_evidence_firewall():
    evidence = v13.build_structural_frame_retention_root_capture_v13()
    with pytest.raises(v13.StructuralFrameRetentionRootCaptureV13Error):
        replace(evidence, process_capability_validated=True).validate()
    with pytest.raises(v13.StructuralFrameRetentionRootCaptureV13Error):
        replace(evidence, physical_validation_eligible=True).validate()
