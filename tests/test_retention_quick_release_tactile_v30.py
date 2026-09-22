from dataclasses import replace
import pytest
from masck_one import retention_quick_release_tactile_v30 as v30


def test_v30_builds_and_binds_all_clearance_corners():
    audit = v30.build_retention_quick_release_tactile_v30()
    manifest = audit.manifest()["clearance_authority_corner_screen"]
    assert manifest["corner_count"] == 4
    assert audit.pose_count == audit.transverse_sample_count * len(v30.v12._canonical_positions())
    assert audit.max_rigid_guide_intersection_mm3 <= v30.v1.TOL_MM3
    assert len(audit.evidence_sha256) == 64


def test_v30_rejects_stale_pose_count():
    audit = v30.build_retention_quick_release_tactile_v30()
    with pytest.raises(v30.RetentionQuickReleaseTactileV30Error):
        replace(audit, pose_count=audit.pose_count + 1).validate()


def test_v30_rejects_stale_digest():
    audit = v30.build_retention_quick_release_tactile_v30()
    with pytest.raises(v30.RetentionQuickReleaseTactileV30Error):
        replace(audit, evidence_sha256="0" * 64).validate()


def test_v30_rejects_positive_bound_intersection():
    audit = v30.build_retention_quick_release_tactile_v30()
    with pytest.raises(v30.RetentionQuickReleaseTactileV30Error):
        replace(audit, max_rigid_guide_intersection_mm3=v30.v1.TOL_MM3 + 1e-9).validate()


def test_v30_corner_authority_is_complete():
    mechanism = v30.v1.build_retention_quick_release_tactile()
    corners = v30._clearance_corners(mechanism)
    assert [name for name, _, _ in corners] == ["nominal_nominal", "nominal_max_side", "max_radial_nominal", "max_max"]
    assert len({(radial, side) for _, radial, side in corners}) == 4
