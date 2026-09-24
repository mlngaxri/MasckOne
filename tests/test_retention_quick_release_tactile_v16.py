from __future__ import annotations

from dataclasses import replace

import pytest

from masck_one import retention_quick_release_tactile_v12 as v12
from masck_one import retention_quick_release_tactile_v16 as v16


def test_v16_increases_full_domain_transverse_density():
    candidate = v16.build_retention_quick_release_tactile_v16()
    inherited_transverse = candidate.prior.full_domain_pose_count // len(v12._canonical_positions())
    assert candidate.transverse_sample_count > inherited_transverse
    assert candidate.pose_count == candidate.transverse_sample_count * len(v12._canonical_positions())
    assert candidate.boundary_sample_count >= candidate.prior.full_domain_boundary_sample_count
    assert candidate.max_rigid_guide_intersection_mm3 >= 0.0
    assert len(candidate.evidence_sha256) == 64


def test_v16_rejects_stale_dense_counts():
    candidate = v16.build_retention_quick_release_tactile_v16()
    with pytest.raises(v16.RetentionQuickReleaseTactileV16Error, match="transverse sample count is stale"):
        replace(candidate, transverse_sample_count=candidate.transverse_sample_count - 1).validate()
    with pytest.raises(v16.RetentionQuickReleaseTactileV16Error, match="pose count is stale"):
        replace(candidate, pose_count=candidate.pose_count - 1).validate()
    with pytest.raises(v16.RetentionQuickReleaseTactileV16Error, match="boundary evidence is stale"):
        replace(candidate, boundary_sample_count=candidate.boundary_sample_count - 1).validate()


def test_v16_rejects_stale_and_noncanonical_evidence():
    candidate = v16.build_retention_quick_release_tactile_v16()
    with pytest.raises(v16.RetentionQuickReleaseTactileV16Error, match="maximum intersection is stale"):
        replace(candidate, max_rigid_guide_intersection_mm3=candidate.max_rigid_guide_intersection_mm3 + 0.01).validate()
    stale = ("0" if candidate.evidence_sha256[0] != "0" else "1") + candidate.evidence_sha256[1:]
    with pytest.raises(v16.RetentionQuickReleaseTactileV16Error, match="digest is stale"):
        replace(candidate, evidence_sha256=stale).validate()
    with pytest.raises(v16.RetentionQuickReleaseTactileV16Error, match="canonical lowercase SHA-256"):
        replace(candidate, evidence_sha256="A" * 64).validate()


def test_v16_manifest_preserves_physical_validation_firewall():
    manifest = v16.build_retention_quick_release_tactile_v16().manifest()
    evidence = manifest["dense_full_declared_transverse_clearance_screen"]
    assert manifest["schema"] == v16.SCHEMA
    assert evidence["polar_angles"] == 32
    assert len(evidence["polar_radii"]) == 9
    assert "NOT_CONTINUOUS_SWEPT_VOLUME" in evidence["scope"]
    assert manifest["physical_validation_eligible"] is False
