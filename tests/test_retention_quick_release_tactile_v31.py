from dataclasses import replace

import pytest

from masck_one import retention_quick_release_tactile_v31 as v31


def test_v31_builds_and_cross_binds_v30_corner_meshes():
    audit = v31.build_retention_quick_release_tactile_v31()
    manifest = audit.manifest()["clearance_corner_mesh_integrity"]
    assert manifest["corner_count"] == 4
    assert audit.combined_unique_count == audit.aligned_unique_count + audit.interstitial_unique_count
    assert audit.combined_unique_count == audit.prior.transverse_sample_count
    assert len(audit.corner_mesh_identity_sha256) == 64


def test_v31_rejects_stale_combined_count():
    audit = v31.build_retention_quick_release_tactile_v31()
    with pytest.raises(v31.RetentionQuickReleaseTactileV31Error):
        replace(audit, combined_unique_count=audit.combined_unique_count - 1).validate()


def test_v31_rejects_stale_digest():
    audit = v31.build_retention_quick_release_tactile_v31()
    with pytest.raises(v31.RetentionQuickReleaseTactileV31Error):
        replace(audit, corner_mesh_identity_sha256="0" * 64).validate()


def test_v31_rejects_duplicate_pose_at_non_nominal_corner(monkeypatch):
    original = v31.v16._dense_samples

    def duplicate_at_max_radial(radial, side):
        samples = original(radial, side)
        if radial == v31.v1.MAX_SPOOL_RAIL_RADIAL_CLEARANCE_MM:
            return samples + (samples[0],)
        return samples

    monkeypatch.setattr(v31.v16, "_dense_samples", duplicate_at_max_radial)
    with pytest.raises(v31.RetentionQuickReleaseTactileV31Error, match="audit failed"):
        v31._corner_mesh_binding()


def test_v31_rejects_aligned_interstitial_overlap_at_max_side(monkeypatch):
    aligned = v31.v16._dense_samples
    original = v31.v17._interstitial_samples

    def overlap_at_max_side(radial, side):
        samples = original(radial, side)
        if side == v31.v1.MAX_ANTI_ROTATION_SIDE_CLEARANCE_MM:
            return samples + (aligned(radial, side)[0],)
        return samples

    monkeypatch.setattr(v31.v17, "_interstitial_samples", overlap_at_max_side)
    with pytest.raises(v31.RetentionQuickReleaseTactileV31Error, match="overlap"):
        v31._corner_mesh_binding()
