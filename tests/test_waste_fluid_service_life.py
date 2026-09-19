from dataclasses import replace

import pytest

from masck_one.waste_fluid_accounting import (
    WasteFluidAccountingError,
    build_authority_waste_fluid_budget,
)


def test_service_life_boundary_accounts_for_reprime_loading():
    budget = build_authority_waste_fluid_budget()
    assert budget.maximum_service_cycles_that_fit(prime_events=1) == 7
    assert budget.maximum_service_cycles_that_fit(prime_events=6) == 7
    assert budget.maximum_service_cycles_that_fit(prime_events=18) == 6

    six_cycles = budget.service_capacity_screen(cycles=6, prime_events=18)
    seven_cycles = budget.service_capacity_screen(cycles=7, prime_events=18)
    assert six_cycles.maximum_cartridge_inflow_mL == pytest.approx(34.8)
    assert six_cycles.capacity_satisfied is True
    assert seven_cycles.maximum_cartridge_inflow_mL == pytest.approx(39.4)
    assert seven_cycles.capacity_satisfied is False


def test_prime_only_overflow_fails_closed():
    budget = build_authority_waste_fluid_budget()
    with pytest.raises(WasteFluidAccountingError, match="prime liquid alone"):
        budget.maximum_service_cycles_that_fit(prime_events=88)


def test_zero_nominal_volume_reports_unbounded_service_cycles():
    budget = replace(build_authority_waste_fluid_budget(), nominal_introduced_mL_per_cycle=0.0)
    assert budget.maximum_service_cycles_that_fit(prime_events=1) is None


def test_service_life_query_rejects_boolean_and_negative_prime_counts():
    budget = build_authority_waste_fluid_budget()
    for invalid in (True, -1):
        with pytest.raises(WasteFluidAccountingError, match="nonnegative integer"):
            budget.maximum_service_cycles_that_fit(prime_events=invalid)


def test_manifest_exposes_cycle_capacity_for_reprime_profiles():
    manifest = build_authority_waste_fluid_budget().manifest()
    assert manifest["maximum_service_cycles_with_single_initial_prime"] == 7
    assert manifest["maximum_service_cycles_with_baseline_reprimes"] == 7
