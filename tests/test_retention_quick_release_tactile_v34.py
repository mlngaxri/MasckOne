from dataclasses import replace

import pytest

from masck_one import retention_quick_release_tactile_v20 as v20
from masck_one import retention_quick_release_tactile_v30 as v30
from masck_one import retention_quick_release_tactile_v34 as v34


def test_v34_builds_and_halves_v33_longitudinal_gap():
    result = v34.build_retention_quick_release_tactile_v34()
    assert result.eighth_position_count == 4 * (len(v34.v12._canonical_positions()) - 1)
    assert result.pose_count == result.transverse_sample_count * result.eighth_position_count
    assert result.max_rigid_guide_intersection_mm3 == 0.0
    assert result.max_unsampled_longitudinal_interval_mm == pytest.approx(
        result.prior.max_unsampled_longitudinal_interval_mm / 2.0, abs=1e-12
    )
    assert result.manifest()["schema"] == v34.SCHEMA


def test_v34_rejects_inherited_eighth_schedule_drift(monkeypatch):
    inherited = v20._eighth_positions()
    monkeypatch.setattr(v20, "_eighth_positions", lambda: (inherited[0] + 1e-6,) + inherited[1:])
    with pytest.raises(v34.RetentionQuickReleaseTactileV34Error, match="disagrees"):
        v34._eighth_positions()


def test_v34_rejects_positive_sub_tolerance_raw_collision(monkeypatch):
    monkeypatch.setattr(v30, "_raw_intersection", lambda *_args, **_kwargs: 1e-15)
    with pytest.raises(v34.RetentionQuickReleaseTactileV34Error, match="collides"):
        v34._eighth_evidence()


def test_v34_rejects_stale_pose_count():
    result = v34.build_retention_quick_release_tactile_v34()
    with pytest.raises(v34.RetentionQuickReleaseTactileV34Error, match="pose count"):
        replace(result, pose_count=result.pose_count - 1).validate()


def test_v34_rejects_stale_digest():
    result = v34.build_retention_quick_release_tactile_v34()
    with pytest.raises(v34.RetentionQuickReleaseTactileV34Error, match="digest"):
        replace(result, evidence_sha256="0" * 64).validate()
