from dataclasses import replace

import pytest

from masck_one.waste_fluid_accounting import WasteFluidAccountingError, build_authority_waste_fluid_budget
from masck_one.waste_fluid_closure import screen_service_routing_closure


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


def test_service_routing_rejects_even_sub_tolerance_prime_sink_overallocation():
    budget = build_authority_waste_fluid_budget()
    # Digital destination fractions partition one physical prime volume. A prior
    # numerical tolerance allowed a tiny sum above unity, which could allocate
    # more liquid to named sinks than the prime event actually contains.
    with pytest.raises(WasteFluidAccountingError, match="must not sum above one"):
        screen_service_routing_closure(
            budget,
            cycles=budget.service_cycles,
            prime_events=1,
            prime_recovery_ratio_contract=0.90,
            prime_residual_ratio_contract=0.08,
            prime_external_leakage_ratio_contract=0.0200000000005,
        )


def test_service_routing_accepts_exact_full_prime_sink_partition():
    budget = build_authority_waste_fluid_budget()
    closure = screen_service_routing_closure(
        budget,
        cycles=budget.service_cycles,
        prime_events=1,
        prime_recovery_ratio_contract=0.90,
        prime_residual_ratio_contract=0.08,
        prime_external_leakage_ratio_contract=0.02,
    )
    assert closure.prime_liquid_without_routing_contract_mL == pytest.approx(0.0)
    assert (
        closure.minimum_prime_liquid_routed_to_cartridge_mL
        + closure.maximum_prime_residual_mL
        + closure.maximum_prime_external_leakage_mL
    ) == pytest.approx(closure.total_prime_liquid_mL)


def test_service_routing_finite_guard_does_not_change_authority_result():
    closure = screen_service_routing_closure(
        build_authority_waste_fluid_budget(),
        cycles=6,
        prime_events=6,
        prime_recovery_ratio_contract=0.90,
    )
    assert closure.total_prime_liquid_mL == pytest.approx(2.4)
    assert closure.minimum_prime_liquid_routed_to_cartridge_mL == pytest.approx(2.16)
    assert closure.total_liquid_without_routing_contract_mL == pytest.approx(0.30)
