from dataclasses import replace
import math

import pytest

from masck_one.waste_fluid_accounting import build_authority_waste_fluid_budget
from masck_one.waste_fluid_limiting_event_capacity import screen_limiting_event_cartridge_capacity
from masck_one.waste_fluid_recovery_capacity_compatibility import (
    RecoveryCapacityCompatibilityError,
    evaluate_recovery_capacity_compatibility,
)


def _screen(budget, recovery=.90, residual=.08, leakage=.02):
    return screen_limiting_event_cartridge_capacity(
        budget,
        cycles=budget.service_cycles,
        prime_recovery_ratio_contract=recovery,
        prime_residual_ratio_contract=residual,
        prime_external_leakage_ratio_contract=leakage,
    )


def test_authority_contract_exposes_capacity_recovery_incompatibility():
    budget = build_authority_waste_fluid_budget()
    result = evaluate_recovery_capacity_compatibility(budget, _screen(budget))
    assert result.authority_recovery_floor_capacity_feasible is False
    assert result.full_nominal_recovery_capacity_feasible is False
    assert result.capacity_limited_nominal_recovery_ratio < result.authority_nominal_recovery_floor_ratio
    assert result.recovery_ratio_margin_above_authority_floor < 0.0
    assert result.recovered_reprime_reserved_mL > 0.0
    assert result.authority_recovery_floor_capacity_shortfall_mL > 0.0
    assert result.full_nominal_recovery_capacity_shortfall_mL >= result.authority_recovery_floor_capacity_shortfall_mL
    assert result.capacity_limited_service_cycles_at_authority_floor < budget.service_cycles
    assert result.capacity_limited_service_cycles_at_full_recovery <= result.capacity_limited_service_cycles_at_authority_floor
    assert result.authority_service_cycle_shortfall_at_recovery_floor > 0
    assert result.authority_service_cycle_shortfall_at_full_recovery >= result.authority_service_cycle_shortfall_at_recovery_floor


def test_larger_synthetic_capacity_can_accept_full_nominal_recovery():
    budget = replace(build_authority_waste_fluid_budget(), cartridge_retained_capacity_requirement_mL=40.0)
    result = evaluate_recovery_capacity_compatibility(budget, _screen(budget))
    assert result.authority_recovery_floor_capacity_feasible is True
    assert result.full_nominal_recovery_capacity_feasible is True
    assert result.capacity_limited_nominal_recovery_ratio == pytest.approx(1.0)
    assert result.recovery_ratio_margin_above_authority_floor >= 0.0
    assert result.authority_recovery_floor_capacity_shortfall_mL == 0.0
    assert result.full_nominal_recovery_capacity_shortfall_mL == 0.0
    assert result.capacity_limited_service_cycles_at_full_recovery >= budget.service_cycles
    assert result.authority_service_cycle_shortfall_at_recovery_floor == 0
    assert result.authority_service_cycle_shortfall_at_full_recovery == 0


def test_capacity_ceiling_reserves_recovered_reprime_before_nominal_recovery():
    budget = build_authority_waste_fluid_budget()
    screen = _screen(budget)
    result = evaluate_recovery_capacity_compatibility(budget, screen)
    assert result.reprime_only_capacity_margin_mL == pytest.approx(screen.retained_cartridge_capacity_mL - screen.prime_liquid_routed_to_cartridge_mL)
    assert result.capacity_available_for_nominal_recovery_mL == pytest.approx(max(result.reprime_only_capacity_margin_mL, 0.0))
    assert result.capacity_limited_nominal_recovery_ratio == pytest.approx(result.capacity_available_for_nominal_recovery_mL / result.nominal_introduced_service_mL)


