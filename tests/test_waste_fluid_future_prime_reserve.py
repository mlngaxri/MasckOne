from dataclasses import replace

import pytest

from masck_one.waste_fluid_accounting import WasteFluidAccountingError, build_authority_waste_fluid_budget
from masck_one.waste_fluid_profile import screen_service_profile


def test_future_prime_reserve_closes_zero_reprime_projection_blind_spot():
    budget = build_authority_waste_fluid_budget()
    profile = screen_service_profile(
        budget,
        prime_events_by_cycle=(1,),
        target_cycles=6,
        future_prime_events_per_remaining_cycle=1,
    )

    first = profile.final
    assert profile.future_prime_events_per_remaining_cycle == 1
    assert first.reserved_future_prime_events == 5
    assert first.reserved_future_prime_mL == pytest.approx(2.0)
    assert first.minimum_projected_service_end_inflow_mL == pytest.approx(30.0)
    assert first.projected_service_end_margin_mL == pytest.approx(5.0)
    assert first.service_target_feasible is True


def test_remaining_prime_allowance_exposes_exact_service_target_headroom():
    budget = build_authority_waste_fluid_budget()
    profile = screen_service_profile(budget, prime_events_by_cycle=(1,), target_cycles=6)

    first = profile.final
    assert first.maximum_additional_prime_events_for_target == 17
    boundary = screen_service_profile(budget, prime_events_by_cycle=(18,), target_cycles=6)
    assert boundary.final.maximum_additional_prime_events_for_target == 0
    assert boundary.final.projected_service_end_margin_mL == pytest.approx(0.2)


def test_remaining_prime_allowance_decrements_with_observed_reprime_loading():
    budget = build_authority_waste_fluid_budget()
    one_prime = screen_service_profile(budget, prime_events_by_cycle=(1,), target_cycles=6).final
    two_primes = screen_service_profile(budget, prime_events_by_cycle=(2,), target_cycles=6).final

    assert one_prime.maximum_additional_prime_events_for_target == 17
    assert two_primes.maximum_additional_prime_events_for_target == 16


def test_zero_volume_prime_has_unbounded_capacity_allowance():
    budget = replace(build_authority_waste_fluid_budget(), maximum_initial_prime_mL_per_cycle=0.0)
    profile = screen_service_profile(budget, prime_events_by_cycle=(100,), target_cycles=6)
    assert profile.final.maximum_additional_prime_events_for_target is None


def test_future_prime_reserve_can_expose_lost_service_life_early():
    budget = build_authority_waste_fluid_budget()
    profile = screen_service_profile(
        budget,
        prime_events_by_cycle=(1,),
        target_cycles=6,
        future_prime_events_per_remaining_cycle=4,
    )

    first = profile.final
    assert first.reserved_future_prime_events == 20
    assert first.reserved_future_prime_mL == pytest.approx(8.0)
    assert first.minimum_projected_service_end_inflow_mL == pytest.approx(36.0)
    assert first.projected_service_end_margin_mL == pytest.approx(-1.0)
    assert first.service_target_feasible is False
    assert profile.first_target_infeasible_cycle == 1
    assert profile.first_overflow_cycle is None


def test_future_prime_reserve_is_only_applied_to_unprofiled_cycles():
    budget = build_authority_waste_fluid_budget()
    profile = screen_service_profile(
        budget,
        prime_events_by_cycle=(1, 1, 1, 1, 1, 1),
        target_cycles=6,
        future_prime_events_per_remaining_cycle=100,
    )

    assert profile.final.reserved_future_prime_events == 0
    assert profile.final.reserved_future_prime_mL == pytest.approx(0.0)
    assert profile.final.minimum_projected_service_end_inflow_mL == pytest.approx(30.0)


def test_future_prime_reserve_rejects_invalid_counts():
    budget = build_authority_waste_fluid_budget()
    with pytest.raises(WasteFluidAccountingError, match="nonnegative integer"):
        screen_service_profile(
            budget,
            prime_events_by_cycle=(0,),
            future_prime_events_per_remaining_cycle=-1,
        )
    with pytest.raises(WasteFluidAccountingError, match="nonnegative integer"):
        screen_service_profile(
            budget,
            prime_events_by_cycle=(0,),
            future_prime_events_per_remaining_cycle=True,
        )
