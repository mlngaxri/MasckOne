from __future__ import annotations

from dataclasses import replace

import pytest

from masck_one import retention_quick_release_tactile_v12 as v12
from masck_one import retention_quick_release_tactile_v17 as v17


def test_v17_screens_interstitial_cells_through_release_schedule():
    candidate = v17.build_retention_quick_release_tactile_v17()
    assert candidate.interstitial_sample_count > 0
    assert candidate.pose_count == candidate.interstitial_sample_count * len(v12._canonical_positions())
    assert candidate.max_rigid_guide_intersection_mm3 >= 0.0
    assert len(candidate.evidence_sha256) == 64


def test_v17_samples_are_phase_shifted_and_radially_interstitial():
    candidate = v17.build_retention_quick_release_tactile_v17()
    mechanism = candidate.prior.prior.prior.prior.prior.prior.mechanism
    samples = v17._interstitial_samples(mechanism.rail_radial_clearance_mm, mechanism.anti_rotation_side_clearance_mm)
    assert all(0.0 < (y * y + z * z) ** 0.5 < mechanism.rail_radial_clearance_mm for y, z in samples)
    assert v17.ANGLE_PHASE_RAD > 0.0
    assert all(fraction not in candidate.prior.manifest()["dense_full_declared_transverse_clearance_screen"]["polar_radii"] for fraction in v17.INTERSTITIAL_RADII)


def test_v17_rejects_stale_counts_and_evidence():
    candidate = v17.build_retention_quick_release_tactile_v17()
    with pytest.raises(v17.RetentionQuickReleaseTactileV17Error, match="sample count is stale"):
        replace(candidate, interstitial_sample_count=candidate.interstitial_sample_count - 1).validate()
    with pytest.raises(v17.RetentionQuickReleaseTactileV17Error, match="pose count is stale"):
        replace(candidate, pose_count=candidate.pose_count - 1).validate()
    with pytest.raises(v17.RetentionQuickReleaseTactileV17Error, match="maximum intersection is stale"):
        replace(candidate, max_rigid_guide_intersection_mm3=candidate.max_rigid_guide_intersection_mm3 + 0.01).validate()
    stale = ("0" if candidate.evidence_sha256[0] != "0" else "1") + candidate.evidence_sha256[1:]
    with pytest.raises(v17.RetentionQuickReleaseTactileV17Error, match="digest is stale"):
        replace(candidate, evidence_sha256=stale).validate()
    with pytest.raises(v17.RetentionQuickReleaseTactileV17Error, match="canonical lowercase SHA-256"):
        replace(candidate, evidence_sha256="A" * 64).validate()


def test_v17_manifest_preserves_physical_validation_firewall():
    manifest = v17.build_retention_quick_release_tactile_v17().manifest()
    evidence = manifest["interstitial_full_declared_transverse_clearance_screen"]
    assert manifest["schema"] == v17.SCHEMA
    assert evidence["angular_rays"] == 32
    assert len(evidence["radial_midpoints"]) == 8
    assert "NOT_CONTINUOUS_SWEPT_VOLUME" in evidence["scope"]
    assert manifest["physical_validation_eligible"] is False