def test_service_life_bounds_invert_remaining_capacity_per_cycle():
    budget = build_authority_waste_fluid_budget()
    result = evaluate_recovery_capacity_compatibility(budget, _screen(budget))
    floor_per_cycle = budget.nominal_introduced_mL_per_cycle * result.authority_nominal_recovery_floor_ratio
    expected_floor_cycles = math.floor((result.capacity_available_for_nominal_recovery_mL + 1e-12) / floor_per_cycle)
    expected_full_cycles = math.floor((result.capacity_available_for_nominal_recovery_mL + 1e-12) / budget.nominal_introduced_mL_per_cycle)
    assert result.capacity_limited_service_cycles_at_authority_floor == expected_floor_cycles
    assert result.capacity_limited_service_cycles_at_full_recovery == expected_full_cycles
    assert result.authority_service_cycle_shortfall_at_recovery_floor == max(budget.service_cycles - expected_floor_cycles, 0)
    assert result.authority_service_cycle_shortfall_at_full_recovery == max(budget.service_cycles - expected_full_cycles, 0)


def test_endpoint_capacity_minima_invert_recovery_accounting_exactly():
    budget = build_authority_waste_fluid_budget()
    result = evaluate_recovery_capacity_compatibility(budget, _screen(budget))
    expected_floor = result.recovered_reprime_reserved_mL + result.nominal_introduced_service_mL * result.authority_nominal_recovery_floor_ratio
    expected_full = result.recovered_reprime_reserved_mL + result.nominal_introduced_service_mL
    assert result.minimum_capacity_for_authority_recovery_floor_mL == pytest.approx(expected_floor)
    assert result.minimum_capacity_for_full_nominal_recovery_mL == pytest.approx(expected_full)
    assert result.authority_recovery_floor_capacity_shortfall_mL == pytest.approx(max(expected_floor - budget.cartridge_retained_capacity_requirement_mL, 0.0))
    assert result.full_nominal_recovery_capacity_shortfall_mL == pytest.approx(max(expected_full - budget.cartridge_retained_capacity_requirement_mL, 0.0))


def test_synthetic_capacity_below_reprime_load_is_reported_independently():
    authority = build_authority_waste_fluid_budget()
    authority_screen = _screen(authority)
    assert authority_screen.prime_liquid_routed_to_cartridge_mL > 0.0
    budget = replace(authority, cartridge_retained_capacity_requirement_mL=authority_screen.prime_liquid_routed_to_cartridge_mL / 2.0)
    result = evaluate_recovery_capacity_compatibility(budget, _screen(budget))
    assert result.reprime_only_capacity_exceeded is True
    assert result.reprime_only_capacity_margin_mL < 0.0
    assert result.capacity_available_for_nominal_recovery_mL == 0.0
    assert result.capacity_limited_nominal_recovery_ratio == 0.0
    assert result.capacity_limited_service_cycles_at_authority_floor == 0
    assert result.capacity_limited_service_cycles_at_full_recovery == 0
    assert result.authority_recovery_floor_capacity_feasible is False
    assert result.full_nominal_recovery_capacity_feasible is False
    assert result.authority_recovery_floor_capacity_shortfall_mL > 0.0


def test_rejects_capacity_screen_from_different_budget():
    budget = build_authority_waste_fluid_budget()
    altered = replace(budget, cartridge_retained_capacity_requirement_mL=40.0)
    with pytest.raises(RecoveryCapacityCompatibilityError, match="retained capacity disagrees"):
        evaluate_recovery_capacity_compatibility(altered, _screen(budget))


def test_rejects_partial_service_window_before_making_service_life_claim():
    budget = build_authority_waste_fluid_budget()
    partial = screen_limiting_event_cartridge_capacity(
        budget,
        cycles=budget.service_cycles - 1,
        prime_recovery_ratio_contract=.90,
        prime_residual_ratio_contract=.08,
        prime_external_leakage_ratio_contract=.02,
    )
    with pytest.raises(RecoveryCapacityCompatibilityError, match="exactly the authority service cycle count"):
        evaluate_recovery_capacity_compatibility(budget, partial)


def test_rejects_wrong_evidence_type():
    with pytest.raises(TypeError, match="LimitingEventCapacityScreen"):
        evaluate_recovery_capacity_compatibility(build_authority_waste_fluid_budget(), object())
