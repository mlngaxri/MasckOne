from dataclasses import replace

import pytest

from masck_one import retention_quick_release_tactile_v12 as v12
from masck_one import retention_quick_release_tactile_v18 as v18


def test_midpoints_strictly_fill_every_canonical_travel_gap() -> None:
    positions = v12._canonical_positions()
    midpoints = v18._midpoint_positions()
    assert len(midpoints) == len(positions) - 1
    assert all(a < midpoint < b for a, midpoint, b in zip(positions, midpoints, positions[1:]))
    assert all(midpoint == pytest.approx((a + b) / 2.0) for a, midpoint, b in zip(positions, midpoints, positions[1:]))


def test_validate_rejects_stale_travel_gap_counts(monkeypatch: pytest.MonkeyPatch) -> None:
    prior = object()
    monkeypatch.setattr(v18.v17.RetentionQuickReleaseTactileV17, "validate", lambda self: self)
    monkeypatch.setattr(v18, "_travel_gap_evidence", lambda mechanism: (7, 11, 77, 0.0, "a" * 64))

    class Chain:
        def __init__(self, depth: int) -> None:
            self.prior = Chain(depth - 1) if depth else None
            self.mechanism = object()

    evidence = v18.RetentionQuickReleaseTactileV18(Chain(7), 7, 11, 77, 0.0, "a" * 64)
    evidence.validate()
    with pytest.raises(v18.RetentionQuickReleaseTactileV18Error, match="travel midpoint count is stale"):
        replace(evidence, travel_midpoint_count=6).validate()
    with pytest.raises(v18.RetentionQuickReleaseTactileV18Error, match="pose count is stale"):
        replace(evidence, pose_count=76).validate()


def test_validate_rejects_noncanonical_or_stale_digest(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(v18.v17.RetentionQuickReleaseTactileV17, "validate", lambda self: self)
    monkeypatch.setattr(v18, "_travel_gap_evidence", lambda mechanism: (2, 3, 6, 0.0, "b" * 64))

    class Chain:
        def __init__(self, depth: int) -> None:
            self.prior = Chain(depth - 1) if depth else None
            self.mechanism = object()

    evidence = v18.RetentionQuickReleaseTactileV18(Chain(7), 2, 3, 6, 0.0, "b" * 64)
    with pytest.raises(v18.RetentionQuickReleaseTactileV18Error, match="canonical lowercase SHA-256"):
        replace(evidence, evidence_sha256="B" * 64).validate()
    with pytest.raises(v18.RetentionQuickReleaseTactileV18Error, match="digest is stale"):
        replace(evidence, evidence_sha256="c" * 64).validate()
