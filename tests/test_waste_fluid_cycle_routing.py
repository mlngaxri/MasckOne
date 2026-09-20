import pytest
from masck_one.waste_fluid_accounting import WasteFluidAccountingError, build_authority_waste_fluid_budget
from masck_one.waste_fluid_cycle_routing import screen_cycle_resolved_routing_closure

def test_authority_one_prime_per_cycle_preserves_local_sink_margins():
    closure = screen_cycle_resolved_routing_closure(build_authority_waste_fluid_budget(), prime_events_by_cycle=[1]*6, prime_recovery_ratio_contract=.90, prime_residual_ratio_contract=.08, prime_external_leakage_ratio_contract=.02)
    assert len(closure.cycles) == 6
    assert closure.service.total_prime_liquid_mL == pytest.approx(2.4)
    assert all(c.prime_residual_mL == pytest.approx(.032) for c in closure.cycles)
    assert all(c.prime_external_leakage_mL == pytest.approx(.008) for c in closure.cycles)
    assert all(c.residual_ceiling_margin_mL == pytest.approx(.368) for c in closure.cycles)
    assert all(c.external_leakage_ceiling_margin_mL == pytest.approx(.042) for c in closure.cycles)
    assert closure.total_prime_residual_mL == pytest.approx(.192)
    assert closure.total_prime_residual_mL == pytest.approx(closure.service.maximum_prime_residual_mL)
    assert closure.total_prime_external_leakage_mL == pytest.approx(.048)
    assert closure.total_prime_external_leakage_mL == pytest.approx(closure.service.maximum_prime_external_leakage_mL)
    assert closure.first_incomplete_cycle == 1
    assert not closure.all_cycles_routing_complete

def test_cycle_screen_exposes_minimum_cartridge_routing_load():
    closure = screen_cycle_resolved_routing_closure(build_authority_waste_fluid_budget(), prime_events_by_cycle=[1]*6, prime_recovery_ratio_contract=.90, prime_residual_ratio_contract=.08, prime_external_leakage_ratio_contract=.02)
    assert all(c.minimum_nominal_routed_to_cartridge_mL == pytest.approx(4.14) for c in closure.cycles)
    assert all(c.minimum_prime_routed_to_cartridge_mL == pytest.approx(.36) for c in closure.cycles)
    assert all(c.minimum_total_routed_to_cartridge_mL == pytest.approx(4.50) for c in closure.cycles)
    assert closure.service.minimum_nominal_liquid_routed_to_cartridge_mL == pytest.approx(24.84)
    assert closure.minimum_total_routed_to_cartridge_mL == pytest.approx(27.0)
    assert closure.minimum_total_routed_to_cartridge_mL == pytest.approx(closure.service.minimum_nominal_liquid_routed_to_cartridge_mL + closure.service.minimum_prime_liquid_routed_to_cartridge_mL)

def test_cycle_screen_tracks_fail_conservative_cartridge_capacity_without_sink_credit():
    closure = screen_cycle_resolved_routing_closure(build_authority_waste_fluid_budget(), prime_events_by_cycle=[1]*6, prime_recovery_ratio_contract=.90, prime_residual_ratio_contract=.08, prime_external_leakage_ratio_contract=.02)
    assert [c.cumulative_maximum_cartridge_inflow_mL for c in closure.cycles] == pytest.approx([5,10,15,20,25,30])
    assert [c.cartridge_capacity_margin_mL for c in closure.cycles] == pytest.approx([30,25,20,15,10,5])
    assert all(c.cartridge_capacity_satisfied for c in closure.cycles)
    assert closure.first_cartridge_capacity_exceeded_cycle is None
    assert closure.all_cycles_cartridge_capacity_satisfied

def test_cycle_screen_identifies_exact_cycle_where_clustered_reprimes_exceed_capacity():
    closure = screen_cycle_resolved_routing_closure(build_authority_waste_fluid_budget(), prime_events_by_cycle=[0,0,0,0,0,30], prime_recovery_ratio_contract=1.0)
    assert closure.cycles[4].cumulative_maximum_cartridge_inflow_mL == pytest.approx(23.0)
    assert closure.cycles[4].cartridge_capacity_margin_mL == pytest.approx(12.0)
    assert closure.cycles[4].cartridge_capacity_satisfied
    assert closure.cycles[5].cumulative_maximum_cartridge_inflow_mL == pytest.approx(39.6)
    assert closure.cycles[5].cartridge_capacity_margin_mL == pytest.approx(-4.6)
    assert not closure.cycles[5].cartridge_capacity_satisfied
    assert closure.first_cartridge_capacity_exceeded_cycle == 6
    assert not closure.all_cycles_cartridge_capacity_satisfied

