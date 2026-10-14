from dataclasses import replace

import pytest

from masck_one.waste_fluid_accounting import (
    WasteFluidAccountingError,
    build_authority_waste_fluid_budget,
)
from masck_one.waste_fluid_overflow_authority import validate_overflow_guard_authority
from masck_one.waste_fluid_overflow_guard import screen_cartridge_overflow_guard


def _guard(budget=None, *, prime_events_by_cycle=None):
    budget = budget or build_authority_waste_fluid_budget()
    if prime_events_by_cycle is None:
        prime_events_by_cycle = [1] * budget.service_cycles
    return screen_cartridge_overflow_guard(
        budget,
        prime_events_by_cycle=prime_events_by_cycle,
        prime_recovery_ratio_contract=0.90,
        prime_residual_ratio_contract=0.08,
        prime_external_leakage_ratio_contract=0.02,
    )


def test_authority_guard_binds_to_budget():
    budget = build_authority_waste_fluid_budget()
    guard = _guard(budget)
    validate_overflow_guard_authority(budget, guard)


def test_rejects_partial_service_trajectory_as_overflow_authority():
    budget = build_authority_waste_fluid_budget()
    guard = _guard(budget, prime_events_by_cycle=[1] * (budget.service_cycles - 1))
    with pytest.raises(WasteFluidAccountingError, match="complete authority service life"):
        validate_overflow_guard_authority(budget, guard)


def test_rejects_internally_valid_guard_from_different_capacity_authority():
    budget = build_authority_waste_fluid_budget()
    alternate = replace(budget, cartridge_retained_capacity_requirement_mL=36.0)
    guard = _guard(alternate)
    with pytest.raises(WasteFluidAccountingError, match="retained capacity"):
        validate_overflow_guard_authority(budget, guard)


def test_rejects_internally_valid_guard_from_different_delivery_authority():
    budget = build_authority_waste_fluid_budget()
    alternate = replace(
        budget,
        nominal_introduced_mL_per_cycle=4.5,
        recovery_ratio_min=0.90,
    )
    guard = screen_cartridge_overflow_guard(
        alternate,
        prime_events_by_cycle=[1] * 6,
        prime_recovery_ratio_contract=0.90,
        prime_residual_ratio_contract=0.08,
        prime_external_leakage_ratio_contract=0.02,
    )
    with pytest.raises(WasteFluidAccountingError, match="service routing|cycle routing|inflow trajectory"):
        validate_overflow_guard_authority(budget, guard)


def test_rejects_internally_valid_guard_from_different_nominal_recovery_authority():
    budget = build_authority_waste_fluid_budget()
    alternate = replace(budget, recovery_ratio_min=0.95)
    guard = _guard(alternate)
    with pytest.raises(WasteFluidAccountingError, match="service routing|cycle routing|nominal recovery"):
        validate_overflow_guard_authority(budget, guard)


def test_rejects_authority_collision_that_preserves_nominal_recovery_and_maximum_inflow():
    budget = build_authority_waste_fluid_budget()
    alternate_nominal = budget.nominal_introduced_mL_per_cycle + 0.1
    alternate_prime = budget.maximum_initial_prime_mL_per_cycle - 0.1
    alternate = replace(
        budget,
        nominal_introduced_mL_per_cycle=alternate_nominal,
        maximum_initial_prime_mL_per_cycle=alternate_prime,
        recovery_ratio_min=budget.minimum_recovered_mL_per_cycle / alternate_nominal,
    )
    guard = _guard(alternate)

    assert guard.routing.cycles[0].minimum_nominal_routed_to_cartridge_mL == pytest.approx(
        budget.minimum_recovered_mL_per_cycle
    )
    assert guard.routing.cycles[-1].cumulative_maximum_cartridge_inflow_mL == pytest.approx(
        budget.conservative_service_screen.maximum_cartridge_inflow_mL
    )
    with pytest.raises(WasteFluidAccountingError, match="service routing|cycle routing"):
        validate_overflow_guard_authority(budget, guard)


def test_rejects_equal_and_opposite_cycle_prime_recovery_corruption():
    budget = build_authority_waste_fluid_budget()
    guard = _guard(budget)
    first, second, *rest = guard.routing.cycles
    delta = 0.01

    forged_first = replace(
        first,
        minimum_prime_routed_to_cartridge_mL=first.minimum_prime_routed_to_cartridge_mL + delta,
        minimum_total_routed_to_cartridge_mL=first.minimum_total_routed_to_cartridge_mL + delta,
        cumulative_minimum_cartridge_routing_mL=first.cumulative_minimum_cartridge_routing_mL + delta,
        cartridge_occupancy_uncertainty_mL=first.cartridge_occupancy_uncertainty_mL - delta,
        minimum_routing_capacity_margin_mL=first.minimum_routing_capacity_margin_mL - delta,
    )
    forged_second = replace(
        second,
        minimum_prime_routed_to_cartridge_mL=second.minimum_prime_routed_to_cartridge_mL - delta,
        minimum_total_routed_to_cartridge_mL=second.minimum_total_routed_to_cartridge_mL - delta,
    )
    forged_routing = replace(
        guard.routing,
        cycles=(forged_first, forged_second, *rest),
    )
    forged_guard = replace(guard, routing=forged_routing)

    # The forged profile remains internally self-consistent and preserves aggregate
    # service totals, but it no longer represents the authority's per-cycle routing.
    forged_guard.__post_init__()
    with pytest.raises(WasteFluidAccountingError, match="cycle routing"):
        validate_overflow_guard_authority(budget, forged_guard)


def test_rejects_wrong_evidence_types():
    budget = build_authority_waste_fluid_budget()
    guard = _guard(budget)
    with pytest.raises(WasteFluidAccountingError):
        validate_overflow_guard_authority(object(), guard)
    with pytest.raises(WasteFluidAccountingError):
        validate_overflow_guard_authority(budget, object())
