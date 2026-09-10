from __future__ import annotations

from masck_one import primary_control_haptic as v1
from masck_one import primary_control_haptic_v9 as v9
from masck_one import primary_control_haptic_v10 as v10
from masck_one.primary_control_haptic_v11 import (
    DOME_BOTTOM_EVENT_MM,
    LOST_MOTION_TO_HARD_STOP_MM,
    MAX_INCREMENTAL_LOST_MOTION_FORCE_N,
    MAX_PRECONTACT_DEAD_TRAVEL_MM,
    MIN_SPRING_SOLID_CLEARANCE_MM,
    PLUNGER_REST_GAP_TO_DOME_MM,
    SCHEMA,
    build_primary_control_haptic_architecture_v11,
)


def test_v11_removes_large_precontact_dead_travel_without_moving_sensor_package():
    architecture = build_primary_control_haptic_architecture_v11()
    manifest = architecture.manifest()
    correction = manifest["tactile_slack_correction"]

    assert manifest["schema"] == SCHEMA
    assert manifest["supersedes"] == v10.SCHEMA
    assert v9.PLUNGER_REST_GAP_TO_DOME_MM == 0.22
    assert 0.0 < PLUNGER_REST_GAP_TO_DOME_MM <= MAX_PRECONTACT_DEAD_TRAVEL_MM
    assert correction["v11_rest_gap_mm"] == PLUNGER_REST_GAP_TO_DOME_MM
    assert correction["spring_chamber_extended"] is False
    assert correction["side_hall_package_relocated"] is False


def test_v11_rebalanced_spring_keeps_preload_solid_clearance_and_low_post_snap_force():
    architecture = build_primary_control_haptic_architecture_v11()
    metrics = architecture.spring_metrics

    assert metrics["rest_preload_compression_mm"] > 0.0
    assert metrics["solid_height_clearance_mm"] >= MIN_SPRING_SOLID_CLEARANCE_MM
    assert metrics["incremental_force_over_lost_motion_N"] <= MAX_INCREMENTAL_LOST_MOTION_FORCE_N
    assert metrics["wire_diameter_mm"] == 0.12
    assert metrics["total_coils_seed"] == 4.0
    assert DOME_BOTTOM_EVENT_MM == PLUNGER_REST_GAP_TO_DOME_MM + v9.DOME_HEIGHT_MM
    assert LOST_MOTION_TO_HARD_STOP_MM == v1.HARD_STOP_MM - DOME_BOTTOM_EVENT_MM


def test_v11_near_contact_plunger_remains_collision_free_through_event_and_package():
    architecture = build_primary_control_haptic_architecture_v11()

    assert architecture.plunger_rest_moving_intersection_mm3 == 0.0
    assert architecture.plunger_event_moving_intersection_mm3 == 0.0
    assert architecture.plunger_rest_shell_intersection_mm3 == 0.0
    assert architecture.plunger_event_shell_intersection_mm3 == 0.0
    assert max(architecture.keepout_intersections_mm3.values(), default=0.0) == 0.0


def test_v11_preserves_v10_positive_capture_and_compliant_return_hierarchy():
    architecture = build_primary_control_haptic_architecture_v11()
    predecessor = architecture.predecessor
    manifest = architecture.manifest()

    assert predecessor.capture_flange_root_overlap_mm3 > 0.0
    assert predecessor.capture_rest_bushing_intersection_mm3 == 0.0
    assert predecessor.capture_at_nominal_limit_intersection_mm3 == 0.0
    assert predecessor.capture_hostile_overpull_intersection_mm3 > 0.0
    assert predecessor.installed_diaphragm_shell_intersection_mm3 == 0.0
    assert predecessor.installed_diaphragm_moving_intersection_mm3 == 0.0
    assert "POSITIVE_ABUSE_CAPTURE" in manifest["tactile_sequence"]


def test_v11_keeps_physical_validation_and_cost_firewalls():
    manifest = build_primary_control_haptic_architecture_v11().manifest()

    assert manifest["physical_validation_eligible"] is False
    assert "SPRING_SUPPLIER" in manifest["physical_validation"]
    assert "SUBJECTIVE_FEEL" in manifest["physical_validation"]
    assert "NO_SENSOR_MOVE" in manifest["cost_rule"]
    assert "PRECISION_FEEL_ONLY" in manifest["tactile_reference_rule"]
