from dataclasses import replace

import pytest

from masck_one import retention_quick_release_tactile_v41 as v41


def test_v41_binds_clearance_corners_to_validated_mesh_authority():
    model = v41.build_retention_quick_release_tactile_v41()
    assert model.combined_unique_count == model.aligned_unique_count + model.interstitial_unique_count
    binding = model.manifest()["clearance_corner_mesh_authority_binding"]
    assert binding["criterion"] == "EXACT_CLEARANCE_CORNERS_ARE_BOUND_TO_THE_VALIDATED_TRANSVERSE_MESH_AUTHORITY"


def test_v41_rejects_stale_mesh_counts():
    model = v41.build_retention_quick_release_tactile_v41()
    with pytest.raises(v41.RetentionQuickReleaseTactileV41Error, match="counts are stale"):
        replace(model, combined_unique_count=model.combined_unique_count + 1).validate()


def test_v41_rejects_stale_mesh_identity():
    model = v41.build_retention_quick_release_tactile_v41()
    with pytest.raises(v41.RetentionQuickReleaseTactileV41Error, match="identity is stale"):
        replace(model, corner_mesh_identity_sha256="0" * 64).validate()


def test_v41_rejects_stale_binding_digest():
    model = v41.build_retention_quick_release_tactile_v41()
    with pytest.raises(v41.RetentionQuickReleaseTactileV41Error, match="binding digest is stale"):
        replace(model, corner_mesh_authority_binding_sha256="0" * 64).validate()


def test_v41_rejects_mesh_count_drift_from_collision_screen(monkeypatch):
    model = v41.build_retention_quick_release_tactile_v41()
    original = v41.v31.build_retention_quick_release_tactile_v31
    mesh = original()
    bad_prior = replace(mesh.prior, transverse_sample_count=mesh.prior.transverse_sample_count + 1)
    bad_mesh = replace(mesh, prior=bad_prior)
    monkeypatch.setattr(v41.v31, "build_retention_quick_release_tactile_v31", lambda: bad_mesh)
    with pytest.raises(v41.RetentionQuickReleaseTactileV41Error, match="count drifted"):
        v41._corner_mesh_authority_binding(model.prior)
