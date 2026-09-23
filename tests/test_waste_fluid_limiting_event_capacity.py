import pytest

from masck_one.waste_fluid_accounting import build_authority_waste_fluid_budget
from masck_one.waste_fluid_limiting_event_capacity import screen_limiting_event_cartridge_capacity


def test_capacity_limited_contract_exposes_negative_worst_case_capacity_margin():
    budget = build_authority_waste_fluid_budget()
    screen = screen_limiting_event_cartridge_capacity(
        budget,
        cycles=6,
        prime_recovery_ratio_contract=.90,
        prime_residual_ratio_contract=.08,
        prime_external_leakage_ratio_contract=.02,
    )
    assert screen.service_envelope.controlling_constraint == "CARTRIDGE_CAPACITY"
    assert screen.limiting_prime_events == 26
    assert screen.nominal_liquid_at_maximum_recovery_mL == pytest.approx(
        6 * budget.nominal_introduced_mL_per_cycle
    )
    assert screen.nominal_only_cartridge_overflow_mL == pytest.approx(0.0)
    assert screen.nominal_only_cartridge_headroom_mL == pytest.approx(
        budget.cartridge_retained_capacity_requirement_mL
        - screen.nominal_liquid_at_maximum_recovery_mL
    )
    assert screen.prime_cartridge_capacity_allowance_mL == pytest.approx(
        screen.nominal_only_cartridge_headroom_mL
    )
    assert screen.prime_liquid_routed_to_cartridge_mL == pytest.approx(
        26 * budget.maximum_initial_prime_mL_per_cycle * .90
    )
    assert screen.prime_cartridge_allowance_margin_mL == pytest.approx(
        screen.prime_cartridge_capacity_allowance_mL
        - screen.prime_liquid_routed_to_cartridge_mL
    )
    assert screen.prime_cartridge_allowance_margin_mL < 0.0
    assert screen.cartridge_demand_at_maximum_nominal_recovery_mL == pytest.approx(
        screen.nominal_liquid_at_maximum_recovery_mL + screen.prime_liquid_routed_to_cartridge_mL
    )
    assert screen.cartridge_margin_at_maximum_nominal_recovery_mL == pytest.approx(
        budget.cartridge_retained_capacity_requirement_mL
        - screen.cartridge_demand_at_maximum_nominal_recovery_mL
    )
    assert screen.cartridge_headroom_at_maximum_nominal_recovery_mL == pytest.approx(0.0)
    assert screen.cartridge_overflow_at_maximum_nominal_recovery_mL == pytest.approx(
        -screen.cartridge_margin_at_maximum_nominal_recovery_mL
    )
    assert screen.cartridge_overflow_at_maximum_nominal_recovery_mL == pytest.approx(
        -screen.prime_cartridge_allowance_margin_mL
    )
    assert screen.cartridge_utilization_at_maximum_nominal_recovery == pytest.approx(
        screen.cartridge_demand_at_maximum_nominal_recovery_mL
        / budget.cartridge_retained_capacity_requirement_mL
    )
    assert screen.cartridge_utilization_at_maximum_nominal_recovery > 1.0
    assert screen.cartridge_capacity_exceeded_at_maximum_nominal_recovery is True


def test_sink_first_contract_proves_cartridge_headroom_at_limiting_event():
    budget = build_authority_waste_fluid_budget()
    screen = screen_limiting_event_cartridge_capacity(
        budget,
        cycles=6,
        prime_recovery_ratio_contract=0.0,
        prime_residual_ratio_contract=1.0,
        prime_external_leakage_ratio_contract=0.0,
    )
    assert screen.service_envelope.controlling_constraint == "RESIDUAL_CEILING"
    assert screen.limiting_prime_events == 7
    assert screen.prime_liquid_routed_to_cartridge_mL == pytest.approx(0.0)
    assert screen.cartridge_demand_at_maximum_nominal_recovery_mL == pytest.approx(
        6 * budget.nominal_introduced_mL_per_cycle
    )
    assert screen.nominal_only_cartridge_overflow_mL == pytest.approx(0.0)
    assert screen.prime_cartridge_capacity_allowance_mL == pytest.approx(7.4)
    assert screen.prime_cartridge_allowance_margin_mL == pytest.approx(7.4)
    assert screen.cartridge_margin_at_maximum_nominal_recovery_mL == pytest.approx(7.4)
    assert screen.cartridge_headroom_at_maximum_nominal_recovery_mL == pytest.approx(7.4)
    assert screen.cartridge_overflow_at_maximum_nominal_recovery_mL == pytest.approx(0.0)
    assert screen.cartridge_utilization_at_maximum_nominal_recovery < 1.0
    assert screen.cartridge_capacity_exceeded_at_maximum_nominal_recovery is False


def test_all_prime_recovery_capacity_screen_conserves_liquid_volume():
    budget = build_authority_waste_fluid_budget()
    screen = screen_limiting_event_cartridge_capacity(
        budget,
        cycles=6,
        prime_recovery_ratio_contract=1.0,
        prime_residual_ratio_contract=0.0,
        prime_external_leakage_ratio_contract=0.0,
    )
    expected = (
        6 * budget.nominal_introduced_mL_per_cycle
        + screen.limiting_prime_events * budget.maximum_initial_prime_mL_per_cycle
    )
    assert screen.cartridge_demand_at_maximum_nominal_recovery_mL == pytest.approx(expected)
    assert screen.retained_cartridge_capacity_mL == pytest.approx(
        budget.cartridge_retained_capacity_requirement_mL
    )
    assert screen.cartridge_headroom_at_maximum_nominal_recovery_mL * screen.cartridge_overflow_at_maximum_nominal_recovery_mL == pytest.approx(0.0)
    assert screen.nominal_only_cartridge_headroom_mL * screen.nominal_only_cartridge_overflow_mL == pytest.approx(0.0)
