from __future__ import annotations

import math

from studies.treatment_parallel_preload_flexure import (
    CAM_TRAVEL_MM,
    CONTINUOUS_REACTION_REFERENCE_N,
    ENTRY_OVERCLOSURE_MM,
    FULL_SEAT_PRELOAD_N,
    LOSSY_BACKUP_TRAVEL_SEED_MM,
    TRANSIENT_REACTION_REFERENCE_N,
    build_axis,
    build_manifest,
    force_profile,
)


def test_axes_are_independently_tuned_to_same_seated_preload():
    x = build_axis("X")
    z = build_axis("Z")
    assert x.target_deflection_mm > z.target_deflection_mm
    assert x.required_pair_stiffness_N_per_mm < z.required_pair_stiffness_N_per_mm
    assert math.isclose(x.seated_preload_N, FULL_SEAT_PRELOAD_N, rel_tol=1e-12)
    assert math.isclose(z.seated_preload_N, FULL_SEAT_PRELOAD_N, rel_tol=1e-12)
    assert x.continuous_contact_margin_N > 0.09
    assert z.continuous_contact_margin_N > 0.09
    assert FULL_SEAT_PRELOAD_N > CONTINUOUS_REACTION_REFERENCE_N


def test_entry_force_is_small_and_force_profile_has_zero_endpoint_gradient():
    for axis in ("X", "Z"):
        row = build_axis(axis)
        profile = force_profile(axis, 41)
        assert profile[0]["axial_travel_mm"] == 0.0
        assert math.isclose(profile[-1]["axial_travel_mm"], CAM_TRAVEL_MM, rel_tol=1e-12)
        assert row.entry_force_N < 0.015
        assert profile[0]["force_gradient_N_per_mm"] == 0.0
        assert profile[-1]["force_gradient_N_per_mm"] == 0.0
        assert all(
            profile[i + 1]["preload_force_N"] >= profile[i]["preload_force_N"]
            for i in range(len(profile) - 1)
        )


def test_axis_tuning_matches_mid_travel_force_gradient():
    x = build_axis("X")
    z = build_axis("Z")
    # The different stiffnesses intentionally compensate the different clearances.
    assert abs(x.maximum_cam_force_gradient_N_per_mm - z.maximum_cam_force_gradient_N_per_mm) < 0.02


def test_lossy_backup_engages_after_normal_load_and_before_transient_reference():
    for axis in ("X", "Z"):
        row = build_axis(axis)
        assert LOSSY_BACKUP_TRAVEL_SEED_MM > 0.0
        assert row.backup_first_engagement_force_N > FULL_SEAT_PRELOAD_N
        assert row.backup_first_engagement_force_N < TRANSIENT_REACTION_REFERENCE_N
        assert row.leaf_root_stress_proxy_backup_MPa > row.leaf_root_stress_proxy_seated_MPa


def test_manifest_keeps_buttery_claim_as_design_intent_not_physical_evidence():
    manifest = build_manifest()
    assert manifest["physical_validation_eligible"] is False
    assert "AXIS_SPECIFIC_STIFFNESS" in manifest["selected_direction"]
    assert "ZERO_SLOPE_CAM_ENDPOINTS" in manifest["buttery_reasoning"]
    assert manifest["physical_validation"].startswith("OPEN_")
    assert ENTRY_OVERCLOSURE_MM > 0.0
