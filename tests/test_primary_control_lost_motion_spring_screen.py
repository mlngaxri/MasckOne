from __future__ import annotations

from studies.primary_control_lost_motion_spring_screen import (
    MAX_INCREMENTAL_FORCE_OVER_RELATIVE_TRAVEL_N,
    MIN_SOLID_CLEARANCE_MM,
    SCHEMA,
    build_screen,
)


def test_lost_motion_spring_stays_preloaded_and_above_solid_height():
    screen = build_screen()
    assert screen.rest_preload_compression_mm > 0.0
    assert screen.rest_preload_force_proxy_N > 0.0
    assert screen.solid_height_clearance_mm >= MIN_SOLID_CLEARANCE_MM


def test_lost_motion_spring_adds_only_small_first_order_post_snap_force():
    screen = build_screen()
    assert screen.incremental_force_over_relative_travel_N <= MAX_INCREMENTAL_FORCE_OVER_RELATIVE_TRAVEL_N
    assert screen.incremental_force_over_relative_travel_N < 0.06
    assert screen.package_viable_for_coupon is True


def test_lost_motion_spring_screen_keeps_dynamic_behavior_unvalidated():
    manifest = build_screen().manifest()
    assert manifest["schema"] == SCHEMA
    assert manifest["derived"]["package_viable_for_coupon"] is True
    assert "NO_DIRECT_METAL_TO_SHELL_REACTION_PATH" in manifest["acoustic_rule"]
    assert manifest["physical_validation_eligible"] is False
    assert "RING_TWANG" in manifest["physical_validation"]
