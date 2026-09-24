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
