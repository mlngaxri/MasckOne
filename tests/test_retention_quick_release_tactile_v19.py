from dataclasses import replace

import pytest

from masck_one import retention_quick_release_tactile_v12 as v12
from masck_one import retention_quick_release_tactile_v18 as v18
from masck_one import retention_quick_release_tactile_v19 as v19


class Chain:
    def __init__(self, depth: int) -> None:
        self.prior = Chain(depth - 1) if depth else None
        self.mechanism = object()

    def validate(self) -> "Chain":
        return self


def test_quarter_points_fill_each_half_left_by_v18_midpoints() -> None:
    positions = v12._canonical_positions()
    points = v19._quarter_positions()
    midpoints = v18._midpoint_positions()
    assert len(points) == 2 * (len(positions) - 1)
    for index, (a, midpoint, b) in enumerate(zip(positions, midpoints, positions[1:])):
        q1, q3 = points[2 * index : 2 * index + 2]
        assert a < q1 < midpoint < q3 < b
        assert q1 == pytest.approx(a + (b - a) * 0.25)
        assert q3 == pytest.approx(a + (b - a) * 0.75)


def test_validate_rejects_stale_quarter_gap_counts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(v19, "_quarter_gap_evidence", lambda mechanism: (14, 11, 154, 0.0, "a" * 64))
    evidence = v19.RetentionQuickReleaseTactileV19(Chain(8), 14, 11, 154, 0.0, "a" * 64)
    evidence.validate()
    with pytest.raises(v19.RetentionQuickReleaseTactileV19Error, match="quarter-point count is stale"):
        replace(evidence, travel_quarter_point_count=13).validate()
    with pytest.raises(v19.RetentionQuickReleaseTactileV19Error, match="pose count is stale"):
        replace(evidence, pose_count=153).validate()


def test_validate_rejects_noncanonical_or_stale_digest(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(v19, "_quarter_gap_evidence", lambda mechanism: (4, 3, 12, 0.0, "b" * 64))
    evidence = v19.RetentionQuickReleaseTactileV19(Chain(8), 4, 3, 12, 0.0, "b" * 64)
    with pytest.raises(v19.RetentionQuickReleaseTactileV19Error, match="canonical lowercase SHA-256"):
        replace(evidence, evidence_sha256="B" * 64).validate()
    with pytest.raises(v19.RetentionQuickReleaseTactileV19Error, match="digest is stale"):
        replace(evidence, evidence_sha256="c" * 64).validate()
