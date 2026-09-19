import pytest

from masck_one.waste_fluid_accounting import (
    WasteFluidAccountingError,
    build_authority_waste_fluid_budget,
)
from masck_one.waste_fluid_profile import screen_service_profile


def test_profile_reconciles_to_aggregate_capacity_screen():
    budget = build_authority_waste_fluid_budget()
    profile = screen_service_profile(budget, prime_events_by_cycle=(1, 1, 1, 1, 1, 1))
    aggregate = budget.service_capacity_screen(cycles=6, prime_events=6)

    assert profile.capacity_satisfied is True
    assert profile.service_target_feasible is True
    assert profile.first_overflow_cycle is None
    assert profile.first_target_infeasible_cycle is None
    assert profile.target_cycles == 6
    assert profile.final.cumulative_prime_events == 6
    assert profile.final.maximum_cartridge_inflow_mL == pytest.approx(
        aggregate.maximum_cartridge_inflow_mL
    )
    assert profile.final.minimum_projected_service_end_inflow_mL == pytest.approx(30.0)
    assert profile.final.projected_service_end_margin_mL == pytest.approx(5.0)
    assert profile.final.requirement_margin_mL == pytest.approx(5.0)


def test_profile_exposes_cycle_where_reprime_burst_first_overflows():
    budget = build_authority_waste_fluid_budget()
    profile = screen_service_profile(budget, prime_events_by_cycle=(1, 1, 1, 1, 1, 14))

    assert profile.cycles[4].maximum_cartridge_inflow_mL == pytest.approx(25.0)
    assert profile.cycles[4].capacity_satisfied is True
    assert profile.final.cumulative_prime_events == 19
    assert profile.final.maximum_cartridge_inflow_mL == pytest.approx(35.2)
    assert profile.final.requirement_margin_mL == pytest.approx(-0.2)
    assert profile.first_overflow_cycle == 6
    assert profile.first_target_infeasible_cycle == 6
    assert profile.capacity_satisfied is False
    assert profile.service_target_feasible is False


def test_profile_flags_lost_service_life_before_cartridge_overflows():
    budget = build_authority_waste_fluid_budget()
    profile = screen_service_profile(
        budget,
        prime_events_by_cycle=(19,),
        target_cycles=6,
    )

    first = profile.cycles[0]
    assert first.maximum_cartridge_inflow_mL == pytest.approx(12.2)
    assert first.capacity_satisfied is True
    assert first.minimum_projected_service_end_inflow_mL == pytest.approx(35.2)
    assert first.projected_service_end_margin_mL == pytest.approx(-0.2)
    assert first.service_target_feasible is False
    assert profile.first_overflow_cycle is None
    assert profile.first_target_infeasible_cycle == 1
    assert profile.capacity_satisfied is True
    assert profile.service_target_feasible is False


def test_profile_preserves_service_target_boundary_at_eighteen_primes():
    budget = build_authority_waste_fluid_budget()
    profile = screen_service_profile(
        budget,
        prime_events_by_cycle=(18,),
        target_cycles=6,
    )

    first = profile.cycles[0]
    assert first.minimum_projected_service_end_inflow_mL == pytest.approx(34.8)
    assert first.projected_service_end_margin_mL == pytest.approx(0.2)
    assert first.service_target_feasible is True
    assert profile.first_target_infeasible_cycle is None


def test_profile_preserves_multiple_reprimes_within_one_cycle():
    budget = build_authority_waste_fluid_budget()
    profile = screen_service_profile(budget, prime_events_by_cycle=(3, 0))

    assert profile.cycles[0].prime_events_this_cycle == 3
    assert profile.cycles[0].cumulative_prime_events == 3
    assert profile.cycles[0].cumulative_prime_mL == pytest.approx(1.2)
    assert profile.final.cumulative_prime_events == 3
    assert profile.final.maximum_cartridge_inflow_mL == pytest.approx(10.4)
    assert profile.final.minimum_projected_service_end_inflow_mL == pytest.approx(28.8)


def test_profile_rejects_empty_or_invalid_prime_schedule():
    budget = build_authority_waste_fluid_budget()
    with pytest.raises(WasteFluidAccountingError, match="at least one cycle"):
        screen_service_profile(budget, prime_events_by_cycle=())
    with pytest.raises(WasteFluidAccountingError, match="nonnegative integers"):
        screen_service_profile(budget, prime_events_by_cycle=(1, True))
    with pytest.raises(WasteFluidAccountingError, match="nonnegative integers"):
        screen_service_profile(budget, prime_events_by_cycle=(1, -1))
    with pytest.raises(WasteFluidAccountingError, match="positive integer"):
        screen_service_profile(budget, prime_events_by_cycle=(1,), target_cycles=True)
    with pytest.raises(WasteFluidAccountingError, match="less than the profiled"):
        screen_service_profile(budget, prime_events_by_cycle=(0, 0), target_cycles=1)
