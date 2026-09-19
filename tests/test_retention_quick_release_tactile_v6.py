from __future__ import annotations

import pytest

from masck_one import retention_quick_release_tactile as v1
from masck_one import retention_quick_release_tactile_v4 as v4
from masck_one import retention_quick_release_tactile_v5 as v5
from masck_one.retention_quick_release_tactile_v6 import (
    OFFSET_FRACTIONS,
    SCHEMA,
    SUPERSEDES_SCHEMA,
    RetentionQuickReleaseTactileV6Error,
    _transverse_clearance_screen,
    build_retention_quick_release_tactile_v6,
)


def test_v6_screens_full_release_path_across_two_axis_clearance_grid():
    candidate = build_retention_quick_release_tactile_v6()
    nominal_limit = min(candidate.mechanism.rail_radial_clearance_mm, candidate.mechanism.anti_rotation_side_clearance_mm)
    assert candidate.offset_limit_mm == pytest.approx(0.8 * nominal_limit)
    assert candidate.transverse_grid_count == len(OFFSET_FRACTIONS) ** 2
    assert candidate.release_station_count == v4.SWEEP_STATIONS
    assert candidate.total_pose_count == len(OFFSET_FRACTIONS) ** 2 * v4.SWEEP_STATIONS
    assert candidate.max_rigid_guide_intersection_mm3 == 0.0


def test_v6_manifest_preserves_evidence_firewall_and_axes():
    manifest = build_retention_quick_release_tactile_v6().manifest()
    screen = manifest["transverse_clearance_release_path"]
    assert manifest["schema"] == SCHEMA
    assert manifest["supersedes_schema"] == SUPERSEDES_SCHEMA == v5.SCHEMA
    assert screen["offset_axes"] == ["Y", "Z"]
    assert screen["total_pose_count"] == len(OFFSET_FRACTIONS) ** 2 * v4.SWEEP_STATIONS
    assert "NOT_MANUFACTURING_OR_PHYSICAL_VALIDATION" in screen["scope"]
    assert manifest["physical_validation_eligible"] is False


def test_v6_rejects_screen_at_or_beyond_nominal_clearance():
    mechanism = v5.build_retention_quick_release_tactile_v5().mechanism
    nominal_limit = min(mechanism.rail_radial_clearance_mm, mechanism.anti_rotation_side_clearance_mm)
    with pytest.raises(RetentionQuickReleaseTactileV6Error, match="inside nominal guide clearance"):
        _transverse_clearance_screen(mechanism, nominal_limit)


def test_v6_hostile_vertical_offset_fails_closed():
    mechanism = v5.build_retention_quick_release_tactile_v5().mechanism
    hostile = v1.RetentionQuickReleaseTactile(
        mechanism.slider.translate((0.0, 0.0, 0.40)),
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
    with pytest.raises(RetentionQuickReleaseTactileV6Error, match="collision"):
        _transverse_clearance_screen(hostile, 0.8 * min(hostile.rail_radial_clearance_mm, hostile.anti_rotation_side_clearance_mm))
