from dataclasses import replace

import pytest

from masck_one import retention_quick_release_tactile_v21 as v21
from masck_one import retention_quick_release_tactile_v30 as v30
from masck_one import retention_quick_release_tactile_v35 as v35


def test_v35_builds_and_halves_v34_longitudinal_gap():
    result = v35.build_retention_quick_release_tactile_v35()
    assert result.sixteenth_position_count == 8 * (len(v35.v12._canonical_positions()) - 1)
    assert result.pose_count == result.transverse_sample_count * result.sixteenth_position_count
    assert result.max_rigid_guide_intersection_mm3 == 0.0
    assert result.max_unsampled_longitudinal_interval_mm == pytest.approx(
        result.prior.max_unsampled_longitudinal_interval_mm / 2.0, abs=1e-12
    )
    assert result.manifest()["schema"] == v35.SCHEMA


def test_v35_rejects_inherited_sixteenth_schedule_drift(monkeypatch):
    inherited = v21._sixteenth_positions()
    monkeypatch.setattr(v21, "_sixteenth_positions", lambda: (inherited[0] + 1e-6,) + inherited[1:])
    with pytest.raises(v35.RetentionQuickReleaseTactileV35Error, match="disagrees"):
        v35._sixteenth_positions()


def test_v35_rejects_positive_sub_tolerance_raw_collision(monkeypatch):
    monkeypatch.setattr(v30, "_raw_intersection", lambda *_args, **_kwargs: 1e-15)
    with pytest.raises(v35.RetentionQuickReleaseTactileV35Error, match="collides"):
        v35._sixteenth_evidence()


def test_v35_rejects_stale_pose_count():
    result = v35.build_retention_quick_release_tactile_v35()
    with pytest.raises(v35.RetentionQuickReleaseTactileV35Error, match="pose count"):
        replace(result, pose_count=result.pose_count - 1).validate()


def test_v35_rejects_stale_digest():
    result = v35.build_retention_quick_release_tactile_v35()
    with pytest.raises(v35.RetentionQuickReleaseTactileV35Error, match="digest"):
        replace(result, evidence_sha256="0" * 64).validate()
