from dataclasses import replace

import pytest

from masck_one import retention_quick_release_tactile_v24 as v24


def test_v24_builds_and_cross_binds_station_pose_contract():
    audit = v24.build_retention_quick_release_tactile_v24()
    assert audit.bound_station_count > 0
    assert audit.bound_pose_count == audit.prior.bound_pose_count
    assert len(audit.station_evidence_sha256) == 64
    manifest = audit.manifest()["travel_station_clearance_cross_binding"]
    assert manifest["bound_station_count"] == audit.bound_station_count
    assert manifest["bound_pose_count"] == audit.bound_pose_count


def test_v24_rejects_stale_bound_station_count():
    audit = v24.build_retention_quick_release_tactile_v24()
    with pytest.raises(v24.RetentionQuickReleaseTactileV24Error, match="station count"):
        replace(audit, bound_station_count=audit.bound_station_count + 1).validate()


def test_v24_rejects_stale_digest():
    audit = v24.build_retention_quick_release_tactile_v24()
    with pytest.raises(v24.RetentionQuickReleaseTactileV24Error, match="digest"):
        replace(audit, station_evidence_sha256="0" * 64).validate()


def test_v24_rejects_manifest_station_drift(monkeypatch):
    audit = v24.build_retention_quick_release_tactile_v24()
    owner = type(audit.prior.prior.prior)
    original = owner.manifest

    def drifted_manifest(self):
        payload = original(self)
        evidence = dict(payload["quarter_release_travel_screen"])
        positions = list(evidence["travel_quarter_points_mm"])
        positions[0] += 1e-6
        evidence["travel_quarter_points_mm"] = positions
        payload["quarter_release_travel_screen"] = evidence
        return payload

    monkeypatch.setattr(owner, "manifest", drifted_manifest)
    with pytest.raises(v24.RetentionQuickReleaseTactileV24Error, match="authoritative schedule"):
        audit.validate()


def test_v24_rejects_pose_arithmetic_drift(monkeypatch):
    audit = v24.build_retention_quick_release_tactile_v24()
    owner = type(audit.prior.prior.prior)
    original = owner.manifest

    def drifted_manifest(self):
        payload = original(self)
        evidence = dict(payload["eighth_release_travel_screen"])
        evidence["pose_count"] += 1
        payload["eighth_release_travel_screen"] = evidence
        return payload

    monkeypatch.setattr(owner, "manifest", drifted_manifest)
    with pytest.raises(v24.RetentionQuickReleaseTactileV24Error, match="pose count"):
        audit.validate()
