from __future__ import annotations

from studies.primary_control_spring_geometry_screen import (
    MAX_CREDIBLE_PROXY_TO_TARGET_RATIO,
    SCHEMA,
    build_screen,
)


def test_current_short_beam_tactile_spring_fails_order_of_magnitude_force_screen():
    screen = build_screen()

    assert screen.geometry_force_credibility_pass is False
    assert screen.proxy_to_target_ratio > MAX_CREDIBLE_PROXY_TO_TARGET_RATIO
    assert screen.four_beam_bending_stiffness_N_per_mm > screen.target_average_rise_stiffness_N_per_mm


def test_screen_remains_an_evidence_firewall_not_a_force_prediction():
    manifest = build_screen().manifest()

    assert manifest["schema"] == SCHEMA
    assert manifest["decision"] == "REJECT_CURRENT_SHORT_BEAM_GEOMETRY_AS_FORCE_DERIVED_TACTILE_SOLUTION"
    assert manifest["method"].startswith("COMPLIANCE_FAVOURING_FIXED_FREE_LINEAR_BENDING_SCREEN_ONLY")
    assert manifest["physical_validation_eligible"] is False
    assert "NONLINEAR_FORCE_TRAVEL_ANALYSIS_WITH_MATERIAL_AND_FORMING_ASSUMPTIONS" in manifest["required_next_evidence"]
    assert "PHYSICAL_FORCE_TRAVEL_HYSTERESIS_AND_LIFETIME_COUPON" in manifest["required_next_evidence"]
