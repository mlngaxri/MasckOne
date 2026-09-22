from __future__ import annotations

from dataclasses import replace

import pytest

from masck_one import retention_quick_release_tactile_v27 as v27


def test_v27_binds_accepted_sampler_resolution() -> None:
    audit = v27.build_retention_quick_release_tactile_v27()
    binding = audit.manifest()["transverse_sampler_resolution_binding"]
    assert binding["aligned_radial_interval_count"] == 8
    assert binding["aligned_angular_ray_count"] == 32
    assert binding["interstitial_radial_ring_count"] == 8
    assert binding["interstitial_angular_ray_count"] == 32


def test_v27_rejects_stale_resolution_digest() -> None:
    audit = v27.build_retention_quick_release_tactile_v27()
    with pytest.raises(v27.RetentionQuickReleaseTactileV27Error, match="digest is stale"):
        replace(audit, sampler_resolution_sha256="0" * 64).validate()


def test_v27_rejects_aligned_angular_coarsening(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(v27.v16, "POLAR_ANGLES", 16)
    with pytest.raises(v27.RetentionQuickReleaseTactileV27Error, match="aligned angular resolution"):
        v27.build_retention_quick_release_tactile_v27()


def test_v27_rejects_radial_coarsening(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(v27.v16, "POLAR_RADII", tuple(index / 4.0 for index in range(5)))
    with pytest.raises(v27.RetentionQuickReleaseTactileV27Error, match="aligned radial schedule"):
        v27.build_retention_quick_release_tactile_v27()


def test_v27_rejects_interstitial_phase_drift(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(v27.v17, "ANGLE_PHASE_RAD", 0.0)
    with pytest.raises(v27.RetentionQuickReleaseTactileV27Error, match="phase no longer bisects"):
        v27.build_retention_quick_release_tactile_v27()
