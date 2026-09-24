from dataclasses import replace

import pytest

from masck_one import retention_quick_release_tactile_v12 as v12
from masck_one import retention_quick_release_tactile_v20 as v20
from masck_one import retention_quick_release_tactile_v21 as v21


class Chain:
    def __init__(self, depth: int) -> None:
        self.prior = Chain(depth - 1) if depth else None
        self.mechanism = object()

    def validate(self) -> "Chain":
        return self


def test_sixteenth_points_fill_remaining_gaps_around_eighth_grid() -> None:
    positions = v12._canonical_positions()
    sixteenths = v21._sixteenth_positions()
    eighths = v20._eighth_positions()
    assert len(sixteenths) == 8 * (len(positions) - 1)
    for index, (a, b) in enumerate(zip(positions, positions[1:])):
        odd = sixteenths[8 * index : 8 * index + 8]
        existing = eighths[4 * index : 4 * index + 4]
        full_grid = sorted((a, b, *odd, *existing, a + (b-a)*0.25, a + (b-a)*0.5, a + (b-a)*0.75))
        expected = [a + (b - a) * k / 16.0 for k in range(17)]
        assert full_grid == pytest.approx(expected)


def test_validate_rejects_stale_sixteenth_gap_counts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(v21, "_sixteenth_gap_evidence", lambda mechanism: (56, 11, 616, 0.0, "a" * 64))
    evidence = v21.RetentionQuickReleaseTactileV21(Chain(10), 56, 11, 616, 0.0, "a" * 64)
    evidence.validate()
    with pytest.raises(v21.RetentionQuickReleaseTactileV21Error, match="sixteenth-point count is stale"):
        replace(evidence, travel_sixteenth_point_count=55).validate()
    with pytest.raises(v21.RetentionQuickReleaseTactileV21Error, match="pose count is stale"):
        replace(evidence, pose_count=615).validate()


def test_validate_rejects_noncanonical_or_stale_digest(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(v21, "_sixteenth_gap_evidence", lambda mechanism: (8, 3, 24, 0.0, "b" * 64))
    evidence = v21.RetentionQuickReleaseTactileV21(Chain(10), 8, 3, 24, 0.0, "b" * 64)
    with pytest.raises(v21.RetentionQuickReleaseTactileV21Error, match="canonical lowercase SHA-256"):
        replace(evidence, evidence_sha256="B" * 64).validate()
    with pytest.raises(v21.RetentionQuickReleaseTactileV21Error, match="digest is stale"):
        replace(evidence, evidence_sha256="c" * 64).validate()
