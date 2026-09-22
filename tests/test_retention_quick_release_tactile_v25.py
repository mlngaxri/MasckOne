from __future__ import annotations

from dataclasses import replace

import pytest

from masck_one import retention_quick_release_tactile_v16 as v16
from masck_one import retention_quick_release_tactile_v25 as v25


def test_v25_builds_and_reaches_declared_transverse_boundaries() -> None:
    audit = v25.build_retention_quick_release_tactile_v25()
    manifest = audit.manifest()["transverse_clearance_boundary_binding"]
    assert audit.bound_transverse_sample_count > 0
    assert audit.bound_boundary_quadrant_count == 4
    assert audit.bound_max_abs_y_mm == pytest.approx(0.03, abs=1e-12)
    assert audit.bound_max_abs_z_mm == pytest.approx(0.03, abs=1e-12)
    assert manifest["bound_boundary_quadrant_count"] == 4


def test_v25_rejects_stale_bound_digest() -> None:
    audit = v25.build_retention_quick_release_tactile_v25()
    with pytest.raises(v25.RetentionQuickReleaseTactileV25Error, match="digest is stale"):
        replace(audit, boundary_evidence_sha256="0" * 64).validate()


def test_v25_rejects_mesh_that_silently_shrinks_radial_boundary(monkeypatch: pytest.MonkeyPatch) -> None:
    original = v16._dense_samples

    def shrunk(radial: float, side: float):
        return original(radial * 0.9, min(side, radial * 0.9))

    monkeypatch.setattr(v16, "_dense_samples", shrunk)
    with pytest.raises(v25.RetentionQuickReleaseTactileV25Error, match="radial clearance boundary"):
        v25.build_retention_quick_release_tactile_v25()


def test_v25_rejects_loss_of_four_quadrant_boundary_coverage(monkeypatch: pytest.MonkeyPatch) -> None:
    original = v16._dense_samples

    def one_sided(radial: float, side: float):
        return tuple((y, z) for y, z in original(radial, side) if y >= -1e-12 or z >= -1e-12)

    monkeypatch.setattr(v16, "_dense_samples", one_sided)
    monkeypatch.setattr(v25.v17, "_interstitial_samples", lambda radial, side: ())
    with pytest.raises(v25.RetentionQuickReleaseTactileV25Error, match="four-quadrant symmetric"):
        v25.build_retention_quick_release_tactile_v25()
