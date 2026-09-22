from dataclasses import replace

import pytest

from masck_one import retention_quick_release_tactile_v23 as v23


def test_v23_builds_and_binds_all_interior_grid_clearance_families():
    audit = v23.build_retention_quick_release_tactile_v23()
    assert audit.bound_family_count == 4
    assert audit.bound_pose_count > 0
    assert audit.maximum_bound_intersection_mm3 >= 0.0
    assert len(audit.clearance_evidence_sha256) == 64
    manifest = audit.manifest()["sixteenth_grid_clearance_evidence_binding"]
    assert manifest["families"] == list(v23._FAMILIES)
    assert manifest["bound_pose_count"] == audit.bound_pose_count


def test_v23_binds_the_actual_v18_midpoint_manifest_key():
    audit = v23.build_retention_quick_release_tactile_v23()
    upstream = audit.prior.prior.manifest()
    assert "interstitial_release_travel_screen" in upstream
    assert "midpoint_release_travel_screen" not in upstream
    assert v23._FAMILIES[0] == "interstitial_release_travel_screen"


def test_v23_rejects_stale_pose_count():
    audit = v23.build_retention_quick_release_tactile_v23()
    with pytest.raises(v23.RetentionQuickReleaseTactileV23Error, match="pose count"):
        replace(audit, bound_pose_count=audit.bound_pose_count + 1).validate()


def test_v23_rejects_stale_digest():
    audit = v23.build_retention_quick_release_tactile_v23()
    with pytest.raises(v23.RetentionQuickReleaseTactileV23Error, match="digest"):
        replace(audit, clearance_evidence_sha256="0" * 64).validate()


def test_v23_rejects_missing_evidence_family(monkeypatch):
    audit = v23.build_retention_quick_release_tactile_v23()
    original = audit.prior.prior.manifest

    def incomplete_manifest():
        payload = original()
        payload.pop("sixteenth_release_travel_screen")
        return payload

    monkeypatch.setattr(type(audit.prior.prior), "manifest", lambda self: incomplete_manifest())
    with pytest.raises(v23.RetentionQuickReleaseTactileV23Error, match="missing clearance evidence family"):
        audit.validate()
