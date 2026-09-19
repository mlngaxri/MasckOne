from __future__ import annotations

import pytest

from masck_one import retention_quick_release_tactile as v1
from masck_one import retention_quick_release_tactile_v8 as v8
from masck_one import retention_quick_release_tactile_v9 as v9
from masck_one.retention_quick_release_tactile_v10 import (
    CLEARANCE_FRACTION, SCHEMA, SUPERSEDES_SCHEMA, TRAVEL_STATIONS,
    RetentionQuickReleaseTactileV10Error, _quartered_clearance_screen,
    _travel_positions_mm, build_retention_quick_release_tactile_v10,
)


def test_v10_preserves_v8_domain_and_halves_v9_travel_interval():
    prior = v9.build_retention_quick_release_tactile_v9()
    candidate = build_retention_quick_release_tactile_v10()
    assert candidate.radial_limit_mm == prior.radial_limit_mm
    assert candidate.side_limit_mm == prior.side_limit_mm
    assert candidate.transverse_sample_count == prior.transverse_sample_count
    assert candidate.boundary_sample_count == prior.boundary_sample_count
    assert candidate.release_station_count == TRAVEL_STATIONS == 2 * v9.TRAVEL_STATIONS - 1
    assert candidate.inherited_v9_station_count == v9.TRAVEL_STATIONS
    assert candidate.added_quarter_station_count == v9.TRAVEL_STATIONS - 1
    assert candidate.max_unscreened_travel_interval_mm == pytest.approx(v1.RELEASE_TRAVEL_MM / (TRAVEL_STATIONS - 1))
    assert candidate.max_unscreened_travel_interval_mm == pytest.approx(0.5 * v1.RELEASE_TRAVEL_MM / (v9.TRAVEL_STATIONS - 1))
    assert candidate.total_pose_count == candidate.transverse_sample_count * TRAVEL_STATIONS
    assert candidate.max_rigid_guide_intersection_mm3 == 0.0


def test_v10_positions_retain_every_v9_station_and_add_interval_quarters():
    positions = _travel_positions_mm()
    inherited = v9._travel_positions_mm()
    assert positions[0] == 0.0
    assert positions[-1] == pytest.approx(v1.RELEASE_TRAVEL_MM)
    assert all(any(x == pytest.approx(old) for x in positions) for old in inherited)
    for left, right in zip(inherited, inherited[1:]):
        assert any(x == pytest.approx(left + 0.5 * (right - left)) for x in positions)


def test_v10_manifest_keeps_evidence_firewall_and_reports_interval():
    manifest = build_retention_quick_release_tactile_v10().manifest()
    screen = manifest["transverse_clearance_release_path"]
    assert manifest["schema"] == SCHEMA
    assert manifest["supersedes_schema"] == SUPERSEDES_SCHEMA == v9.SCHEMA
    assert screen["added_quarter_station_count"] == v9.TRAVEL_STATIONS - 1
    assert screen["max_unscreened_travel_interval_mm"] > 0.0
    assert "SAMPLED" in screen["scope"]
    assert "NOT_CONTINUOUS_PROOF" in screen["scope"]
    assert manifest["physical_validation_eligible"] is False


def test_v10_rejects_nominal_clearance_limits():
    mechanism = v8.build_retention_quick_release_tactile_v8().mechanism
    with pytest.raises(RetentionQuickReleaseTactileV10Error, match="spool-rail radial clearance"):
        _quartered_clearance_screen(mechanism, mechanism.rail_radial_clearance_mm, CLEARANCE_FRACTION * mechanism.anti_rotation_side_clearance_mm)
    with pytest.raises(RetentionQuickReleaseTactileV10Error, match="anti-rotation side clearance"):
        _quartered_clearance_screen(mechanism, CLEARANCE_FRACTION * mechanism.rail_radial_clearance_mm, mechanism.anti_rotation_side_clearance_mm)


def test_v10_hostile_offset_fails_closed():
    mechanism = v8.build_retention_quick_release_tactile_v8().mechanism
    hostile = v1.RetentionQuickReleaseTactile(
        mechanism.slider.translate((0.0, 0.0, 0.40)), mechanism.guide,
        mechanism.flexure_free, mechanism.flexure_installed_reference,
        mechanism.bumper_free_regions, mechanism.bumper_installed_references,
        mechanism.rail_radial_clearance_mm, mechanism.anti_rotation_side_clearance_mm,
        mechanism.flexure_free_slider_interference_mm3, mechanism.flexure_installed_slider_interference_mm3,
        mechanism.inboard_bumper_free_interference_mm3, mechanism.outboard_bumper_free_interference_mm3,
        mechanism.inboard_bumper_installed_interference_mm3, mechanism.outboard_bumper_installed_interference_mm3,
        mechanism.rigid_inboard_overtravel_intersection_mm3, mechanism.rigid_outboard_overtravel_intersection_mm3,
        mechanism.physical_validation_eligible,
    )
    with pytest.raises(RetentionQuickReleaseTactileV10Error, match="collision"):
        _quartered_clearance_screen(hostile, CLEARANCE_FRACTION * hostile.rail_radial_clearance_mm, CLEARANCE_FRACTION * hostile.anti_rotation_side_clearance_mm)
