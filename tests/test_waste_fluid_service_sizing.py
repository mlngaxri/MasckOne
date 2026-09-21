import pytest

from masck_one.waste_fluid_accounting import (
    WasteFluidAccountingError,
    build_authority_waste_fluid_budget,
)
from masck_one.waste_fluid_profile import screen_service_profile
from masck_one.waste_fluid_service_sizing import derive_service_capacity_sizing_interval


def test_authority_service_profile_exposes_capacity_sizing_interval():
    budget = build_authority_waste_fluid_budget()
    profile = screen_service_profile(
        budget,
        prime_events_by_cycle=(1, 1, 1, 1, 1, 1),
        target_cycles=6,
    )

    sizing = derive_service_capacity_sizing_interval(profile)

    assert sizing.contractual_required_usable_capacity_mL == pytest.approx(27.0)
    assert sizing.conservative_required_usable_capacity_mL == pytest.approx(30.0)
    assert sizing.unresolved_capacity_interval_mL == pytest.approx(3.0)
    assert sizing.capacity_reserve_mL == pytest.approx(0.0)
    assert sizing.usable_capacity_mL == pytest.approx(35.0)
    assert sizing.retained_capacity_requirement_mL == pytest.approx(35.0)
    assert sizing.contractual_required_retained_capacity_mL == pytest.approx(27.0)
    assert sizing.conservative_required_retained_capacity_mL == pytest.approx(30.0)
    assert sizing.contractual_headroom_mL == pytest.approx(8.0)
    assert sizing.conservative_headroom_mL == pytest.approx(5.0)
    assert sizing.contractual_fit is True
    assert sizing.conservative_fit is True


def test_explicit_reserve_is_added_back_to_retained_capacity_sizing_bounds():
    budget = build_authority_waste_fluid_budget()
    profile = screen_service_profile(
        budget,
        prime_events_by_cycle=(1, 1, 1, 1, 1, 1),
        target_cycles=6,
        capacity_reserve_mL=5.5,
    )

    sizing = derive_service_capacity_sizing_interval(profile)

    assert sizing.capacity_reserve_mL == pytest.approx(5.5)
    assert sizing.usable_capacity_mL == pytest.approx(29.5)
    assert sizing.retained_capacity_requirement_mL == pytest.approx(35.0)
    assert sizing.contractual_required_usable_capacity_mL == pytest.approx(27.0)
    assert sizing.conservative_required_usable_capacity_mL == pytest.approx(30.0)
    assert sizing.contractual_required_retained_capacity_mL == pytest.approx(32.5)
    assert sizing.conservative_required_retained_capacity_mL == pytest.approx(35.5)
    assert sizing.contractual_headroom_mL == pytest.approx(2.5)
    assert sizing.conservative_headroom_mL == pytest.approx(-0.5)
    assert sizing.contractual_fit is True
    assert sizing.conservative_fit is False


def test_future_reprime_contingency_is_charged_to_conservative_sizing_bound():
    budget = build_authority_waste_fluid_budget()
    profile = screen_service_profile(
        budget,
        prime_events_by_cycle=(1,),
        target_cycles=6,
        future_prime_events_per_remaining_cycle=2,
    )

    sizing = derive_service_capacity_sizing_interval(profile)

    assert sizing.contractual_required_usable_capacity_mL == pytest.approx(27.0)
    assert sizing.conservative_required_usable_capacity_mL == pytest.approx(32.0)
    assert sizing.contractual_required_retained_capacity_mL == pytest.approx(27.0)
    assert sizing.conservative_required_retained_capacity_mL == pytest.approx(32.0)
    assert sizing.unresolved_capacity_interval_mL == pytest.approx(5.0)
    assert sizing.conservative_headroom_mL == pytest.approx(3.0)


def test_future_reprime_and_capacity_reserve_compose_without_double_credit():
    budget = build_authority_waste_fluid_budget()
    profile = screen_service_profile(
        budget,
        prime_events_by_cycle=(1,),
        target_cycles=6,
        future_prime_events_per_remaining_cycle=2,
        capacity_reserve_mL=4.0,
    )

    sizing = derive_service_capacity_sizing_interval(profile)

    assert sizing.usable_capacity_mL == pytest.approx(31.0)
    assert sizing.retained_capacity_requirement_mL == pytest.approx(35.0)
    assert sizing.contractual_required_retained_capacity_mL == pytest.approx(31.0)
    assert sizing.conservative_required_retained_capacity_mL == pytest.approx(36.0)
    assert sizing.contractual_headroom_mL == pytest.approx(4.0)
    assert sizing.conservative_headroom_mL == pytest.approx(-1.0)
    assert sizing.contractual_fit is True
    assert sizing.conservative_fit is False


def test_sizing_rejects_non_profile_evidence():
    with pytest.raises(WasteFluidAccountingError, match="exact ServiceFluidProfile"):
        derive_service_capacity_sizing_interval(object())
