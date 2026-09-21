from dataclasses import replace

import pytest

from masck_one import retention_quick_release_tactile_v12 as v12
from masck_one import retention_quick_release_tactile_v18 as v18
from masck_one import retention_quick_release_tactile_v19 as v19
from masck_one import retention_quick_release_tactile_v20 as v20


class Chain:
    def __init__(self, depth: int) -> None:
        self.prior = Chain(depth - 1) if depth else None
        self.mechanism = object()

    def validate(self) -> "Chain":
        return self


def test_eighth_points_fill_remaining_gaps_between_existing_travel_samples() -> None:
    positions = v12._canonical_positions()
    eighths = v20._eighth_positions()
    quarters = v19._quarter_positions()
    midpoints = v18._midpoint_positions()
    assert len(eighths) == 4 * (len(positions) - 1)
    for index, (a, midpoint, b) in enumerate(zip(positions, midpoints, positions[1:])):
        e1, e3, e5, e7 = eighths[4 * index : 4 * index + 4]
        q1, q3 = quarters[2 * index : 2 * index + 2]
        assert a < e1 < q1 < e3 < midpoint < e5 < q3 < e7 < b
        assert (e1, e3, e5, e7) == pytest.approx(tuple(a + (b - a) * f for f in (0.125, 0.375, 0.625, 0.875)))


def test_validate_rejects_stale_eighth_gap_counts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(v20, "_eighth_gap_evidence", lambda mechanism: (28, 11, 308, 0.0, "a" * 64))
    evidence = v20.RetentionQuickReleaseTactileV20(Chain(9), 28, 11, 308, 0.0, "a" * 64)
    evidence.validate()
    with pytest.raises(v20.RetentionQuickReleaseTactileV20Error, match="eighth-point count is stale"):
        replace(evidence, travel_eighth_point_count=27).validate()
    with pytest.raises(v20.RetentionQuickReleaseTactileV20Error, match="pose count is stale"):
        replace(evidence, pose_count=307).validate()


def test_validate_rejects_noncanonical_or_stale_digest(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(v20, "_eighth_gap_evidence", lambda mechanism: (4, 3, 12, 0.0, "b" * 64))
    evidence = v20.RetentionQuickReleaseTactileV20(Chain(9), 4, 3, 12, 0.0, "b" * 64)
    with pytest.raises(v20.RetentionQuickReleaseTactileV20Error, match="canonical lowercase SHA-256"):
        replace(evidence, evidence_sha256="B" * 64).validate()
    with pytest.raises(v20.RetentionQuickReleaseTactileV20Error, match="digest is stale"):
        replace(evidence, evidence_sha256="c" * 64).validate()
