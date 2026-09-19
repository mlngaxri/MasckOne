from __future__ import annotations

import math

import pytest

from masck_one import retention_quick_release_tactile as v1
from masck_one import retention_quick_release_tactile_v4 as v4
from masck_one import retention_quick_release_tactile_v6 as v6
from masck_one.retention_quick_release_tactile_v7 import (
    CLEARANCE_FRACTION,
    SCHEMA,
    SUPERSEDES_SCHEMA,
    RetentionQuickReleaseTactileV7Error,
    _normalised_disk_samples,
    _radial_clearance_screen,
    build_retention_quick_release_tactile_v7,
)


def test_v7_samples_are_inside_radial_disk_not_v6_square_corners():
    samples = _normalised_disk_samples()
    assert samples
    assert all(math.hypot(y, z) <= 1.0 + 1e-12 for y, z in samples)
    assert (1.0, 1.0) not in samples
    assert (-1.0, -1.0) not in samples


def test_v7_screens_radial_and_side_clearance_through_full_release_path():
    candidate = build_retention_quick_release_tactile_v7()
    assert candidate.radial_limit_mm == pytest.approx(CLEARANCE_FRACTION * candidate.mechanism.rail_radial_clearance_mm)
    assert candidate.side_limit_mm == pytest.approx(CLEARANCE_FRACTION * candidate.mechanism.anti_rotation_side_clearance_mm)
    assert candidate.transverse_sample_count == len(_normalised_disk_samples())
    assert candidate.release_station_count == v4.SWEEP_STATIONS
    assert candidate.total_pose_count == candidate.transverse_sample_count * v4.SWEEP_STATIONS
    assert candidate.max_rigid_guide_intersection_mm3 == 0.0


def test_v7_manifest_preserves_evidence_firewall_and_supersedes_v6():
    manifest = build_retention_quick_release_tactile_v7().manifest()
    screen = manifest["transverse_clearance_release_path"]
    assert manifest["schema"] == SCHEMA
    assert manifest["supersedes_schema"] == SUPERSEDES_SCHEMA == v6.SCHEMA
    assert screen["criterion"] == "NO_POSITIVE_RIGID_GUIDE_INTERSECTION_INSIDE_RADIAL_AND_SIDE_CLEARANCE_BOUNDS"
    assert "NOT_MANUFACTURING_OR_PHYSICAL_VALIDATION" in screen["scope"]
    assert manifest["physical_validation_eligible"] is False


def test_v7_rejects_radial_or_side_limit_at_nominal_clearance():
    mechanism = v6.build_retention_quick_release_tactile_v6().mechanism
    with pytest.raises(RetentionQuickReleaseTactileV7Error, match="spool-rail radial clearance"):
        _radial_clearance_screen(mechanism, mechanism.rail_radial_clearance_mm, 0.8 * mechanism.anti_rotation_side_clearance_mm)
    with pytest.raises(RetentionQuickReleaseTactileV7Error, match="anti-rotation side clearance"):
        _radial_clearance_screen(mechanism, 0.8 * mechanism.rail_radial_clearance_mm, mechanism.anti_rotation_side_clearance_mm)


def test_v7_hostile_vertical_offset_fails_closed():
    mechanism = v6.build_retention_quick_release_tactile_v6().mechanism
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
    with pytest.raises(RetentionQuickReleaseTactileV7Error, match="collision"):
        _radial_clearance_screen(
            hostile,
            CLEARANCE_FRACTION * hostile.rail_radial_clearance_mm,
            CLEARANCE_FRACTION * hostile.anti_rotation_side_clearance_mm,
        )
