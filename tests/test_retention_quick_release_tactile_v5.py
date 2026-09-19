from __future__ import annotations

import pytest

from masck_one import retention_quick_release_tactile as v1
from masck_one import retention_quick_release_tactile_v4 as v4
from masck_one.retention_quick_release_tactile_v5 import (
    LATERAL_OFFSET_FRACTIONS,
    SCHEMA,
    SUPERSEDES_SCHEMA,
    RetentionQuickReleaseTactileV5Error,
    _lateral_clearance_screen,
    build_retention_quick_release_tactile_v5,
)


def test_v5_screens_full_release_path_across_bounded_lateral_offsets():
    candidate = build_retention_quick_release_tactile_v5()
    nominal_limit = min(
        candidate.mechanism.rail_radial_clearance_mm,
        candidate.mechanism.anti_rotation_side_clearance_mm,
    )
    assert candidate.lateral_offset_limit_mm == pytest.approx(0.8 * nominal_limit)
    assert candidate.lateral_offset_count == len(LATERAL_OFFSET_FRACTIONS)
    assert candidate.release_station_count == v4.SWEEP_STATIONS
    assert candidate.total_pose_count == len(LATERAL_OFFSET_FRACTIONS) * v4.SWEEP_STATIONS
    assert candidate.max_rigid_guide_intersection_mm3 == 0.0


def test_v5_manifest_preserves_evidence_firewall():
    candidate = build_retention_quick_release_tactile_v5()
    manifest = candidate.manifest()
    screen = manifest["lateral_clearance_release_path"]
    assert manifest["schema"] == SCHEMA
    assert manifest["supersedes_schema"] == SUPERSEDES_SCHEMA == v4.SCHEMA
    assert screen["total_pose_count"] == len(LATERAL_OFFSET_FRACTIONS) * v4.SWEEP_STATIONS
    assert screen["max_rigid_guide_intersection_mm3"] == 0.0
    assert "NOT_MANUFACTURING_OR_PHYSICAL_VALIDATION" in screen["scope"]
    assert manifest["physical_validation_eligible"] is False


def test_v5_rejects_screen_at_or_beyond_nominal_clearance():
    mechanism = v4.build_retention_quick_release_tactile_v4().mechanism
    nominal_limit = min(
        mechanism.rail_radial_clearance_mm,
        mechanism.anti_rotation_side_clearance_mm,
    )
    with pytest.raises(RetentionQuickReleaseTactileV5Error, match="inside nominal guide clearance"):
        _lateral_clearance_screen(mechanism, nominal_limit)


def test_v5_hostile_lateral_offset_still_fails_closed():
    mechanism = v4.build_retention_quick_release_tactile_v4().mechanism
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
    with pytest.raises(RetentionQuickReleaseTactileV5Error, match="collision"):
        _lateral_clearance_screen(hostile, 0.8 * min(
            hostile.rail_radial_clearance_mm,
            hostile.anti_rotation_side_clearance_mm,
        ))
