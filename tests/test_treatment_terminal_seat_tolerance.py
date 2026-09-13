from __future__ import annotations

from studies.treatment_terminal_seat_tolerance import (
    RADIAL_ERROR_STUDY_MM,
    axial_capture_deadband_screen,
    build_manifest,
    rigid_four_face_tolerance_screen,
    single_detent_wedge_window,
)


def test_rigid_four_face_terminal_seat_is_rejected_as_tolerance_baseline():
    screen = rigid_four_face_tolerance_screen()
    assert screen["decision"].startswith("REJECT_FULLY_RIGID_FOUR_FACE_MATCHED_CONTACT")
    assert tuple(row["radial_error_seed_mm"] for row in screen["rows"]) == RADIAL_ERROR_STUDY_MM
    # Even the smallest deliberately optimistic study seed produces more independent
    # contact-position spread than the current 0.10 mm overtravel wedge can equalize.
    assert all(not row["current_overtravel_wedge_covers_spread"] for row in screen["rows"])


def test_single_detent_has_a_narrow_friction_retention_window():
    screen = single_detent_wedge_window()
    assert screen["retention_limited_max_equal_taper_angle_deg"] < 17.1
    rows = {row["friction_coefficient_seed"]: row for row in screen["friction_rows"]}
    assert rows[0.30]["feasible_slope_window"] is True
    assert rows[0.30]["angle_window_deg"] < 0.4
    assert rows[0.35]["feasible_slope_window"] is False
    assert screen["decision"].startswith("DO_NOT_REQUIRE_ONE_DETENT")


def test_positive_axial_capture_is_an_overload_backstop_not_normal_reaction_path():
    screen = axial_capture_deadband_screen()
    assert len(screen["rows"]) == 3
    assert all(row["x_clearance_reopened_before_hard_capture_mm"] > 0.0 for row in screen["rows"])
    assert all(row["z_clearance_reopened_before_hard_capture_mm"] > 0.0 for row in screen["rows"])
    assert screen["interpretation"].startswith("A_HARD_CAPTURE_IS_AN_OVERLOAD_BACKSTOP")


def test_manifest_selects_equalized_preloaded_rigid_bottoming_architecture():
    manifest = build_manifest()
    assert manifest["physical_validation_eligible"] is False
    assert "INDEPENDENT_RADIAL_EQUALIZATION_SHOES" in manifest["selected_architecture_direction"]
    assert "RIGID_COMPRESSIVE_DATUM_BOTTOMING" in manifest["selected_architecture_direction"]
    assert "SEPARATE_POSITIVE_AXIAL_OVERLOAD_CAPTURE" in manifest["selected_architecture_direction"]
    assert manifest["working_reaction_rule"].startswith("40HZ_WORKING_REACTION_MUST_NOT_CYCLE_A_LOOSE_GAP")
    assert manifest["physical_validation"].startswith("OPEN_")
