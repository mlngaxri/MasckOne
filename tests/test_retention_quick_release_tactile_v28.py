from dataclasses import replace

import pytest

from masck_one import retention_quick_release_tactile_v16 as v16
from masck_one import retention_quick_release_tactile_v17 as v17
from masck_one.retention_quick_release_tactile_v28 import (
    RetentionQuickReleaseTactileV28Error,
    build_retention_quick_release_tactile_v28,
)


def test_v28_binds_realized_meshes_to_v27_schedule():
    audit = build_retention_quick_release_tactile_v28()
    manifest = audit.manifest()
    binding = manifest["transverse_sampler_implementation_binding"]
    assert manifest["schema"] == "MASCK_ONE_RETENTION_QUICK_RELEASE_TACTILE_V28"
    assert binding["aligned_bound_count"] > 0
    assert binding["interstitial_bound_count"] > 0
    assert len(binding["implementation_binding_sha256"]) == 64
    assert manifest["physical_validation_eligible"] is False


def test_v28_rejects_aligned_sampler_drift_even_if_constants_are_unchanged(monkeypatch):
    original = v16._dense_samples

    def drifted(radial: float, side: float):
        samples = list(original(radial, side))
        y, z = samples[1]
        samples[1] = (y * 0.999, z)
        return tuple(samples)

    monkeypatch.setattr(v16, "_dense_samples", drifted)
    with pytest.raises(RetentionQuickReleaseTactileV28Error, match="aligned mesh"):
        build_retention_quick_release_tactile_v28()


def test_v28_rejects_interstitial_sampler_drift_even_if_constants_are_unchanged(monkeypatch):
    original = v17._interstitial_samples

    def drifted(radial: float, side: float):
        samples = list(original(radial, side))
        y, z = samples[0]
        samples[0] = (y, z * 0.999)
        return tuple(samples)

    monkeypatch.setattr(v17, "_interstitial_samples", drifted)
    with pytest.raises(RetentionQuickReleaseTactileV28Error, match="interstitial mesh"):
        build_retention_quick_release_tactile_v28()


def test_v28_rejects_stale_binding_digest():
    audit = build_retention_quick_release_tactile_v28()
    with pytest.raises(RetentionQuickReleaseTactileV28Error, match="digest is stale"):
        replace(audit, implementation_binding_sha256="0" * 64).validate()
