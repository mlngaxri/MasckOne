from dataclasses import replace

import pytest

from masck_one import retention_quick_release_tactile as v1
from masck_one.retention_quick_release_tactile_v29 import (
    RetentionQuickReleaseTactileV29Error,
    build_retention_quick_release_tactile_v29,
)


def test_v29_screens_existing_maximum_clearance_authority():
    audit = build_retention_quick_release_tactile_v29()
    manifest = audit.manifest()
    evidence = manifest["maximum_accepted_transverse_clearance_screen"]
    assert manifest["schema"] == "MASCK_ONE_RETENTION_QUICK_RELEASE_TACTILE_V29"
    assert evidence["radial_clearance_mm"] == v1.MAX_SPOOL_RAIL_RADIAL_CLEARANCE_MM
    assert evidence["anti_rotation_side_clearance_mm"] == v1.MAX_ANTI_ROTATION_SIDE_CLEARANCE_MM
    assert evidence["transverse_sample_count"] > 0
    assert evidence["pose_count"] > evidence["transverse_sample_count"]
    assert evidence["max_rigid_guide_intersection_mm3"] == 0.0
    assert len(evidence["evidence_sha256"]) == 64
    assert manifest["physical_validation_eligible"] is False


def test_v29_rejects_stale_pose_count():
    audit = build_retention_quick_release_tactile_v29()
    with pytest.raises(RetentionQuickReleaseTactileV29Error, match="pose count is stale"):
        replace(audit, pose_count=audit.pose_count - 1).validate()


def test_v29_rejects_positive_bound_intersection():
    audit = build_retention_quick_release_tactile_v29()
    with pytest.raises(RetentionQuickReleaseTactileV29Error, match="maximum intersection is stale"):
        replace(audit, max_rigid_guide_intersection_mm3=1e-6).validate()


def test_v29_rejects_stale_evidence_digest():
    audit = build_retention_quick_release_tactile_v29()
    with pytest.raises(RetentionQuickReleaseTactileV29Error, match="digest is stale"):
        replace(audit, evidence_sha256="0" * 64).validate()
