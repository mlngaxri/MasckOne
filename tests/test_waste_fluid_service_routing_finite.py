from dataclasses import replace

import pytest

from masck_one.waste_fluid_accounting import WasteFluidAccountingError, build_authority_waste_fluid_budget
from masck_one.waste_fluid_closure import screen_service_routing_closure


def test_service_routing_rejects_prime_volume_overflow_without_contracts():
    budget = build_authority_waste_fluid_budget()
    with pytest.raises(WasteFluidAccountingError, match="service routing arithmetic produced nonfinite"):
        screen_service_routing_closure(
            budget,
            cycles=1,
            prime_events=10**400,
        )


def test_service_routing_rejects_prime_volume_overflow_with_recovery_contract():
    budget = build_authority_waste_fluid_budget()
    with pytest.raises(WasteFluidAccountingError, match="service routing arithmetic produced nonfinite"):
        screen_service_routing_closure(
            budget,
            cycles=1,
            prime_events=10**400,
            prime_recovery_ratio_contract=1.0,
        )


def test_service_routing_rejects_finite_operands_whose_prime_product_overflows():
    budget = replace(
        build_authority_waste_fluid_budget(),
        service_cycles=1,
        maximum_initial_prime_mL_per_cycle=1e308,
        cartridge_retained_capacity_requirement_mL=1e308,
    )
    # The replacement is intentionally synthetic. Its one-cycle authority screen
    # remains finite, while two routing prime events overflow the derived volume.
    budget.validate()
    with pytest.raises(WasteFluidAccountingError, match="service routing arithmetic produced nonfinite"):
        screen_service_routing_closure(budget, cycles=1, prime_events=2)
