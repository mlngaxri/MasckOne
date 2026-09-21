import pytest

from masck_one.waste_fluid_accounting import WasteFluidAccountingError, build_authority_waste_fluid_budget
from masck_one.waste_fluid_profile import screen_service_profile


def test_capacity_reserve_propagates_through_service_projection_and_reprime_headroom():
    budget = build_authority_waste_fluid_budget()
    profile = screen_service_profile(
        budget,
        prime_events_by_cycle=(1,),
        target_cycles=6,
        future_prime_events_per_remaining_cycle=1,
        capacity_reserve_mL=5.5,
    )

    first = profile.final
    assert profile.capacity_reserve_mL == pytest.approx(5.5)
    assert profile.usable_capacity_mL == pytest.approx(29.5)
    assert first.minimum_projected_service_end_inflow_mL == pytest.approx(30.0)
    assert first.projected_service_end_margin_mL == pytest.approx(-0.5)
    assert first.maximum_additional_prime_events_for_target == 3
    assert first.maximum_unreserved_prime_events_after_contingency == 0
    assert first.service_target_feasible is False
    assert profile.first_target_infeasible_cycle == 1


def test_capacity_reserve_changes_current_cycle_overflow_boundary():
    budget = build_authority_waste_fluid_budget()
    profile = screen_service_profile(
        budget,
        prime_events_by_cycle=(1, 1, 1, 1, 1, 1),
        target_cycles=6,
        capacity_reserve_mL=5.5,
    )

    assert profile.cycles[4].maximum_cartridge_inflow_mL == pytest.approx(25.0)
    assert profile.cycles[4].requirement_margin_mL == pytest.approx(4.5)
    assert profile.cycles[4].capacity_satisfied is True
    assert profile.final.maximum_cartridge_inflow_mL == pytest.approx(30.0)
    assert profile.final.requirement_margin_mL == pytest.approx(-0.5)
    assert profile.final.capacity_satisfied is False
    assert profile.first_overflow_cycle == 6


def test_zero_reserve_preserves_existing_authority_profile_results():
    budget = build_authority_waste_fluid_budget()
    profile = screen_service_profile(
        budget,
        prime_events_by_cycle=(1,),
        target_cycles=6,
        future_prime_events_per_remaining_cycle=1,
    )

    assert profile.capacity_reserve_mL == pytest.approx(0.0)
    assert profile.usable_capacity_mL == pytest.approx(35.0)
    assert profile.final.projected_service_end_margin_mL == pytest.approx(5.0)
    assert profile.final.maximum_additional_prime_events_for_target == 17
    assert profile.final.maximum_unreserved_prime_events_after_contingency == 12
    assert profile.service_target_feasible is True


@pytest.mark.parametrize("reserve", [-0.1, float("nan"), float("inf"), True, "1.0", 35.0, 36.0])
def test_capacity_reserve_rejects_invalid_values(reserve):
    budget = build_authority_waste_fluid_budget()
    with pytest.raises(WasteFluidAccountingError, match="capacity_reserve_mL"):
        screen_service_profile(
            budget,
            prime_events_by_cycle=(1,),
            capacity_reserve_mL=reserve,
        )
