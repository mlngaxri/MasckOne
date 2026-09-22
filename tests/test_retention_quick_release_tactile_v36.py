from __future__ import annotations

from dataclasses import replace

import pytest

from masck_one import retention_quick_release_tactile_v35 as v35
from masck_one import retention_quick_release_tactile_v36 as v36


def test_v36_builds_complete_sixteenth_lattice() -> None:
    model = v36.build_retention_quick_release_tactile_v36()
    expected = v36._expected_lattice()
    assert model.complete_lattice_position_count == len(expected)
    assert model.max_longitudinal_sample_gap_mm > 0.0
    assert len(model.coverage_sha256) == 64
    manifest = model.manifest()
    assert manifest["schema"] == v36.SCHEMA
    assert manifest["physical_validation_eligible"] is False


def test_v36_rejects_missing_inherited_sample(monkeypatch: pytest.MonkeyPatch) -> None:
    original = v35._sixteenth_positions
    monkeypatch.setattr(v35, "_sixteenth_positions", lambda: original()[:-1])
    with pytest.raises(v36.RetentionQuickReleaseTactileV36Error, match="count is incomplete"):
        v36._coverage_evidence()


def test_v36_rejects_duplicate_inherited_sample(monkeypatch: pytest.MonkeyPatch) -> None:
    original = v35._sixteenth_positions
    values = original()
    monkeypatch.setattr(v35, "_sixteenth_positions", lambda: values[:-1] + (values[-2],))
    with pytest.raises(v36.RetentionQuickReleaseTactileV36Error, match="duplicate samples"):
        v36._coverage_evidence()


def test_v36_rejects_displaced_inherited_sample(monkeypatch: pytest.MonkeyPatch) -> None:
    original = v35._sixteenth_positions
    values = original()
    monkeypatch.setattr(v35, "_sixteenth_positions", lambda: values[:-1] + (values[-1] + 1e-5,))
    with pytest.raises(v36.RetentionQuickReleaseTactileV36Error, match="do not exactly cover"):
        v36._coverage_evidence()


def test_v36_rejects_stale_evidence() -> None:
    model = v36.build_retention_quick_release_tactile_v36()
    with pytest.raises(v36.RetentionQuickReleaseTactileV36Error, match="position count is stale"):
        replace(model, complete_lattice_position_count=model.complete_lattice_position_count + 1).validate()
    with pytest.raises(v36.RetentionQuickReleaseTactileV36Error, match="sample-gap evidence is stale"):
        replace(model, max_longitudinal_sample_gap_mm=model.max_longitudinal_sample_gap_mm + 0.01).validate()
    with pytest.raises(v36.RetentionQuickReleaseTactileV36Error, match="coverage digest is stale"):
        replace(model, coverage_sha256="0" * 64).validate()
