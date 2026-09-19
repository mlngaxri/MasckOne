import pytest

from masck_one.waste_fluid_accounting import WasteFluidAccountingError, build_authority_waste_fluid_budget
from masck_one.waste_fluid_cycle_routing import screen_cycle_resolved_routing_closure


def test_authority_one_prime_per_cycle_preserves_local_sink_margins():
    closure = screen_cycle_resolved_routing_closure(
        build_authority_waste_fluid_budget(),
        prime_events_by_cycle=[1, 1, 1, 1, 1, 1],
        prime_recovery_ratio_contract=0.90,
        prime_residual_ratio_contract=0.08,
        prime_external_leakage_ratio_contract=0.02,
    )
    assert len(closure.cycles) == 6
    assert closure.service.total_prime_liquid_mL == pytest.approx(2.4)
    assert all(c.prime_residual_mL == pytest.approx(0.032) for c in closure.cycles)
    assert all(c.prime_external_leakage_mL == pytest.approx(0.008) for c in closure.cycles)
    assert all(c.residual_ceiling_margin_mL == pytest.approx(0.368) for c in closure.cycles)
    assert all(c.external_leakage_ceiling_margin_mL == pytest.approx(0.042) for c in closure.cycles)


def test_cycle_screen_exposes_shared_sink_shortfall_after_prime_allocation():
    closure = screen_cycle_resolved_routing_closure(
        build_authority_waste_fluid_budget(),
        prime_events_by_cycle=[1],
        prime_recovery_ratio_contract=0.90,
        prime_residual_ratio_contract=0.08,
        prime_external_leakage_ratio_contract=0.02,
    )
    cycle = closure.cycles[0]
    assert cycle.classified_sink_capacity_after_prime_mL == pytest.approx(0.410)
    assert cycle.nominal_unclassified_nonrecovery_after_prime_mL == pytest.approx(0.050)
    assert cycle.classified_sink_headroom_after_nominal_mL == pytest.approx(0.0)
    assert not cycle.local_routing_contract_complete


def test_cycle_screen_reports_true_shared_sink_headroom_when_recovery_is_tighter():
    budget = build_authority_waste_fluid_budget()
    tighter = type(budget)(
        service_cycles=budget.service_cycles,
        nominal_introduced_mL_per_cycle=budget.nominal_introduced_mL_per_cycle,
        maximum_initial_prime_mL_per_cycle=budget.maximum_initial_prime_mL_per_cycle,
        recovery_ratio_min=0.95,
        residual_free_liquid_max_mL=budget.residual_free_liquid_max_mL,
        external_leakage_max_mL_per_cycle=budget.external_leakage_max_mL_per_cycle,
        cartridge_retained_capacity_requirement_mL=budget.cartridge_retained_capacity_requirement_mL,
    )
    closure = screen_cycle_resolved_routing_closure(
        tighter,
        prime_events_by_cycle=[1],
        prime_recovery_ratio_contract=1.0,
    )
    cycle = closure.cycles[0]
    assert cycle.classified_sink_capacity_after_prime_mL == pytest.approx(0.450)
    assert cycle.nominal_unclassified_nonrecovery_after_prime_mL == pytest.approx(0.0)
    assert cycle.classified_sink_headroom_after_nominal_mL == pytest.approx(0.220)
    assert cycle.local_routing_contract_complete


def test_clustered_reprimes_cannot_average_external_leakage_across_cycles():
    with pytest.raises(WasteFluidAccountingError, match="leakage contract exceeds"):
        screen_cycle_resolved_routing_closure(
            build_authority_waste_fluid_budget(),
            prime_events_by_cycle=[6, 0, 0, 0, 0, 0],
            prime_recovery_ratio_contract=0.90,
            prime_external_leakage_ratio_contract=0.10,
        )


def test_clustered_reprimes_cannot_average_residual_allocation_across_cycles():
    with pytest.raises(WasteFluidAccountingError, match="residual contract exceeds"):
        screen_cycle_resolved_routing_closure(
            build_authority_waste_fluid_budget(),
            prime_events_by_cycle=[6, 0, 0, 0, 0, 0],
            prime_recovery_ratio_contract=0.50,
            prime_residual_ratio_contract=0.50,
        )


def test_zero_prime_cycle_keeps_full_local_sink_headroom():
    closure = screen_cycle_resolved_routing_closure(
        build_authority_waste_fluid_budget(),
        prime_events_by_cycle=[0],
        prime_recovery_ratio_contract=1.0,
    )
    cycle = closure.cycles[0]
    assert cycle.prime_residual_mL == pytest.approx(0.0)
    assert cycle.prime_external_leakage_mL == pytest.approx(0.0)
    assert cycle.residual_ceiling_margin_mL == pytest.approx(0.4)
    assert cycle.external_leakage_ceiling_margin_mL == pytest.approx(0.05)


def test_cycle_routing_profile_cannot_extend_past_configured_service_life():
    budget = build_authority_waste_fluid_budget()
    assert budget.service_cycles == 6
    with pytest.raises(WasteFluidAccountingError, match="exceeds configured service life"):
        screen_cycle_resolved_routing_closure(
            budget,
            prime_events_by_cycle=[0, 0, 0, 0, 0, 0, 0],
            prime_recovery_ratio_contract=1.0,
        )


def test_cycle_routing_profile_may_screen_a_service_life_prefix():
    closure = screen_cycle_resolved_routing_closure(
        build_authority_waste_fluid_budget(),
        prime_events_by_cycle=[1, 0, 2],
        prime_recovery_ratio_contract=1.0,
    )
    assert len(closure.cycles) == 3
    assert closure.service.cycles == 3
    assert closure.service.prime_events == 3


def test_cycle_resolved_routing_rejects_invalid_schedules():
    budget = build_authority_waste_fluid_budget()
    for schedule in ([], (), [1, -1], [True], [1.5]):
        with pytest.raises(WasteFluidAccountingError):
            screen_cycle_resolved_routing_closure(budget, prime_events_by_cycle=schedule)
