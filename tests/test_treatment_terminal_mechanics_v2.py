from __future__ import annotations

from studies.treatment_terminal_mechanics_v2 import (
    PRELOAD_TARGET_N,
    TRANSIENT_REACTION_REFERENCE_N,
    axis_design,
    build_manifest,
    contact_equilibrium_screen,
)


def test_terminal_preload_pairs_remove_the_preload_couple_by_geometry():
    row = contact_equilibrium_screen()
    assert row["X_master_preload_Z_offset_mm"] == 0.0
    assert row["Z_master_preload_X_offset_mm"] == 0.0
    assert row["preload_only_resultant_moment_about_Y_Nmm"] == 0.0
    assert row["moment_balance_closed_by_geometry"] is True


def test_axis_separated_pairs_supply_real_rotational_guidance():
    for axis in ("X", "Z"):
        row = axis_design(axis)
        assert abs(row.seated_force_N - PRELOAD_TARGET_N) < 1e-10
        assert row.guided_to_fixed_ratio > 0.95
        assert row.guided_stiffness_N_per_mm > 3.5 * row.free_rotation_stiffness_N_per_mm
        assert row.hostile_contact_margin_N > 0.0
        assert row.backup_entry_force_N < TRANSIENT_REACTION_REFERENCE_N


def test_selected_terminal_force_profile_stays_subordinate_to_final_axial_event():
    manifest = build_manifest()
    checks = manifest["digital_checks"]
    assert checks["preload_couple_removed_by_geometry"] is True
    assert checks["X_guidance_above_95pct_fixed_tip"] is True
    assert checks["Z_guidance_above_95pct_fixed_tip"] is True
    assert checks["combined_cam_peak_below_0p15N"] is True
    assert checks["combined_cam_peak_subordinate_to_axial_event"] is True
    assert checks["both_backup_entries_below_transient_reference"] is True
    assert manifest["physical_validation_eligible"] is False
