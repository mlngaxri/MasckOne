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


def test_clustered_reprimes_cannot_average_external_leakage_across_cycles():
    # Six primes at a 10% leakage contract total 0.24 mL, below the six-cycle
    # aggregate 0.30 mL ceiling. They are nevertheless invalid when all occur in
    # cycle 1 because that cycle alone would allocate 0.24 mL against a 0.05 mL
    # cycle ceiling.
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


def test_cycle_resolved_routing_rejects_invalid_schedules():
    budget = build_authority_waste_fluid_budget()
    for schedule in ([], (), [1, -1], [True], [1.5]):
        with pytest.raises(WasteFluidAccountingError):
            screen_cycle_resolved_routing_closure(budget, prime_events_by_cycle=schedule)
