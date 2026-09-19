from __future__ import annotations

import math

import pytest

from masck_one import retention_quick_release_tactile as v1
from masck_one import retention_quick_release_tactile_v4 as v4
from masck_one import retention_quick_release_tactile_v7 as v7
from masck_one.retention_quick_release_tactile_v8 import (
    CLEARANCE_FRACTION,
    SCHEMA,
    SUPERSEDES_SCHEMA,
    RetentionQuickReleaseTactileV8Error,
    _boundary_aware_clearance_screen,
    _constrained_transverse_samples,
    _is_boundary_sample,
    build_retention_quick_release_tactile_v8,
)


def test_v8_explicitly_samples_constrained_boundary():
    candidate = build_retention_quick_release_tactile_v8()
    samples = _constrained_transverse_samples(candidate.radial_limit_mm, candidate.side_limit_mm)
    assert len(samples) == candidate.transverse_sample_count
    assert candidate.transverse_sample_count > v7.build_retention_quick_release_tactile_v7().transverse_sample_count
    assert candidate.boundary_sample_count >= 4
    assert sum(_is_boundary_sample(y, z, candidate.radial_limit_mm, candidate.side_limit_mm) for y, z in samples) == candidate.boundary_sample_count
    assert all(math.hypot(y, z) <= candidate.radial_limit_mm + 1e-12 for y, z in samples)
    assert all(abs(y) <= candidate.side_limit_mm + 1e-12 for y, z in samples)


def test_v8_screens_boundary_and_interior_through_full_release_path():
    candidate = build_retention_quick_release_tactile_v8()
    assert candidate.radial_limit_mm == pytest.approx(CLEARANCE_FRACTION * candidate.mechanism.rail_radial_clearance_mm)
    assert candidate.side_limit_mm == pytest.approx(CLEARANCE_FRACTION * candidate.mechanism.anti_rotation_side_clearance_mm)
    assert candidate.release_station_count == v4.SWEEP_STATIONS
    assert candidate.total_pose_count == candidate.transverse_sample_count * v4.SWEEP_STATIONS
    assert candidate.max_rigid_guide_intersection_mm3 == 0.0


def test_v8_manifest_preserves_evidence_firewall_and_supersedes_v7():
    manifest = build_retention_quick_release_tactile_v8().manifest()
    screen = manifest["transverse_clearance_release_path"]
    assert manifest["schema"] == SCHEMA
    assert manifest["supersedes_schema"] == SUPERSEDES_SCHEMA == v7.SCHEMA
    assert screen["criterion"] == "NO_POSITIVE_RIGID_GUIDE_INTERSECTION_AT_CONSTRAINED_BOUNDARY_AND_INTERIOR_SAMPLES"
    assert "NOT_CONTINUOUS_PROOF" in screen["scope"]
    assert manifest["physical_validation_eligible"] is False


def test_v8_rejects_limits_at_nominal_clearance():
    mechanism = v7.build_retention_quick_release_tactile_v7().mechanism
    with pytest.raises(RetentionQuickReleaseTactileV8Error, match="spool-rail radial clearance"):
        _boundary_aware_clearance_screen(mechanism, mechanism.rail_radial_clearance_mm, 0.8 * mechanism.anti_rotation_side_clearance_mm)
    with pytest.raises(RetentionQuickReleaseTactileV8Error, match="anti-rotation side clearance"):
        _boundary_aware_clearance_screen(mechanism, 0.8 * mechanism.rail_radial_clearance_mm, mechanism.anti_rotation_side_clearance_mm)


def test_v8_hostile_vertical_offset_fails_closed():
    mechanism = v7.build_retention_quick_release_tactile_v7().mechanism
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
    with pytest.raises(RetentionQuickReleaseTactileV8Error, match="collision"):
        _boundary_aware_clearance_screen(
            hostile,
            CLEARANCE_FRACTION * hostile.rail_radial_clearance_mm,
            CLEARANCE_FRACTION * hostile.anti_rotation_side_clearance_mm,
        )
