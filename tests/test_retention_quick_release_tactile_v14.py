from __future__ import annotations

from dataclasses import replace

import pytest

from masck_one import retention_quick_release_tactile_v14 as v14


def test_v14_binds_every_sampled_clearance_pose():
    candidate = v14.build_retention_quick_release_tactile_v14()
    assert candidate.sampled_pose_count == candidate.prior.prior.prior.total_pose_count
    assert candidate.max_rigid_guide_intersection_mm3 >= 0.0
    assert len(candidate.sampled_pose_evidence_sha256) == 64


def test_v14_rejects_stale_pose_digest():
    candidate = v14.build_retention_quick_release_tactile_v14()
    stale = ("0" if candidate.sampled_pose_evidence_sha256[0] != "0" else "1") + candidate.sampled_pose_evidence_sha256[1:]
    with pytest.raises(v14.RetentionQuickReleaseTactileV14Error, match="digest is stale"):
        replace(candidate, sampled_pose_evidence_sha256=stale).validate()


@pytest.mark.parametrize("digest", ["a" * 63, "A" * 64, "g" * 64, "a" * 63 + "\n"])
def test_v14_rejects_noncanonical_digest(digest: str):
    candidate = v14.build_retention_quick_release_tactile_v14()
    with pytest.raises(v14.RetentionQuickReleaseTactileV14Error, match="canonical lowercase SHA-256"):
        replace(candidate, sampled_pose_evidence_sha256=digest).validate()


def test_v14_rejects_stale_pose_count_and_maximum():
    candidate = v14.build_retention_quick_release_tactile_v14()
    with pytest.raises(v14.RetentionQuickReleaseTactileV14Error, match="pose count is stale"):
        replace(candidate, sampled_pose_count=candidate.sampled_pose_count - 1).validate()
    with pytest.raises(v14.RetentionQuickReleaseTactileV14Error, match="maximum intersection is stale"):
        replace(candidate, max_rigid_guide_intersection_mm3=candidate.max_rigid_guide_intersection_mm3 + 0.01).validate()


def test_v14_manifest_keeps_evidence_firewall():
    manifest = v14.build_retention_quick_release_tactile_v14().manifest()
    evidence = manifest["sampled_clearance_pose_evidence"]
    assert manifest["schema"] == v14.SCHEMA
    assert "EVERY_V8_TRANSVERSE_BY_V11_TRAVEL_POSE" in evidence["criterion"]
    assert "NOT_CONTINUOUS_PROOF" in evidence["scope"]
    assert manifest["physical_validation_eligible"] is False
