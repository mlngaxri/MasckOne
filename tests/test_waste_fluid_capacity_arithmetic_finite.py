from dataclasses import replace

import pytest

from masck_one.waste_fluid_accounting import WasteFluidAccountingError, build_authority_waste_fluid_budget


def test_service_capacity_screen_rejects_nonfinite_derived_prime_volume():
    budget = replace(build_authority_waste_fluid_budget(), maximum_initial_prime_mL_per_cycle=1e308)
    with pytest.raises(WasteFluidAccountingError, match="nonfinite"):
        budget.service_capacity_screen(cycles=1, prime_events=2)


def test_maximum_service_cycles_rejects_nonfinite_derived_prime_volume():
    budget = replace(build_authority_waste_fluid_budget(), maximum_initial_prime_mL_per_cycle=1e308)
    with pytest.raises(WasteFluidAccountingError, match="nonfinite"):
        budget.maximum_service_cycles_that_fit(prime_events=2)


def test_maximum_prime_events_rejects_nonfinite_capacity_quotient():
    budget = replace(
        build_authority_waste_fluid_budget(),
        maximum_initial_prime_mL_per_cycle=5e-324,
    )
    with pytest.raises(WasteFluidAccountingError, match="maximum_prime_events_quotient"):
        budget.maximum_prime_events_that_fit(cycles=1)


def test_maximum_service_cycles_rejects_nonfinite_capacity_quotient():
    budget = replace(
        build_authority_waste_fluid_budget(),
        nominal_introduced_mL_per_cycle=5e-324,
        recovery_ratio_min=0.0,
    )
    with pytest.raises(WasteFluidAccountingError, match="maximum_service_cycles_quotient"):
        budget.maximum_service_cycles_that_fit(prime_events=0)
