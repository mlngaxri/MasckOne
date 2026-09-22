from dataclasses import replace

import pytest

from masck_one import retention_quick_release_tactile_v33 as v33


def test_v33_builds_and_quarters_corner_screen_gap():
    audit = v33.build_retention_quick_release_tactile_v33()
    stations = v33.v12._canonical_positions()
    manifest = audit.manifest()["quarter_travel_clearance_corner_screen"]
    assert audit.quarter_position_count == 2 * (len(stations) - 1)
    assert audit.transverse_sample_count == audit.prior.transverse_sample_count
    assert audit.pose_count == audit.transverse_sample_count * audit.quarter_position_count
    assert audit.max_unsampled_longitudinal_interval_mm == pytest.approx(
        max(b-a for a, b in zip(stations, stations[1:])) / 4.0
    )
    assert manifest["max_rigid_guide_intersection_mm3"] == 0.0


def test_v33_rejects_stale_pose_count():
    audit = v33.build_retention_quick_release_tactile_v33()
    with pytest.raises(v33.RetentionQuickReleaseTactileV33Error):
        replace(audit, pose_count=audit.pose_count - 1).validate()


def test_v33_rejects_stale_digest():
    audit = v33.build_retention_quick_release_tactile_v33()
    with pytest.raises(v33.RetentionQuickReleaseTactileV33Error):
        replace(audit, evidence_sha256="0" * 64).validate()


def test_v33_rejects_drift_from_v19_quarter_authority(monkeypatch):
    inherited = v33.v19._quarter_positions()
    monkeypatch.setattr(v33.v19, "_quarter_positions", lambda: (inherited[0] + 1e-4,) + inherited[1:])
    with pytest.raises(v33.RetentionQuickReleaseTactileV33Error, match="V19 authority"):
        v33._quarter_positions()


def test_v33_rejects_positive_quarter_collision(monkeypatch):
    original = v33.v30._raw_intersection
    calls = 0

    def collide_once(first, second):
        nonlocal calls
        calls += 1
        if calls == 1:
            return 1e-15
        return original(first, second)

    monkeypatch.setattr(v33.v30, "_raw_intersection", collide_once)
    with pytest.raises(v33.RetentionQuickReleaseTactileV33Error, match="collides"):
        v33._quarter_evidence()
