from __future__ import annotations

import pytest

from masck_one import retention_quick_release_tactile as v1
from masck_one import retention_quick_release_tactile_v3 as v3
from masck_one.retention_quick_release_tactile_v4 import (
    SCHEMA,
    SUPERSEDES_SCHEMA,
    SWEEP_STATIONS,
    RetentionQuickReleaseTactileV4Error,
    _continuous_guide_screen,
    build_retention_quick_release_tactile_v4,
)


def test_v4_checks_complete_release_travel_with_interior_stations():
    candidate = build_retention_quick_release_tactile_v4()
    assert candidate.sweep_station_count == SWEEP_STATIONS
    assert candidate.sweep_station_count >= 3
    assert candidate.minimum_checked_x_mm == 0.0
    assert candidate.maximum_checked_x_mm == v1.RELEASE_TRAVEL_MM
    assert candidate.max_rigid_guide_intersection_mm3 == 0.0


def test_v4_manifest_keeps_v3_geometry_and_evidence_firewall():
    candidate = build_retention_quick_release_tactile_v4()
    manifest = candidate.manifest()
    assert manifest["schema"] == SCHEMA
    assert manifest["supersedes_schema"] == SUPERSEDES_SCHEMA == v3.SCHEMA
    assert manifest["continuous_release_path"]["station_count"] == SWEEP_STATIONS
    assert manifest["continuous_release_path"]["travel_mm"] == v1.RELEASE_TRAVEL_MM
    assert manifest["continuous_release_path"]["max_rigid_guide_intersection_mm3"] == 0.0
    assert "NOT_PHYSICAL" in manifest["continuous_release_path"]["scope"]
    assert manifest["physical_validation_eligible"] is False


def test_v4_hostile_lateral_offset_is_rejected_by_same_screen():
    mechanism = v3.build_retention_quick_release_tactile_v3().mechanism
    hostile = v1.RetentionQuickReleaseTactile(
        mechanism.slider.translate((0.0, 0.40, 0.0)),
        mechanism.guide,
        mechanism.flexure_free,
        mechanism.flexure_installed_reference,
        mechanism.bumper_free_regions,
        mechanism.bumper_installed_references,
        mechanism.rail_radial_clearance_mm,
        mechanism.anti_rotation_side_clearance_mm,
        mechanism.flexure_free_slider_interference_mm3,
        mechanism.flexure_installed_slider_interference_mm3,
        mechanism.inboard_bumper_free_interference_mm3,
        mechanism.outboard_bumper_free_interference_mm3,
        mechanism.inboard_bumper_installed_interference_mm3,
        mechanism.outboard_bumper_installed_interference_mm3,
        mechanism.rigid_inboard_overtravel_intersection_mm3,
        mechanism.rigid_outboard_overtravel_intersection_mm3,
        mechanism.physical_validation_eligible,
    )
    with pytest.raises(RetentionQuickReleaseTactileV4Error, match="collision"):
        _continuous_guide_screen(hostile)
