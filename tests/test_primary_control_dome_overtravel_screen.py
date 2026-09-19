from __future__ import annotations

from studies.primary_control_dome_overtravel_screen import (
    BENCHMARK_MAX_ACTUATOR_DIAMETER_MM,
    M_SERIES_DESIGNED_OVERTRAVEL_MM,
    SCHEMA,
    build_screen,
)


def test_direct_standard_dome_is_rejected_even_with_optimistic_travel_bound():
    screen = build_screen()
    assert 0.0 <= screen.rest_gap_mm <= 0.05
    assert screen.rest_gap_mm == 0.01
    assert screen.lower_bound_extra_travel_to_nominal_bottom_mm > 0.50
    assert screen.lower_bound_extra_travel_to_hard_stop_mm > 0.65
    assert screen.direct_f_series_viable is False


def test_m_series_standard_overtravel_allowance_still_does_not_cover_button_stroke():
    screen = build_screen()
    assert screen.m_series_overtravel_allowance_mm == round(M_SERIES_DESIGNED_OVERTRAVEL_MM, 9)
    assert screen.direct_m_series_allowance_sufficient is False
    assert screen.required_lost_motion_to_nominal_bottom_mm > screen.m_series_overtravel_allowance_mm


def test_dome_route_requires_small_centered_actuator_and_deliberate_lost_motion():
    manifest = build_screen().manifest()
    change = manifest["required_architecture_change"]

    assert manifest["schema"] == SCHEMA
    assert BENCHMARK_MAX_ACTUATOR_DIAMETER_MM <= 1.75
    assert change["lost_motion_or_compliance_to_nominal_bottom_mm_min"] > 0.50
    assert change["lost_motion_or_compliance_to_hard_stop_mm_min"] > 0.65
    assert "NO_RIGID_DIRECT_PLUNGER" in change["direction"]
    assert manifest["physical_validation_eligible"] is False
