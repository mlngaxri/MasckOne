from __future__ import annotations

import math

from studies.treatment_terminal_seating_profile import (
    AXIS_PRELOAD_TARGET_N,
    CAM_ACQUISITION_TRAVEL_MM,
    CONTINUOUS_REACTION_REFERENCE_N,
    LOSSY_BACKUP_GAP_MM,
    TRANSIENT_REACTION_REFERENCE_N,
    abnormal_reverse_travel_screen,
    build_manifest,
    spring_leaf_screen,
    terminal_cam_profile,
)


def test_terminal_preload_has_meaningful_continuous_contact_margin():
    spring = spring_leaf_screen()
    assert AXIS_PRELOAD_TARGET_N == 0.30
    assert spring["preload_target_N"] > CONTINUOUS_REACTION_REFERENCE_N
    assert math.isclose(
        spring["preload_target_N"] - CONTINUOUS_REACTION_REFERENCE_N,
        0.10,
        abs_tol=1e-12,
    )
    assert 0.14 < spring["preload_deflection_seed_mm"] < 0.18
    assert spring["preload_root_stress_proxy_MPa"] < 350.0


def test_s_curve_cam_starts_and_finishes_without_slope_impulse():
    profile = terminal_cam_profile()
    rows = profile["rows"]
    assert CAM_ACQUISITION_TRAVEL_MM == 0.65
    assert rows[0]["radial_deflection_mm"] == 0.0
    assert rows[0]["ideal_frictionless_axial_cam_force_N"] == 0.0
    assert math.isclose(rows[-1]["radial_force_N"], AXIS_PRELOAD_TARGET_N, rel_tol=1e-12)
    assert rows[-1]["ideal_frictionless_axial_cam_force_N"] == 0.0
    assert profile["per_axis_peak_ideal_frictionless_axial_cam_force_N"] < 0.08
    assert profile["two_axis_peak_upper_bound_if_coincident_N"] < 0.16


def test_abnormal_load_uses_lossy_backup_before_rigid_stop():
    screen = abnormal_reverse_travel_screen()
    assert LOSSY_BACKUP_GAP_MM == 0.04
    assert screen["normal_40hz_should_not_reach_backup"] is True
    assert screen["backup_should_engage_before_transient_reference"] is True
    assert screen["hard_stop_proxy_reaches_transient_reference"] is True
    assert screen["force_at_lossy_backup_entry_N"] < TRANSIENT_REACTION_REFERENCE_N
    assert screen["combined_force_at_hard_stop_proxy_N"] >= TRANSIENT_REACTION_REFERENCE_N


def test_manifest_encodes_low_drag_then_terminal_precision_not_tight_rail():
    manifest = build_manifest()
    assert manifest["physical_validation_eligible"] is False
    assert manifest["selected_seating_sequence"].startswith("FREE_CLEARANCE_RAIL")
    assert "ZERO_SLOPE_S_CURVE_TERMINAL_CAM" in manifest["selected_seating_sequence"]
    assert "LOSSY_BACKUP" in manifest["selected_abnormal_load_sequence"]
    assert manifest["buttery_mechanics_rule"].startswith("DO_NOT_REMOVE_RAIL_CLEARANCE")
    assert manifest["physical_validation"].startswith("OPEN_")
