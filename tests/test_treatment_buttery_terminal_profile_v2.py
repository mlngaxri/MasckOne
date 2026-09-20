from __future__ import annotations

from studies.treatment_buttery_terminal_profile_v2 import (
    CAM_TRAVEL_MM,
    ENTRY_OVERCLOSURE_MM,
    LEAF_THICKNESS_MM,
    LEAF_WIDTH_MM,
    PRELOAD_TARGET_N,
    X_CAM_PHASE_LEAD_MM,
    axis_design,
    build_manifest,
    event_phasing_screen,
    phased_cam_force_screen,
    previous_corner_margin_N,
    smootherstep_derivative,
    smootherstep_second_derivative,
)


def test_selected_profile_is_more_robust_than_previous_coarse_seed():
    x = axis_design("X")
    z = axis_design("Z")
    assert PRELOAD_TARGET_N == 0.40
    assert ENTRY_OVERCLOSURE_MM == 0.030
    assert CAM_TRAVEL_MM == 0.95
    assert X_CAM_PHASE_LEAD_MM == 0.16
    assert x.robustness_corner_contact_margin_N > 0.03
    assert z.robustness_corner_contact_margin_N > 0.01
    assert previous_corner_margin_N("Z") < 0.002
    assert z.robustness_corner_contact_margin_N > previous_corner_margin_N("Z") * 5.0


def test_quintic_profile_is_C2_at_entry_and_full_seat():
    for endpoint in (0.0, 1.0):
        assert abs(smootherstep_derivative(endpoint)) < 1e-12
        assert abs(smootherstep_second_derivative(endpoint)) < 1e-12


def test_axis_specific_parallel_springs_fit_current_study_window():
    x = axis_design("X")
    z = axis_design("Z")
    assert LEAF_WIDTH_MM == 0.80
    assert LEAF_THICKNESS_MM == 0.15
    assert 7.0 < z.effective_leaf_length_mm < x.effective_leaf_length_mm < 8.2
    assert x.backup_entry_force_N < 0.60
    assert z.backup_entry_force_N < 0.60
    assert x.backup_root_stress_proxy_MPa < 330.0
    assert z.backup_root_stress_proxy_MPa < 330.0


def test_phased_C2_cams_keep_takeup_subordinate_to_final_axial_event():
    cam = phased_cam_force_screen()
    phasing = event_phasing_screen()
    assert cam["combined_peak_ideal_axial_cam_force_N"] < 0.15
    assert cam["combined_peak_ideal_axial_cam_force_N"] < cam["current_axial_detent_force_proxy_N"]
    assert phasing["both_radial_axes_fully_preloaded_before_axial_event"] is True
    assert phasing["X_full_preload_lead_before_axial_event_mm"] > phasing[
        "Z_full_preload_lead_before_axial_event_mm"
    ]


def test_manifest_keeps_buttery_claims_inside_digital_evidence_firewall():
    manifest = build_manifest()
    assert manifest["selected_profile"]["cam_profile"] == "QUINTIC_C2_SMOOTHERSTEP"
    assert manifest["digital_checks"]["X_robustness_corner_margin_above_0p03N"] is True
    assert manifest["digital_checks"]["Z_robustness_corner_margin_above_0p01N"] is True
    assert manifest["digital_checks"]["C2_zero_slope_and_curvature_at_both_ends"] is True
    assert manifest["physical_validation_eligible"] is False
    assert manifest["physical_validation"].startswith("OPEN_")
