from __future__ import annotations

import pytest

from masck_one import retention_quick_release_tactile as v1
from masck_one import retention_quick_release_tactile_v8 as v8
from masck_one import retention_quick_release_tactile_v10 as v10
from masck_one import retention_quick_release_tactile_v11 as v11


def test_v11_preserves_v8_domain_and_halves_v10_interval():
    prior = v10.build_retention_quick_release_tactile_v10()
    candidate = v11.build_retention_quick_release_tactile_v11()
    assert candidate.radial_limit_mm == prior.radial_limit_mm
    assert candidate.side_limit_mm == prior.side_limit_mm
    assert candidate.transverse_sample_count == prior.transverse_sample_count
    assert candidate.boundary_sample_count == prior.boundary_sample_count
    assert candidate.release_station_count == v11.TRAVEL_STATIONS == 2 * v10.TRAVEL_STATIONS - 1
    assert candidate.inherited_v10_station_count == v10.TRAVEL_STATIONS
    assert candidate.added_eighth_station_count == v10.TRAVEL_STATIONS - 1
    assert candidate.max_unscreened_travel_interval_mm == pytest.approx(0.5 * prior.max_unscreened_travel_interval_mm)
    assert candidate.total_pose_count == candidate.transverse_sample_count * v11.TRAVEL_STATIONS
    assert candidate.max_rigid_guide_intersection_mm3 == 0.0


def test_v11_retains_every_v10_station():
    positions = v11._travel_positions_mm()
    inherited = v10._travel_positions_mm()
    assert positions[0] == 0.0
    assert positions[-1] == pytest.approx(v1.RELEASE_TRAVEL_MM)
    assert all(any(x == pytest.approx(old) for x in positions) for old in inherited)
    for left, right in zip(inherited, inherited[1:]):
        assert any(x == pytest.approx((left + right) / 2.0) for x in positions)


def test_v11_manifest_keeps_evidence_firewall():
    manifest = v11.build_retention_quick_release_tactile_v11().manifest()
    screen = manifest["transverse_clearance_release_path"]
    assert manifest["schema"] == v11.SCHEMA
    assert manifest["supersedes_schema"] == v10.SCHEMA
    assert screen["added_eighth_station_count"] == v10.TRAVEL_STATIONS - 1
    assert "SAMPLED" in screen["scope"]
    assert "NOT_CONTINUOUS_PROOF" in screen["scope"]
    assert manifest["physical_validation_eligible"] is False


def test_v11_hostile_offset_fails_closed():
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
    with pytest.raises(v11.RetentionQuickReleaseTactileV11Error, match="collision"):
        v11._eighth_interval_clearance_screen(hostile, v11.CLEARANCE_FRACTION * hostile.rail_radial_clearance_mm, v11.CLEARANCE_FRACTION * hostile.anti_rotation_side_clearance_mm)


def test_v11_boolean_failure_fails_closed(monkeypatch):
    mechanism = v8.build_retention_quick_release_tactile_v8().mechanism
    def fail(*_args, **_kwargs):
        raise RuntimeError("synthetic OCC failure")
    monkeypatch.setattr(v1, "_intersection", fail)
    with pytest.raises(v11.RetentionQuickReleaseTactileV11Error, match="Boolean clearance query failed"):
        v11._eighth_interval_clearance_screen(mechanism, v11.CLEARANCE_FRACTION * mechanism.rail_radial_clearance_mm, v11.CLEARANCE_FRACTION * mechanism.anti_rotation_side_clearance_mm)
