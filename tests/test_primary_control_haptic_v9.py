from __future__ import annotations

from masck_one import primary_control_haptic as v1
from masck_one.primary_control_haptic_v9 import (
    DOME_BOTTOM_EVENT_MM,
    DOME_MAX_ACTUATOR_FRACTION,
    LOST_MOTION_TO_HARD_STOP_MM,
    MAX_INCREMENTAL_LOST_MOTION_FORCE_N,
    MIN_BROAD_STEM_TO_DOME_CLEARANCE_AT_HARD_STOP_MM,
    MIN_SPRING_SOLID_CLEARANCE_MM,
    MIN_STEM_BEHIND_LOWER_GUIDE_AT_REST_MM,
    SCHEMA,
    SOURCE_MAIN_SHA,
    build_primary_control_haptic_architecture_v9,
)


def test_v9_builds_valid_low_part_count_tactile_cartridge():
    architecture = build_primary_control_haptic_architecture_v9()
    material = dict(architecture.material_parts)
    refs = dict(architecture.reference_parts)

    assert architecture.source_main_sha == SOURCE_MAIN_SHA
    assert architecture.physical_validation_eligible is False
    assert all(shape.isValid() and shape.Solids() for _name, shape in architecture.material_parts)
    assert "tactile_lost_motion_plunger" in material
    assert len(material["tactile_lost_motion_plunger"].Solids()) == 1
    assert material["tactile_lost_motion_plunger"].Volume() > 0.0
    for rejected in ("tactile_spring_formed", "tactile_damping_annulus", "tactile_snap_retainer"):
        assert rejected not in material
    assert "tactile_dome_coupon_conservative_envelope" in refs
    assert "tactile_dome_retention_film_reference" in refs
    assert "lost_motion_spring_envelope_reference" in refs


def test_v9_preserves_lower_guide_then_protects_dome_from_long_stroke():
    architecture = build_primary_control_haptic_architecture_v9()

    assert architecture.stem_behind_lower_guide_at_rest_mm >= MIN_STEM_BEHIND_LOWER_GUIDE_AT_REST_MM
    assert (
        architecture.broad_stem_to_dome_clearance_at_hard_stop_mm
        >= MIN_BROAD_STEM_TO_DOME_CLEARANCE_AT_HARD_STOP_MM
    )
    assert architecture.main_hard_dome_intersection_mm3 == 0.0
    assert DOME_BOTTOM_EVENT_MM < v1.NOMINAL_BOTTOM_MM < v1.HARD_STOP_MM
    assert LOST_MOTION_TO_HARD_STOP_MM > 0.0


def test_v9_captive_plunger_has_zero_forbidden_collision_at_rest_and_hard_endpoints():
    architecture = build_primary_control_haptic_architecture_v9()

    assert architecture.plunger_cavity_removed_mm3 > 0.0
    assert architecture.plunger_rest_moving_intersection_mm3 == 0.0
    assert architecture.plunger_hard_moving_intersection_mm3 == 0.0
    assert architecture.plunger_rest_shell_intersection_mm3 == 0.0
    assert architecture.plunger_bottom_shell_intersection_mm3 == 0.0
    assert architecture.dome_actuator_fraction <= DOME_MAX_ACTUATOR_FRACTION


def test_v9_lost_motion_spring_screen_stays_preloaded_clear_of_solid_and_low_rate():
    architecture = build_primary_control_haptic_architecture_v9()
    screen = architecture.spring_metrics

    assert screen["rest_preload_compression_mm"] > 0.0
    assert screen["rest_preload_force_proxy_N"] > 0.0
    assert screen["solid_height_clearance_mm"] >= MIN_SPRING_SOLID_CLEARANCE_MM
    assert screen["incremental_force_over_lost_motion_N"] <= MAX_INCREMENTAL_LOST_MOTION_FORCE_N


def test_v9_keeps_released_package_clear_and_evidence_firewall_closed():
    architecture = build_primary_control_haptic_architecture_v9()
    manifest = architecture.manifest()

    assert manifest["schema"] == SCHEMA
    assert max(architecture.rear_extension_keepout_intersections_mm3.values(), default=0.0) == 0.0
    assert max(architecture.keepout_intersections_mm3.values(), default=0.0) == 0.0
    assert manifest["physical_validation_eligible"] is False
    assert manifest["dome_coupon_benchmark"]["production_selected"] is False
    assert "PRECISION_FEEL_ONLY" in manifest["tactile_reference_rule"]
    assert "SUBJECTIVE_FEEL" in manifest["physical_validation"]
