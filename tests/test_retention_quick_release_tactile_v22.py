from dataclasses import replace

import pytest

from masck_one import retention_quick_release_tactile_v12 as v12
from masck_one import retention_quick_release_tactile_v21 as v21
from masck_one import retention_quick_release_tactile_v22 as v22


class Prior:
    def validate(self) -> "Prior":
        return self


def test_complete_grid_is_exact_sixteenth_schedule() -> None:
    canonical = v12._canonical_positions()
    grid = v22._complete_sixteenth_grid()
    expected = []
    for interval_index, (a, b) in enumerate(zip(canonical, canonical[1:])):
        points = [a + (b - a) * index / 16.0 for index in range(17)]
        expected.extend(points if interval_index == 0 else points[1:])
    assert grid == pytest.approx(expected, abs=1e-12)
    assert len(grid) == 16 * (len(canonical) - 1) + 1


def test_coverage_evidence_binds_gap_bound_and_digest() -> None:
    count, maximum, allowed, digest = v22._coverage_evidence()
    assert count == len(v22._complete_sixteenth_grid())
    assert maximum <= allowed + 1e-12
    assert len(digest) == 64
    int(digest, 16)


def test_complete_grid_fails_if_one_screen_drops_a_point(monkeypatch: pytest.MonkeyPatch) -> None:
    original = v21._sixteenth_positions()
    monkeypatch.setattr(v21, "_sixteenth_positions", lambda: original[:-1])
    with pytest.raises(v22.RetentionQuickReleaseTactileV22Error, match="complete sixteenth grid"):
        v22._complete_sixteenth_grid()


def test_validate_rejects_stale_coverage(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(v22, "_coverage_evidence", lambda: (113, 0.1, 0.1, "a" * 64))
    evidence = v22.RetentionQuickReleaseTactileV22(Prior(), 113, 0.1, 0.1, "a" * 64)
    evidence.validate()
    with pytest.raises(v22.RetentionQuickReleaseTactileV22Error, match="point count is stale"):
        replace(evidence, complete_grid_point_count=112).validate()
    with pytest.raises(v22.RetentionQuickReleaseTactileV22Error, match="maximum travel gap is stale"):
        replace(evidence, maximum_travel_gap_mm=0.2).validate()
    with pytest.raises(v22.RetentionQuickReleaseTactileV22Error, match="maximum allowed travel gap is stale"):
        replace(evidence, maximum_allowed_gap_mm=0.2).validate()


def test_validate_rejects_noncanonical_or_stale_digest(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(v22, "_coverage_evidence", lambda: (113, 0.1, 0.1, "b" * 64))
    evidence = v22.RetentionQuickReleaseTactileV22(Prior(), 113, 0.1, 0.1, "b" * 64)
    with pytest.raises(v22.RetentionQuickReleaseTactileV22Error, match="canonical lowercase SHA-256"):
        replace(evidence, schedule_sha256="B" * 64).validate()
    with pytest.raises(v22.RetentionQuickReleaseTactileV22Error, match="schedule digest is stale"):
        replace(evidence, schedule_sha256="c" * 64).validate()
