from copy import deepcopy
from dataclasses import replace

import pytest

from masck_one.authority import Authority, load_authority
from masck_one.waste_fluid_accounting import (
    WasteFluidAccountingError,
    build_authority_waste_fluid_budget,
)


def test_authority_budget_reconciles_cycle_and_capacity_screen():
    budget = build_authority_waste_fluid_budget()
    assert budget.nominal_introduced_mL_per_cycle == pytest.approx(4.60)
    assert budget.maximum_liquid_presented_to_recovery_mL_per_cycle == pytest.approx(5.00)
    assert budget.minimum_recovered_mL_per_cycle == pytest.approx(4.14)
    assert budget.residual_free_liquid_max_mL == pytest.approx(0.400)
    assert budget.external_leakage_max_mL_per_cycle == pytest.approx(0.050)
    assert budget.maximum_cartridge_inflow_screen_mL == pytest.approx(30.0)
    assert budget.cartridge_requirement_margin_mL == pytest.approx(5.0)
    assert budget.manifest()["physical_validation_eligible"] is False


def test_service_profile_tracks_prime_events_separately_from_cycles():
    budget = build_authority_waste_fluid_budget()
    single_prime = budget.service_capacity_screen(cycles=6, prime_events=1)
    assert single_prime.nominal_liquid_mL == pytest.approx(27.6)
    assert single_prime.prime_liquid_mL == pytest.approx(0.4)
    assert single_prime.minimum_recovered_nominal_mL == pytest.approx(24.84)
    assert single_prime.maximum_cartridge_inflow_mL == pytest.approx(28.0)
    assert single_prime.requirement_margin_mL == pytest.approx(7.0)
    assert single_prime.occupancy_uncertainty_mL == pytest.approx(3.16)
    assert single_prime.capacity_satisfied is True

    every_cycle_reprime = budget.service_capacity_screen(cycles=6, prime_events=6)
    assert every_cycle_reprime.minimum_recovered_nominal_mL == pytest.approx(24.84)
    assert every_cycle_reprime.maximum_cartridge_inflow_mL == pytest.approx(30.0)
    assert every_cycle_reprime.occupancy_uncertainty_mL == pytest.approx(5.16)
    assert every_cycle_reprime.requirement_margin_mL == pytest.approx(5.0)
    assert budget.maximum_cartridge_inflow_screen_mL == every_cycle_reprime.maximum_cartridge_inflow_mL


def test_retained_occupancy_interval_does_not_assume_prime_recovery():
    budget = build_authority_waste_fluid_budget()
    no_prime = budget.service_capacity_screen(cycles=6, prime_events=0)
    many_primes = budget.service_capacity_screen(cycles=6, prime_events=10)
    assert no_prime.minimum_recovered_nominal_mL == pytest.approx(24.84)
    assert many_primes.minimum_recovered_nominal_mL == pytest.approx(24.84)
    assert many_primes.maximum_cartridge_inflow_mL - no_prime.maximum_cartridge_inflow_mL == pytest.approx(4.0)
    manifest = budget.manifest()
    assert manifest["minimum_retained_waste_screen_mL"] == pytest.approx(24.84)
    assert manifest["conservative_occupancy_uncertainty_mL"] == pytest.approx(5.16)
    assert manifest["prime_recovery_assumption"] == "UNSPECIFIED_NO_CREDIT_IN_LOWER_BOUND"


def test_minimum_required_recovery_cannot_exceed_cartridge_requirement():
    budget = replace(build_authority_waste_fluid_budget(), recovery_ratio_min=1.0, service_cycles=8)
    with pytest.raises(WasteFluidAccountingError, match="minimum required recovered waste"):
        budget.validate()


def test_each_additional_prime_consumes_exact_prime_allowance():
    budget = build_authority_waste_fluid_budget()
    one = budget.service_capacity_screen(cycles=6, prime_events=1)
    three = budget.service_capacity_screen(cycles=6, prime_events=3)
    assert three.maximum_cartridge_inflow_mL - one.maximum_cartridge_inflow_mL == pytest.approx(0.8)
    assert one.requirement_margin_mL - three.requirement_margin_mL == pytest.approx(0.8)


def test_reprime_events_can_exceed_cycle_count_and_fail_at_capacity_boundary():
    budget = build_authority_waste_fluid_budget()
    assert budget.maximum_prime_events_that_fit(cycles=6) == 18
    eighteen = budget.service_capacity_screen(cycles=6, prime_events=18)
    nineteen = budget.service_capacity_screen(cycles=6, prime_events=19)
    assert eighteen.maximum_cartridge_inflow_mL == pytest.approx(34.8)
    assert eighteen.requirement_margin_mL == pytest.approx(0.2)
    assert eighteen.capacity_satisfied is True
    assert nineteen.maximum_cartridge_inflow_mL == pytest.approx(35.2)
    assert nineteen.requirement_margin_mL == pytest.approx(-0.2)
    assert nineteen.capacity_satisfied is False


