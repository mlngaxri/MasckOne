from __future__ import annotations

import pytest

from masck_one import retention_quick_release_tactile as v1
from masck_one import retention_quick_release_tactile_v4 as v4
from masck_one import retention_quick_release_tactile_v8 as v8
from masck_one.retention_quick_release_tactile_v9 import (
    CLEARANCE_FRACTION,
    SCHEMA,
    SUPERSEDES_SCHEMA,
    TRAVEL_STATIONS,
    RetentionQuickReleaseTactileV9Error,
    _densified_clearance_screen,
    _travel_positions_mm,
    build_retention_quick_release_tactile_v9,
)


def test_v9_preserves_v8_transverse_domain_and_densifies_travel():
    prior = v8.build_retention_quick_release_tactile_v8()
    candidate = build_retention_quick_release_tactile_v9()
    assert candidate.radial_limit_mm == prior.radial_limit_mm
    assert candidate.side_limit_mm == prior.side_limit_mm
    assert candidate.transverse_sample_count == prior.transverse_sample_count
    assert candidate.boundary_sample_count == prior.boundary_sample_count
    assert candidate.release_station_count == TRAVEL_STATIONS == 2 * v4.SWEEP_STATIONS - 1
    assert candidate.inherited_station_count == v4.SWEEP_STATIONS
    assert candidate.midpoint_station_count == v4.SWEEP_STATIONS - 1
    assert candidate.total_pose_count == candidate.transverse_sample_count * TRAVEL_STATIONS
    assert candidate.max_rigid_guide_intersection_mm3 == 0.0


def test_v9_positions_contain_every_v4_station_and_each_interval_midpoint():
    positions = _travel_positions_mm()
    inherited = tuple(v1.RELEASE_TRAVEL_MM * i / (v4.SWEEP_STATIONS - 1) for i in range(v4.SWEEP_STATIONS))
    assert positions[0] == 0.0
    assert positions[-1] == pytest.approx(v1.RELEASE_TRAVEL_MM)
    assert all(any(x == pytest.approx(old) for x in positions) for old in inherited)
    for left, right in zip(inherited, inherited[1:]):
        midpoint = 0.5 * (left + right)
        assert any(x == pytest.approx(midpoint) for x in positions)


def test_v9_manifest_keeps_sampled_evidence_firewall():
    manifest = build_retention_quick_release_tactile_v9().manifest()
    screen = manifest["transverse_clearance_release_path"]
    assert manifest["schema"] == SCHEMA
    assert manifest["supersedes_schema"] == SUPERSEDES_SCHEMA == v8.SCHEMA
    assert screen["midpoint_station_count"] == v4.SWEEP_STATIONS - 1
    assert "SAMPLED" in screen["scope"]
    assert "NOT_CONTINUOUS_PROOF" in screen["scope"]
    assert manifest["physical_validation_eligible"] is False


def test_v9_rejects_limits_at_nominal_clearance():
    mechanism = v8.build_retention_quick_release_tactile_v8().mechanism
    with pytest.raises(RetentionQuickReleaseTactileV9Error, match="spool-rail radial clearance"):
        _densified_clearance_screen(mechanism, mechanism.rail_radial_clearance_mm, CLEARANCE_FRACTION * mechanism.anti_rotation_side_clearance_mm)
    with pytest.raises(RetentionQuickReleaseTactileV9Error, match="anti-rotation side clearance"):
        _densified_clearance_screen(mechanism, CLEARANCE_FRACTION * mechanism.rail_radial_clearance_mm, mechanism.anti_rotation_side_clearance_mm)


def test_v9_hostile_offset_fails_closed_on_densified_path():
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
    with pytest.raises(RetentionQuickReleaseTactileV9Error, match="collision"):
        _densified_clearance_screen(hostile, CLEARANCE_FRACTION * hostile.rail_radial_clearance_mm, CLEARANCE_FRACTION * hostile.anti_rotation_side_clearance_mm)
