from dataclasses import replace

import pytest

from masck_one import retention_quick_release_tactile_v32 as v32


def test_v32_builds_and_halves_longitudinal_station_gap():
    audit = v32.build_retention_quick_release_tactile_v32()
    stations = v32.v12._canonical_positions()
    manifest = audit.manifest()["interstation_midpoint_clearance_screen"]
    assert audit.midpoint_count == len(stations) - 1
    assert audit.transverse_sample_count == audit.prior.combined_unique_count
    assert audit.pose_count == audit.transverse_sample_count * audit.midpoint_count
    assert audit.max_unsampled_longitudinal_interval_mm == pytest.approx(
        max(b - a for a, b in zip(stations, stations[1:])) / 2.0
    )
    assert manifest["max_rigid_guide_intersection_mm3"] == 0.0


def test_v32_rejects_stale_pose_count():
    audit = v32.build_retention_quick_release_tactile_v32()
    with pytest.raises(v32.RetentionQuickReleaseTactileV32Error):
        replace(audit, pose_count=audit.pose_count - 1).validate()


def test_v32_rejects_stale_digest():
    audit = v32.build_retention_quick_release_tactile_v32()
    with pytest.raises(v32.RetentionQuickReleaseTactileV32Error):
        replace(audit, evidence_sha256="0" * 64).validate()


def test_v32_rejects_non_monotonic_station_schedule(monkeypatch):
    monkeypatch.setattr(v32.v12, "_canonical_positions", lambda: (0.0, 1.0, 1.0, 2.0))
    with pytest.raises(v32.RetentionQuickReleaseTactileV32Error, match="strictly increasing"):
        v32._midpoint_positions()


def test_v32_rejects_positive_midpoint_collision(monkeypatch):
    original = v32.v30._raw_intersection
    calls = 0

    def collide_once(first, second):
        nonlocal calls
        calls += 1
        if calls == 1:
            return 1e-15
        return original(first, second)

    monkeypatch.setattr(v32.v30, "_raw_intersection", collide_once)
    with pytest.raises(v32.RetentionQuickReleaseTactileV32Error, match="collides"):
        v32._midpoint_evidence()
