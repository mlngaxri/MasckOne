from __future__ import annotations

from dataclasses import replace

import pytest

from masck_one import retention_quick_release_tactile_v16 as v16
from masck_one import retention_quick_release_tactile_v26 as v26


def test_v26_builds_with_unique_disjoint_symmetric_meshes() -> None:
    audit = v26.build_retention_quick_release_tactile_v26()
    manifest = audit.manifest()["transverse_mesh_identity_binding"]
    assert audit.aligned_unique_count > 0
    assert audit.interstitial_unique_count > 0
    assert audit.combined_unique_count == audit.prior.bound_transverse_sample_count
    assert manifest["combined_unique_count"] == audit.combined_unique_count


def test_v26_rejects_stale_identity_digest() -> None:
    audit = v26.build_retention_quick_release_tactile_v26()
    with pytest.raises(v26.RetentionQuickReleaseTactileV26Error, match="digest is stale"):
        replace(audit, mesh_identity_sha256="0" * 64).validate()


def test_v26_rejects_duplicate_aligned_pose(monkeypatch: pytest.MonkeyPatch) -> None:
    original = v16._dense_samples

    def duplicated(radial: float, side: float):
        samples = original(radial, side)
        return samples + (samples[0],)

    monkeypatch.setattr(v16, "_dense_samples", duplicated)
    with pytest.raises(v26.RetentionQuickReleaseTactileV26Error, match="duplicate poses"):
        v26.build_retention_quick_release_tactile_v26()


def test_v26_rejects_loss_of_inversion_symmetry(monkeypatch: pytest.MonkeyPatch) -> None:
    original = v16._dense_samples

    def asymmetric(radial: float, side: float):
        samples = original(radial, side)
        return tuple(point for point in samples if point[0] >= -1e-12)

    monkeypatch.setattr(v16, "_dense_samples", asymmetric)
    with pytest.raises(v26.RetentionQuickReleaseTactileV26Error, match="inversion symmetry"):
        v26.build_retention_quick_release_tactile_v26()


def test_v26_rejects_family_overlap(monkeypatch: pytest.MonkeyPatch) -> None:
    original = v26.v17._interstitial_samples

    def overlapping(radial: float, side: float):
        return original(radial, side) + (v16._dense_samples(radial, side)[0],)

    monkeypatch.setattr(v26.v17, "_interstitial_samples", overlapping)
    with pytest.raises(v26.RetentionQuickReleaseTactileV26Error, match="meshes overlap"):
        v26.build_retention_quick_release_tactile_v26()