def test_service_profile_rejects_invalid_prime_count_but_not_multiple_reprimes():
    budget = build_authority_waste_fluid_budget()
    assert budget.service_capacity_screen(cycles=2, prime_events=3).prime_events == 3
    with pytest.raises(WasteFluidAccountingError, match="nonnegative integer"):
        budget.service_capacity_screen(cycles=2, prime_events=True)


def test_zero_prime_allowance_reports_unbounded_prime_count_in_capacity_model():
    budget = replace(build_authority_waste_fluid_budget(), maximum_initial_prime_mL_per_cycle=0.0)
    assert budget.maximum_prime_events_that_fit(cycles=6) is None


def test_nominal_service_alone_can_fail_prime_capacity_query():
    budget = build_authority_waste_fluid_budget()
    with pytest.raises(WasteFluidAccountingError, match="nominal service liquid alone"):
        budget.maximum_prime_events_that_fit(cycles=8)


def test_manifest_exposes_prime_capacity_boundary_without_weakening_gate():
    budget = build_authority_waste_fluid_budget()
    manifest = budget.manifest()
    assert manifest["single_initial_prime_service_inflow_mL"] == pytest.approx(28.0)
    assert manifest["single_initial_prime_service_margin_mL"] == pytest.approx(7.0)
    assert manifest["maximum_cartridge_inflow_screen_mL"] == pytest.approx(30.0)
    assert manifest["cartridge_requirement_margin_mL"] == pytest.approx(5.0)
    assert manifest["maximum_prime_events_that_fit_baseline_service"] == 18


def test_unrecovered_fluid_closure_exposes_cross_requirement_threshold():
    budget = build_authority_waste_fluid_budget()
    assert budget.maximum_unrecovered_nominal_mL_per_cycle == pytest.approx(0.460)
    assert budget.maximum_classified_nonrecovery_mL_per_cycle == pytest.approx(0.450)
    assert budget.recovery_ratio_for_residual_leakage_closure == pytest.approx(0.9021739130434783)
    assert budget.recovery_ratio_closure_delta == pytest.approx(0.0021739130434783)
    manifest = budget.manifest()
    assert manifest["maximum_unrecovered_nominal_mL_per_cycle"] == pytest.approx(0.460)
    assert manifest["maximum_classified_nonrecovery_mL_per_cycle"] == pytest.approx(0.450)
    assert manifest["recovery_ratio_for_residual_leakage_closure"] == pytest.approx(0.9021739130434783)


def test_closure_threshold_does_not_promote_recovery_floor():
    budget = build_authority_waste_fluid_budget()
    assert budget.recovery_ratio_min == pytest.approx(0.90)
    assert budget.recovery_ratio_for_residual_leakage_closure > budget.recovery_ratio_min
    assert budget.manifest()["recovery_ratio_min"] == pytest.approx(0.90)


def test_capacity_screen_credits_neither_residual_nor_leakage():
    budget = build_authority_waste_fluid_budget()
    changed = replace(budget, residual_free_liquid_max_mL=0.0, external_leakage_max_mL_per_cycle=0.0)
    assert changed.maximum_cartridge_inflow_screen_mL == budget.maximum_cartridge_inflow_screen_mL


def test_zero_nominal_volume_has_defined_closure_threshold():
    budget = replace(build_authority_waste_fluid_budget(), nominal_introduced_mL_per_cycle=0.0, recovery_ratio_min=0.0)
    assert budget.recovery_ratio_for_residual_leakage_closure == pytest.approx(1.0)


def test_seventh_cycle_exhausts_digital_requirement_margin():
    budget = replace(build_authority_waste_fluid_budget(), service_cycles=7)
    budget.validate()
    assert budget.maximum_cartridge_inflow_screen_mL == pytest.approx(35.0)
    assert budget.cartridge_requirement_margin_mL == pytest.approx(0.0)


def test_eighth_cycle_fails_closed_against_capacity_requirement():
    budget = replace(build_authority_waste_fluid_budget(), service_cycles=8)
    with pytest.raises(WasteFluidAccountingError, match="below conservative cycle inflow screen"):
        budget.validate()


def test_invalid_recovery_ratio_fails_closed():
    budget = replace(build_authority_waste_fluid_budget(), recovery_ratio_min=1.01)
    with pytest.raises(WasteFluidAccountingError, match="recovery ratio"):
        budget.validate()


def test_boolean_cycle_count_is_rejected():
    budget = replace(build_authority_waste_fluid_budget(), service_cycles=True)
    with pytest.raises(WasteFluidAccountingError, match="positive integer"):
        budget.validate()


def test_fractional_authority_cycle_count_is_not_silently_truncated():
    base = load_authority()
    data = deepcopy(base.data)
    data["fluid"]["cartridge"]["service_cycles_baseline"] = 6.5
    mutated = Authority(data=data, source=base.source, validation_report=base.validation_report)
    with pytest.raises(WasteFluidAccountingError, match="service_cycles_baseline"):
        build_authority_waste_fluid_budget(mutated)
