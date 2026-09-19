from dataclasses import replace

import pytest

from masck_one.waste_fluid_accounting import WasteFluidAccountingError, build_authority_waste_fluid_budget
from masck_one.waste_fluid_closure import screen_nonrecovery_closure, screen_service_routing_closure


def test_authority_profile_exposes_unclassified_nonrecovery_allowance():
    closure = screen_nonrecovery_closure(build_authority_waste_fluid_budget())
    assert closure.maximum_unrecovered_nominal_mL == pytest.approx(0.460)
    assert closure.residual_ceiling_mL == pytest.approx(0.400)
    assert closure.external_leakage_ceiling_mL == pytest.approx(0.050)
    assert closure.classified_nonrecovery_ceiling_mL == pytest.approx(0.450)
    assert closure.unclassified_nonrecovery_allowance_mL == pytest.approx(0.010)
    assert closure.classified_sink_headroom_mL == pytest.approx(0.0)
    assert closure.closes_using_only_classified_sinks is False


def test_closure_at_exact_cross_requirement_threshold_has_no_gap():
    budget = build_authority_waste_fluid_budget()
    threshold = budget.recovery_ratio_for_residual_leakage_closure
    closure = screen_nonrecovery_closure(replace(budget, recovery_ratio_min=threshold))
    assert closure.unclassified_nonrecovery_allowance_mL == pytest.approx(0.0, abs=1e-12)
    assert closure.classified_sink_headroom_mL == pytest.approx(0.0, abs=1e-12)
    assert closure.closes_using_only_classified_sinks is True


def test_higher_recovery_floor_reports_classified_sink_headroom_not_negative_gap():
    budget = replace(build_authority_waste_fluid_budget(), recovery_ratio_min=0.95)
    closure = screen_nonrecovery_closure(budget)
    assert closure.maximum_unrecovered_nominal_mL == pytest.approx(0.230)
    assert closure.unclassified_nonrecovery_allowance_mL == pytest.approx(0.0)
    assert closure.classified_sink_headroom_mL == pytest.approx(0.220)
    assert closure.closes_using_only_classified_sinks is True


def test_closure_screen_does_not_credit_sinks_to_cartridge_capacity():
    budget = build_authority_waste_fluid_budget()
    baseline = budget.maximum_cartridge_inflow_screen_mL
    screen_nonrecovery_closure(budget)
    assert budget.maximum_cartridge_inflow_screen_mL == pytest.approx(baseline)


def test_service_routing_closure_exposes_prime_liquid_without_destination_contract():
    budget = build_authority_waste_fluid_budget()
    closure = screen_service_routing_closure(budget, cycles=6, prime_events=6)
    assert closure.nominal_unclassified_nonrecovery_mL == pytest.approx(0.060)
    assert closure.total_prime_liquid_mL == pytest.approx(2.400)
    assert closure.minimum_prime_liquid_routed_to_cartridge_mL == pytest.approx(0.0)
    assert closure.maximum_prime_residual_mL == pytest.approx(0.0)
    assert closure.maximum_prime_external_leakage_mL == pytest.approx(0.0)
    assert closure.prime_liquid_without_routing_contract_mL == pytest.approx(2.400)
    assert closure.total_liquid_without_routing_contract_mL == pytest.approx(2.460)
    assert closure.routing_contract_complete is False


def test_prime_recovery_contract_routes_only_its_explicit_fraction():
    closure = screen_service_routing_closure(
        build_authority_waste_fluid_budget(), cycles=6, prime_events=6, prime_recovery_ratio_contract=0.90
    )
    assert closure.minimum_prime_liquid_routed_to_cartridge_mL == pytest.approx(2.160)
    assert closure.prime_liquid_without_routing_contract_mL == pytest.approx(0.240)
    assert closure.total_liquid_without_routing_contract_mL == pytest.approx(0.300)


def test_prime_nonrecovery_can_be_classified_without_double_counting():
    closure = screen_service_routing_closure(
        build_authority_waste_fluid_budget(),
        cycles=6,
        prime_events=6,
        prime_recovery_ratio_contract=0.90,
        prime_residual_ratio_contract=0.08,
        prime_external_leakage_ratio_contract=0.02,
    )
    assert closure.minimum_prime_liquid_routed_to_cartridge_mL == pytest.approx(2.160)
    assert closure.maximum_prime_residual_mL == pytest.approx(0.192)
    assert closure.maximum_prime_external_leakage_mL == pytest.approx(0.048)
    assert closure.prime_liquid_without_routing_contract_mL == pytest.approx(0.0, abs=1e-12)
    assert closure.total_liquid_without_routing_contract_mL == pytest.approx(0.060)
    assert closure.routing_contract_complete is False


def test_complete_prime_and_nominal_sink_contract_closes_service_routing():
    base = build_authority_waste_fluid_budget()
    budget = replace(base, recovery_ratio_min=base.recovery_ratio_for_residual_leakage_closure)
    closure = screen_service_routing_closure(
        budget,
        cycles=6,
        prime_events=6,
        prime_recovery_ratio_contract=0.90,
        prime_residual_ratio_contract=0.08,
        prime_external_leakage_ratio_contract=0.02,
    )
    assert closure.total_liquid_without_routing_contract_mL == pytest.approx(0.0, abs=1e-12)
    assert closure.routing_contract_complete is True


def test_prime_sink_contract_rejects_overallocated_mass_balance():
    with pytest.raises(WasteFluidAccountingError, match="must not sum above one"):
        screen_service_routing_closure(
            build_authority_waste_fluid_budget(),
            cycles=1,
            prime_events=1,
            prime_recovery_ratio_contract=0.90,
            prime_residual_ratio_contract=0.08,
            prime_external_leakage_ratio_contract=0.03,
        )


def test_service_routing_closure_rejects_invalid_counts_and_prime_contracts():
    budget = build_authority_waste_fluid_budget()
    with pytest.raises(WasteFluidAccountingError, match="positive integer"):
        screen_service_routing_closure(budget, cycles=True, prime_events=0)
    with pytest.raises(WasteFluidAccountingError, match="nonnegative integer"):
        screen_service_routing_closure(budget, cycles=1, prime_events=-1)
    for field in (
        "prime_recovery_ratio_contract",
        "prime_residual_ratio_contract",
        "prime_external_leakage_ratio_contract",
    ):
        for invalid in (-0.01, 1.01, float("nan"), True):
            with pytest.raises(WasteFluidAccountingError, match="finite and between zero and one"):
                screen_service_routing_closure(
                    budget, cycles=1, prime_events=1, **{field: invalid}
                )
