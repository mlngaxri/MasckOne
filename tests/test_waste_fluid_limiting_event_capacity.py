import pytest

from masck_one.waste_fluid_accounting import WasteFluidAccountingError, build_authority_waste_fluid_budget
from masck_one.waste_fluid_limiting_event_capacity import screen_limiting_event_cartridge_capacity


def _screen(recovery=.90, residual=.08, leakage=.02):
    return screen_limiting_event_cartridge_capacity(
        build_authority_waste_fluid_budget(), cycles=6,
        prime_recovery_ratio_contract=recovery,
        prime_residual_ratio_contract=residual,
        prime_external_leakage_ratio_contract=leakage,
    )


def test_capacity_limited_contract_separates_authority_floor_from_maximum_recovery_load():
    budget = build_authority_waste_fluid_budget()
    screen = _screen()
    assert screen.service_envelope.controlling_constraint == "CARTRIDGE_CAPACITY"
    assert screen.limiting_prime_events == 26
    assert screen.authority_floor_nominal_recovery_mL == pytest.approx(6 * budget.minimum_recovered_mL_per_cycle)
    assert screen.prime_liquid_routed_to_cartridge_mL == pytest.approx(26 * budget.maximum_initial_prime_mL_per_cycle * .90)
    assert screen.authority_floor_cartridge_demand_mL == pytest.approx(
        screen.authority_floor_nominal_recovery_mL + screen.prime_liquid_routed_to_cartridge_mL
    )
    assert screen.authority_floor_cartridge_margin_mL == pytest.approx(
        budget.cartridge_retained_capacity_requirement_mL - screen.authority_floor_cartridge_demand_mL
    )
    assert screen.authority_floor_cartridge_headroom_mL == pytest.approx(max(screen.authority_floor_cartridge_margin_mL, 0.0))
    assert screen.authority_floor_cartridge_overflow_mL == pytest.approx(max(-screen.authority_floor_cartridge_margin_mL, 0.0))
    assert screen.authority_floor_cartridge_utilization == pytest.approx(
        screen.authority_floor_cartridge_demand_mL / budget.cartridge_retained_capacity_requirement_mL
    )
    assert screen.authority_floor_cartridge_capacity_exceeded is True
    assert screen.authority_floor_cartridge_headroom_mL == pytest.approx(0.0)
    assert screen.nominal_recovery_uplift_to_maximum_mL == pytest.approx(
        6 * (budget.nominal_introduced_mL_per_cycle - budget.minimum_recovered_mL_per_cycle)
    )
    assert screen.cartridge_demand_at_maximum_nominal_recovery_mL - screen.authority_floor_cartridge_demand_mL == pytest.approx(
        screen.nominal_recovery_uplift_to_maximum_mL
    )
    assert screen.nominal_only_cartridge_overflow_mL == pytest.approx(0.0)
    assert screen.prime_incremental_cartridge_overflow_mL == pytest.approx(-screen.prime_cartridge_allowance_margin_mL)
    assert screen.cartridge_overflow_at_maximum_nominal_recovery_mL == pytest.approx(
        screen.nominal_only_cartridge_overflow_mL + screen.prime_incremental_cartridge_overflow_mL
    )
    assert screen.cartridge_utilization_at_maximum_nominal_recovery > 1.0
    assert screen.cartridge_capacity_exceeded_at_maximum_nominal_recovery is True


def test_sink_first_contract_proves_cartridge_headroom_at_limiting_event():
    budget = build_authority_waste_fluid_budget()
    screen = _screen(0.0, 1.0, 0.0)
    assert screen.service_envelope.controlling_constraint == "RESIDUAL_CEILING"
    assert screen.limiting_prime_events == 7
    assert screen.prime_liquid_routed_to_cartridge_mL == pytest.approx(0.0)
    assert screen.authority_floor_cartridge_demand_mL == pytest.approx(6 * budget.minimum_recovered_mL_per_cycle)
    assert screen.authority_floor_cartridge_overflow_mL == pytest.approx(0.0)
    assert screen.authority_floor_cartridge_headroom_mL > 0.0
    assert screen.authority_floor_cartridge_utilization < 1.0
    assert screen.authority_floor_cartridge_capacity_exceeded is False
    assert screen.cartridge_demand_at_maximum_nominal_recovery_mL == pytest.approx(6 * budget.nominal_introduced_mL_per_cycle)
    assert screen.prime_cartridge_capacity_allowance_mL == pytest.approx(7.4)
    assert screen.prime_cartridge_allowance_margin_mL == pytest.approx(7.4)
    assert screen.prime_incremental_cartridge_overflow_mL == pytest.approx(0.0)
    assert screen.cartridge_margin_at_maximum_nominal_recovery_mL == pytest.approx(7.4)
    assert screen.cartridge_overflow_at_maximum_nominal_recovery_mL == pytest.approx(0.0)
    assert screen.cartridge_capacity_exceeded_at_maximum_nominal_recovery is False


def test_all_prime_recovery_capacity_screen_conserves_liquid_volume():
    budget = build_authority_waste_fluid_budget()
    screen = _screen(1.0, 0.0, 0.0)
    expected = 6 * budget.nominal_introduced_mL_per_cycle + screen.limiting_prime_events * budget.maximum_initial_prime_mL_per_cycle
    assert screen.cartridge_demand_at_maximum_nominal_recovery_mL == pytest.approx(expected)
    assert screen.cartridge_headroom_at_maximum_nominal_recovery_mL * screen.cartridge_overflow_at_maximum_nominal_recovery_mL == pytest.approx(0.0)
    assert screen.authority_floor_cartridge_headroom_mL * screen.authority_floor_cartridge_overflow_mL == pytest.approx(0.0)
    assert screen.nominal_only_cartridge_headroom_mL * screen.nominal_only_cartridge_overflow_mL == pytest.approx(0.0)
    assert screen.cartridge_overflow_at_maximum_nominal_recovery_mL == pytest.approx(
        screen.nominal_only_cartridge_overflow_mL + screen.prime_incremental_cartridge_overflow_mL
    )


def test_capacity_screen_rejects_service_interval_beyond_authority_life():
    budget = build_authority_waste_fluid_budget()
    with pytest.raises(WasteFluidAccountingError, match="exceeds configured service life"):
        screen_limiting_event_cartridge_capacity(
            budget, cycles=budget.service_cycles + 1,
            prime_recovery_ratio_contract=.90,
            prime_residual_ratio_contract=.08,
            prime_external_leakage_ratio_contract=.02,
        )
