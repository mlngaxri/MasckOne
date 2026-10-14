from __future__ import annotations

from studies.primary_control_sensor_travel_screen import (
    SCHEMA,
    build_screen,
)


def test_legacy_rear_hall_package_is_rejected_by_full_travel_collision():
    screen = build_screen()
    assert screen.legacy_pcb_hard_stop_intersection_mm3 > 10.0
    assert screen.legacy_support_hard_stop_intersection_mm3 > 1.0


def test_side_hall_candidate_clears_full_stem_travel_with_margin():
    screen = build_screen()
    assert screen.side_sensor_hard_stop_intersection_mm3 == 0.0
    assert screen.side_sensor_min_radial_clearance_to_stem_mm > 0.50


def test_sensor_travel_screen_keeps_electromagnetic_behavior_unvalidated():
    manifest = build_screen().manifest()
    assert manifest["schema"] == SCHEMA
    assert manifest["legacy_axial_hall"]["status"] == "REJECTED_FULL_TRAVEL_COLLISION"
    assert manifest["side_hall_candidate"]["packaging_status"] == "DIGITALLY_CLEAR_OF_STEM_FULL_TRAVEL"
    assert manifest["physical_validation_eligible"] is False
    assert "FIELD_MAP" in manifest["physical_validation"]
    assert "MONOTONICITY" in manifest["physical_validation"]
