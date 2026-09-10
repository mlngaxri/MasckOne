from __future__ import annotations

from masck_one.retention_quick_release_tactile import (
    ANTI_ROTATION_SIDE_CLEARANCE_MM,
    HISTORICAL_DONOR_HEAD_SHA,
    MAX_ANTI_ROTATION_SIDE_CLEARANCE_MM,
    MAX_SPOOL_RAIL_RADIAL_CLEARANCE_MM,
    RELEASE_TRAVEL_MM,
    SCHEMA,
    SPOOL_RAIL_RADIAL_CLEARANCE_MM,
    build_retention_quick_release_tactile,
)


def test_quick_release_reconstructs_donor_without_promoting_historical_source():
    candidate = build_retention_quick_release_tactile()
    manifest = candidate.manifest()

    assert manifest["schema"] == SCHEMA
    assert manifest["historical_donor_head_sha"] == HISTORICAL_DONOR_HEAD_SHA
    assert manifest["graph_promotion_status"].startswith("NOT_PROMOTED_")
    assert manifest["whole_head_removal"] == "UNRESOLVED"
    assert candidate.physical_validation_eligible is False


def test_integral_rails_and_key_reduce_uncontrolled_motion_without_zero_clearance():
    candidate = build_retention_quick_release_tactile()
    manifest = candidate.manifest()
    guidance = manifest["guidance"]

    assert 0.0 < SPOOL_RAIL_RADIAL_CLEARANCE_MM <= MAX_SPOOL_RAIL_RADIAL_CLEARANCE_MM
    assert guidance["new_integral_rail_radial_clearance_mm"] == SPOOL_RAIL_RADIAL_CLEARANCE_MM
    assert guidance["new_integral_rail_radial_clearance_mm"] < guidance["legacy_flange_to_cavity_radial_float_mm"]
    assert 0.0 < ANTI_ROTATION_SIDE_CLEARANCE_MM <= MAX_ANTI_ROTATION_SIDE_CLEARANCE_MM
    assert guidance["anti_rotation_rib_integral_to_slider"] is True
    assert guidance["open_corner_debris_paths"] == 4


def test_progressive_cam_keeps_free_preload_and_separate_installed_reference():
    candidate = build_retention_quick_release_tactile()
    manifest = candidate.manifest()
    detent = manifest["detent"]

    assert candidate.flexure_free_slider_interference_mm3 > 0.0
    assert candidate.flexure_installed_slider_interference_mm3 == 0.0
    assert detent["cam_profile"].endswith("QUINTIC_SMOOTHSTEP_APPROXIMATION")
    assert detent["nominal_interference_seed_mm"] > 0.0
    assert detent["force_validated"] is False


def test_bumpers_engage_before_but_do_not_replace_rigid_hard_stops():
    candidate = build_retention_quick_release_tactile()
    manifest = candidate.manifest()
    damping = manifest["end_state_damping"]

    assert candidate.inboard_bumper_free_interference_mm3 > 0.0
    assert candidate.outboard_bumper_free_interference_mm3 > 0.0
    assert candidate.inboard_bumper_installed_interference_mm3 == 0.0
    assert candidate.outboard_bumper_installed_interference_mm3 == 0.0
    assert candidate.rigid_inboard_overtravel_intersection_mm3 > 0.0
    assert candidate.rigid_outboard_overtravel_intersection_mm3 > 0.0
    assert damping["rigid_hard_stops_preserved"] is True
    assert damping["free_protrusion_mm"] > 0.0


def test_slider_and_guide_are_valid_and_full_release_travel_is_preserved():
    candidate = build_retention_quick_release_tactile()
    for shape in (candidate.slider, candidate.guide):
        assert shape.val().isValid()
        assert len(shape.val().Solids()) == 1
        assert shape.val().Volume() > 0.0

    manifest = candidate.manifest()
    assert manifest["release_travel_mm"] == RELEASE_TRAVEL_MM
    assert "PRECISION_FEEL_ONLY" in manifest["tactile_reference_rule"]
    assert "SUBJECTIVE_FEEL" in manifest["physical_validation"]
