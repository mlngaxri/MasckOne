from dataclasses import replace
from hashlib import sha256
import json

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
    assert evidence.candidate_minimum_axial_clearance_mm == pytest.approx(0.07)
    assert evidence.candidate_maximum_axial_free_play_mm == pytest.approx(0.23)
    assert evidence.nominal_geometry_unchanged is True


def test_v13_rejects_stale_upstream_evidence():
    evidence = v13.build_structural_frame_retention_root_capture_v13()
    with pytest.raises(v13.StructuralFrameRetentionRootCaptureV13Error):
        replace(evidence, source_capture_v12_sha256="0" * 64).validate()


def test_v13_rejects_stale_upstream_even_with_self_consistent_digest():
    evidence = v13.build_structural_frame_retention_root_capture_v13()
    stale_source = "0" * 64
    values = (
        evidence.current_headroom_mm,
        evidence.target_headroom_mm,
        evidence.additional_headroom_required_mm,
        evidence.combined_bilateral_tolerance_reduction_required_mm,
        evidence.equal_split_reduction_per_feature_mm,
        evidence.candidate_clip_tolerance_mm,
        evidence.candidate_groove_tolerance_mm,
        evidence.candidate_minimum_axial_clearance_mm,
        evidence.candidate_maximum_axial_free_play_mm,
    )
    payload = {
        "source_capture_v12_sha256": stale_source,
        "values": values,
        "nominal_geometry_unchanged": True,
    }
    spoofed_digest = sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()
    with pytest.raises(v13.StructuralFrameRetentionRootCaptureV13Error, match="current V12 authority"):
        replace(
            evidence,
            source_capture_v12_sha256=stale_source,
            evidence_sha256=spoofed_digest,
        ).validate()


def test_v13_rejects_under_recovered_candidate():
    evidence = v13.build_structural_frame_retention_root_capture_v13()
    with pytest.raises(v13.StructuralFrameRetentionRootCaptureV13Error):
        replace(evidence, candidate_maximum_axial_free_play_mm=0.24).validate()


def test_v13_rejects_candidate_that_loses_minimum_clearance():
    evidence = v13.build_structural_frame_retention_root_capture_v13()
    with pytest.raises(v13.StructuralFrameRetentionRootCaptureV13Error):
        replace(evidence, candidate_minimum_axial_clearance_mm=0.04).validate()


def test_v13_preserves_evidence_firewall():
    evidence = v13.build_structural_frame_retention_root_capture_v13()
    with pytest.raises(v13.StructuralFrameRetentionRootCaptureV13Error):
        replace(evidence, process_capability_validated=True).validate()
    with pytest.raises(v13.StructuralFrameRetentionRootCaptureV13Error):
        replace(evidence, physical_validation_eligible=True).validate()
