from dataclasses import replace

import pytest

from masck_one.waste_fluid_accounting import (
    WasteFluidAccountingError,
    build_authority_waste_fluid_budget,
)
from masck_one.waste_fluid_closure import screen_service_routing_closure
from masck_one.waste_fluid_profile import screen_service_profile
from masck_one.waste_fluid_routing_capacity import derive_routing_qualified_capacity_floor


def _completed_profile():
    budget = build_authority_waste_fluid_budget()
    profile = screen_service_profile(
        budget,
        prime_events_by_cycle=[1] * budget.service_cycles,
        target_cycles=budget.service_cycles,
    )
    return budget, profile


def test_prime_recovery_contract_is_charged_to_capacity_floor():
    budget, profile = _completed_profile()
    routing = screen_service_routing_closure(
        budget,
        cycles=budget.service_cycles,
        prime_events=budget.service_cycles,
        prime_recovery_ratio_contract=0.5,
    )

    floor = derive_routing_qualified_capacity_floor(profile, routing)

    expected_prime = (
        budget.service_cycles
        * budget.maximum_initial_prime_mL_per_cycle
        * 0.5
    )
    assert floor.nominal_recovery_floor_mL == pytest.approx(
        budget.service_cycles * budget.minimum_recovered_mL_per_cycle
    )
    assert floor.prime_recovery_floor_mL == pytest.approx(expected_prime)
    assert floor.combined_recovery_floor_mL == pytest.approx(
        floor.nominal_recovery_floor_mL + expected_prime
    )
    assert floor.headroom_mL == pytest.approx(
        profile.usable_capacity_mL - floor.combined_recovery_floor_mL
    )
    assert floor.fit
    assert not floor.routing_contract_complete
    assert not floor.integration_ready


def test_complete_routing_contract_and_capacity_fit_are_integration_ready():
    budget, profile = _completed_profile()
    routing = screen_service_routing_closure(
        budget,
        cycles=budget.service_cycles,
        prime_events=budget.service_cycles,
        prime_recovery_ratio_contract=1.0,
    )
    floor = derive_routing_qualified_capacity_floor(profile, routing)
    assert floor.fit
    assert floor.routing_contract_complete
    assert floor.integration_ready


def test_zero_prime_recovery_contract_preserves_nominal_floor():
    budget, profile = _completed_profile()
    routing = screen_service_routing_closure(
        budget,
        cycles=budget.service_cycles,
        prime_events=budget.service_cycles,
        prime_recovery_ratio_contract=0.0,
    )
    floor = derive_routing_qualified_capacity_floor(profile, routing)
    assert floor.prime_recovery_floor_mL == 0.0
    assert floor.combined_recovery_floor_mL == pytest.approx(
        profile.final.minimum_recovered_nominal_mL
    )
    assert not floor.integration_ready


def test_incomplete_profile_is_rejected_to_prevent_partial_service_floor():
    budget = build_authority_waste_fluid_budget()
    profile = screen_service_profile(
        budget,
        prime_events_by_cycle=[1, 1],
        target_cycles=budget.service_cycles,
    )
    routing = screen_service_routing_closure(
        budget,
        cycles=2,
        prime_events=2,
        prime_recovery_ratio_contract=0.5,
    )
    with pytest.raises(WasteFluidAccountingError, match="completed service profile"):
        derive_routing_qualified_capacity_floor(profile, routing)


def test_cycle_and_prime_count_mismatches_fail_closed():
    budget, profile = _completed_profile()
    routing = screen_service_routing_closure(
        budget,
        cycles=budget.service_cycles,
        prime_events=budget.service_cycles,
        prime_recovery_ratio_contract=0.5,
    )
    with pytest.raises(WasteFluidAccountingError, match="cycle count"):
        derive_routing_qualified_capacity_floor(
            profile,
            replace(routing, cycles=budget.service_cycles - 1),
        )
    with pytest.raises(WasteFluidAccountingError, match="prime count"):
        derive_routing_qualified_capacity_floor(
            profile,
            replace(routing, prime_events=budget.service_cycles - 1),
        )


def test_nominal_floor_mismatch_fails_closed():
    budget, profile = _completed_profile()
    routing = screen_service_routing_closure(
        budget,
        cycles=budget.service_cycles,
        prime_events=budget.service_cycles,
        prime_recovery_ratio_contract=0.5,
    )
    with pytest.raises(WasteFluidAccountingError, match="do not reconcile"):
        derive_routing_qualified_capacity_floor(
            profile,
            replace(
                routing,
                minimum_nominal_liquid_routed_to_cartridge_mL=(
                    routing.minimum_nominal_liquid_routed_to_cartridge_mL + 0.001
                ),
            ),
        )
