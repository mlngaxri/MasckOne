from __future__ import annotations

from dataclasses import replace

import pytest

from masck_one import retention_quick_release_tactile as v1
from masck_one import retention_quick_release_tactile_v11 as v11
from masck_one import retention_quick_release_tactile_v13 as v13


def test_v13_audits_full_uniform_monotonic_release_schedule():
    candidate = v13.build_retention_quick_release_tactile_v13()
    expected_step = v1.RELEASE_TRAVEL_MM / (v11.TRAVEL_STATIONS - 1)
    assert candidate.first_station_mm == pytest.approx(0.0, abs=v13.COORDINATE_TOL_MM)
    assert candidate.last_station_mm == pytest.approx(v1.RELEASE_TRAVEL_MM, abs=v13.COORDINATE_TOL_MM)
    assert candidate.travel_span_mm == pytest.approx(v1.RELEASE_TRAVEL_MM, abs=v13.COORDINATE_TOL_MM)
    assert candidate.minimum_step_mm == pytest.approx(expected_step, abs=v13.COORDINATE_TOL_MM)
    assert candidate.maximum_step_mm == pytest.approx(expected_step, abs=v13.COORDINATE_TOL_MM)


def test_v13_rejects_stale_topology_evidence():
    candidate = v13.build_retention_quick_release_tactile_v13()
    for field in ("first_station_mm", "last_station_mm", "minimum_step_mm", "maximum_step_mm", "travel_span_mm"):
        with pytest.raises(v13.RetentionQuickReleaseTactileV13Error, match="topology evidence is stale"):
            replace(candidate, **{field: getattr(candidate, field) + 0.01}).validate()


def test_v13_rejects_nonfinite_topology_evidence():
    candidate = v13.build_retention_quick_release_tactile_v13()
    with pytest.raises(v13.RetentionQuickReleaseTactileV13Error, match="must be finite"):
        replace(candidate, maximum_step_mm=float("nan")).validate()


def test_v13_manifest_keeps_evidence_firewall():
    manifest = v13.build_retention_quick_release_tactile_v13().manifest()
    audit = manifest["release_path_topology_audit"]
    assert manifest["schema"] == v13.SCHEMA
    assert audit["criterion"] == "STRICTLY_INCREASING_UNIFORM_FULL_TRAVEL_STATION_TOPOLOGY"
    assert "NOT_CONTINUOUS_CLEARANCE" in audit["scope"]
    assert manifest["physical_validation_eligible"] is False
