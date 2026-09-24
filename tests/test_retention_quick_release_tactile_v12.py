from __future__ import annotations

from dataclasses import replace

import pytest

from masck_one import retention_quick_release_tactile_v10 as v10
from masck_one import retention_quick_release_tactile_v11 as v11
from masck_one import retention_quick_release_tactile_v12 as v12


def test_v12_binds_exact_v11_station_schedule_and_v10_inheritance():
    candidate = v12.build_retention_quick_release_tactile_v12()
    positions = v12._canonical_positions()
    assert candidate.prior.release_station_count == v11.TRAVEL_STATIONS
    assert candidate.station_schedule_sha256 == v12._schedule_digest(positions)
    assert candidate.inherited_v10_station_count == v10.TRAVEL_STATIONS
    assert candidate.max_v10_registration_error_mm <= v12.COORDINATE_TOL_MM
    assert all(min(abs(x - old) for x in positions) <= v12.COORDINATE_TOL_MM for old in v10._travel_positions_mm())


def test_v12_rejects_stale_or_malformed_schedule_digest():
    candidate = v12.build_retention_quick_release_tactile_v12()
    with pytest.raises(v12.RetentionQuickReleaseTactileV12Error, match="does not match"):
        replace(candidate, station_schedule_sha256="0" * 64).validate()
    with pytest.raises(v12.RetentionQuickReleaseTactileV12Error, match="canonical lowercase"):
        replace(candidate, station_schedule_sha256="A" * 64).validate()
    with pytest.raises(v12.RetentionQuickReleaseTactileV12Error, match="canonical lowercase"):
        replace(candidate, station_schedule_sha256="0" * 63).validate()


def test_v12_rejects_stale_v10_registration_evidence():
    candidate = v12.build_retention_quick_release_tactile_v12()
    with pytest.raises(v12.RetentionQuickReleaseTactileV12Error, match="registration evidence is stale"):
        replace(candidate, max_v10_registration_error_mm=0.01).validate()
    with pytest.raises(v12.RetentionQuickReleaseTactileV12Error, match="inheritance count"):
        replace(candidate, inherited_v10_station_count=candidate.inherited_v10_station_count - 1).validate()


def test_v12_manifest_keeps_evidence_firewall():
    manifest = v12.build_retention_quick_release_tactile_v12().manifest()
    identity = manifest["release_station_schedule_identity"]
    assert manifest["schema"] == v12.SCHEMA
    assert manifest["supersedes_schema"] == v11.SCHEMA
    assert identity["station_count"] == v11.TRAVEL_STATIONS
    assert "NOT_CONTINUOUS_CLEARANCE" in identity["scope"]
    assert manifest["physical_validation_eligible"] is False