def test_prime_without_recovery_contract_gets_no_cartridge_routing_credit():
    closure = screen_cycle_resolved_routing_closure(build_authority_waste_fluid_budget(), prime_events_by_cycle=[2], prime_residual_ratio_contract=.50)
    cycle = closure.cycles[0]
    assert cycle.minimum_nominal_routed_to_cartridge_mL == pytest.approx(4.14)
    assert cycle.minimum_prime_routed_to_cartridge_mL == pytest.approx(0)
    assert cycle.minimum_total_routed_to_cartridge_mL == pytest.approx(4.14)

def test_first_incomplete_cycle_preserves_cycle_locality():
    budget = build_authority_waste_fluid_budget()
    tighter = type(budget)(budget.service_cycles, budget.nominal_introduced_mL_per_cycle, budget.maximum_initial_prime_mL_per_cycle, .91, budget.residual_free_liquid_max_mL, budget.external_leakage_max_mL_per_cycle, budget.cartridge_retained_capacity_requirement_mL)
    closure = screen_cycle_resolved_routing_closure(tighter, prime_events_by_cycle=[0,1,0], prime_recovery_ratio_contract=.90, prime_residual_ratio_contract=.08, prime_external_leakage_ratio_contract=.02)
    assert closure.cycles[0].local_routing_contract_complete
    assert not closure.cycles[1].local_routing_contract_complete
    assert closure.first_incomplete_cycle == 2
    assert not closure.all_cycles_routing_complete

def test_complete_profile_has_no_incomplete_cycle():
    budget = build_authority_waste_fluid_budget()
    tighter = type(budget)(budget.service_cycles, budget.nominal_introduced_mL_per_cycle, budget.maximum_initial_prime_mL_per_cycle, .95, budget.residual_free_liquid_max_mL, budget.external_leakage_max_mL_per_cycle, budget.cartridge_retained_capacity_requirement_mL)
    closure = screen_cycle_resolved_routing_closure(tighter, prime_events_by_cycle=[0,0,0], prime_recovery_ratio_contract=1.0)
    assert closure.first_incomplete_cycle is None
    assert closure.all_cycles_routing_complete

def test_cycle_screen_exposes_shared_sink_shortfall_after_prime_allocation():
    closure = screen_cycle_resolved_routing_closure(build_authority_waste_fluid_budget(), prime_events_by_cycle=[1], prime_recovery_ratio_contract=.90, prime_residual_ratio_contract=.08, prime_external_leakage_ratio_contract=.02)
    cycle = closure.cycles[0]
    assert cycle.classified_sink_capacity_after_prime_mL == pytest.approx(.410)
    assert cycle.nominal_unclassified_nonrecovery_after_prime_mL == pytest.approx(.050)
    assert cycle.classified_sink_headroom_after_nominal_mL == pytest.approx(0)
    assert not cycle.local_routing_contract_complete

def test_clustered_reprimes_cannot_average_external_leakage_across_cycles():
    with pytest.raises(WasteFluidAccountingError, match="leakage contract exceeds"):
        screen_cycle_resolved_routing_closure(build_authority_waste_fluid_budget(), prime_events_by_cycle=[6,0,0,0,0,0], prime_recovery_ratio_contract=.90, prime_external_leakage_ratio_contract=.10)

def test_clustered_reprimes_cannot_average_residual_allocation_across_cycles():
    with pytest.raises(WasteFluidAccountingError, match="residual contract exceeds"):
        screen_cycle_resolved_routing_closure(build_authority_waste_fluid_budget(), prime_events_by_cycle=[6,0,0,0,0,0], prime_recovery_ratio_contract=.50, prime_residual_ratio_contract=.50)

def test_cycle_routing_profile_cannot_extend_past_configured_service_life():
    budget = build_authority_waste_fluid_budget()
    with pytest.raises(WasteFluidAccountingError, match="exceeds configured service life"):
        screen_cycle_resolved_routing_closure(budget, prime_events_by_cycle=[0]*7, prime_recovery_ratio_contract=1.0)

def test_cycle_routing_profile_may_screen_a_service_life_prefix():
    closure = screen_cycle_resolved_routing_closure(build_authority_waste_fluid_budget(), prime_events_by_cycle=[1,0,2], prime_recovery_ratio_contract=1.0)
    assert len(closure.cycles) == 3
    assert closure.service.cycles == 3
    assert closure.service.prime_events == 3
    assert closure.service.minimum_nominal_liquid_routed_to_cartridge_mL == pytest.approx(3 * 4.14)
    assert closure.minimum_total_routed_to_cartridge_mL == pytest.approx(3 * 4.14 + 3 * .4)

def test_cycle_resolved_routing_rejects_invalid_schedules():
    budget = build_authority_waste_fluid_budget()
    for schedule in ([], (), [1,-1], [True], [1.5]):
        with pytest.raises(WasteFluidAccountingError):
            screen_cycle_resolved_routing_closure(budget, prime_events_by_cycle=schedule)
