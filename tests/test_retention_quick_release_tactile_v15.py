from __future__ import annotations

from dataclasses import replace

import pytest

from masck_one import retention_quick_release_tactile_v15 as v15


def test_v15_expands_screen_to_full_declared_transverse_clearance():
    candidate = v15.build_retention_quick_release_tactile_v15()
    mechanism = candidate.prior.prior.prior.prior.mechanism
    inherited = candidate.prior.prior.prior.prior
    assert mechanism.rail_radial_clearance_mm > inherited.radial_limit_mm
    assert mechanism.anti_rotation_side_clearance_mm > inherited.side_limit_mm
    assert candidate.full_domain_pose_count > 0
    assert candidate.full_domain_boundary_sample_count >= 4
    assert candidate.full_domain_max_rigid_guide_intersection_mm3 >= 0.0
    assert len(candidate.full_domain_evidence_sha256) == 64


def test_v15_rejects_stale_full_domain_evidence():
    candidate = v15.build_retention_quick_release_tactile_v15()
    with pytest.raises(v15.RetentionQuickReleaseTactileV15Error, match="pose count is stale"):
        replace(candidate, full_domain_pose_count=candidate.full_domain_pose_count - 1).validate()
    with pytest.raises(v15.RetentionQuickReleaseTactileV15Error, match="boundary evidence is stale"):
        replace(candidate, full_domain_boundary_sample_count=candidate.full_domain_boundary_sample_count - 1).validate()
    with pytest.raises(v15.RetentionQuickReleaseTactileV15Error, match="maximum intersection is stale"):
        replace(candidate, full_domain_max_rigid_guide_intersection_mm3=candidate.full_domain_max_rigid_guide_intersection_mm3 + 0.01).validate()


def test_v15_rejects_stale_and_noncanonical_digest():
    candidate = v15.build_retention_quick_release_tactile_v15()
    stale = ("0" if candidate.full_domain_evidence_sha256[0] != "0" else "1") + candidate.full_domain_evidence_sha256[1:]
    with pytest.raises(v15.RetentionQuickReleaseTactileV15Error, match="digest is stale"):
        replace(candidate, full_domain_evidence_sha256=stale).validate()
    with pytest.raises(v15.RetentionQuickReleaseTactileV15Error, match="canonical lowercase SHA-256"):
        replace(candidate, full_domain_evidence_sha256="A" * 64).validate()


def test_v15_manifest_keeps_evidence_firewall():
    manifest = v15.build_retention_quick_release_tactile_v15().manifest()
    evidence = manifest["full_declared_transverse_clearance_screen"]
    assert manifest["schema"] == v15.SCHEMA
    assert "FULL_DECLARED_TRANSVERSE_CLEARANCE_DOMAIN" in evidence["criterion"]
    assert "NOT_TOLERANCE_STACK_CONTINUOUS_PROOF" in evidence["scope"]
    assert manifest["physical_validation_eligible"] is False
