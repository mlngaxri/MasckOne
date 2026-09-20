import pytest

from masck_one.waste_fluid_accounting import WasteFluidAccountingError, build_authority_waste_fluid_budget
from masck_one.waste_fluid_overflow_guard import screen_cartridge_overflow_guard


def test_authority_profile_is_conservatively_inside_cartridge_capacity():
    guard = screen_cartridge_overflow_guard(
        build_authority_waste_fluid_budget(),
        prime_events_by_cycle=[1] * 6,
        prime_recovery_ratio_contract=.90,
        prime_residual_ratio_contract=.08,
        prime_external_leakage_ratio_contract=.02,
    )
    assert guard.capacity_proven_by_conservative_screen
    assert not guard.conservative_fit_unproven
    assert not guard.unavoidable_overflow
    assert guard.capacity_reserve_mL == pytest.approx(0)
    assert guard.usable_capacity_mL == pytest.approx(35)
    assert guard.first_conservative_capacity_failure_cycle is None
    assert guard.first_unavoidable_overflow_cycle is None
    assert guard.minimum_overflow_at_failure_mL == pytest.approx(0)
    assert guard.conservative_overflow_at_failure_mL == pytest.approx(0)
    assert guard.contractual_reserve_headroom_mL == pytest.approx(8.0)
    assert guard.conservative_reserve_headroom_mL == pytest.approx(5.0)


def test_guard_distinguishes_unproven_fit_from_unavoidable_overflow():
    guard = screen_cartridge_overflow_guard(
        build_authority_waste_fluid_budget(),
        prime_events_by_cycle=[0, 0, 0, 0, 0, 20],
        prime_recovery_ratio_contract=.50,
    )
    assert guard.conservative_fit_unproven
    assert not guard.capacity_proven_by_conservative_screen
    assert not guard.unavoidable_overflow
    assert guard.first_conservative_capacity_failure_cycle == 6
    assert guard.first_unavoidable_overflow_cycle is None
    assert guard.conservative_overflow_at_failure_mL == pytest.approx(.6)
    assert guard.minimum_overflow_at_failure_mL == pytest.approx(0)
    assert guard.contractual_reserve_headroom_mL == pytest.approx(6.16)
    assert guard.conservative_reserve_headroom_mL == pytest.approx(-.6)


def test_guard_quantifies_first_unavoidable_overflow_without_sink_credit():
    guard = screen_cartridge_overflow_guard(
        build_authority_waste_fluid_budget(),
        prime_events_by_cycle=[0, 0, 0, 0, 0, 30],
        prime_recovery_ratio_contract=1.0,
    )
    assert guard.unavoidable_overflow
    assert guard.conservative_fit_unproven
    assert guard.first_unavoidable_overflow_cycle == 6
    assert guard.first_conservative_capacity_failure_cycle == 6
    assert guard.minimum_overflow_at_failure_mL == pytest.approx(1.84)
    assert guard.conservative_overflow_at_failure_mL == pytest.approx(4.6)
    assert guard.contractual_reserve_headroom_mL == pytest.approx(-1.84)
    assert guard.conservative_reserve_headroom_mL == pytest.approx(-4.6)


def test_guard_preserves_prefix_service_screening():
    guard = screen_cartridge_overflow_guard(
        build_authority_waste_fluid_budget(),
        prime_events_by_cycle=[0, 2, 0],
        prime_recovery_ratio_contract=1.0,
    )
    assert len(guard.routing.cycles) == 3
    assert guard.capacity_proven_by_conservative_screen
    assert guard.contractual_reserve_headroom_mL == pytest.approx(21.78)
    assert guard.conservative_reserve_headroom_mL == pytest.approx(20.4)


def test_explicit_capacity_reserve_reduces_usable_volume_without_changing_authority_budget():
    budget = build_authority_waste_fluid_budget()
    guard = screen_cartridge_overflow_guard(
        budget,
        prime_events_by_cycle=[1] * 6,
        prime_recovery_ratio_contract=.90,
        prime_residual_ratio_contract=.08,
        prime_external_leakage_ratio_contract=.02,
        capacity_reserve_mL=5.5,
    )
    assert budget.cartridge_retained_capacity_requirement_mL == pytest.approx(35)
    assert guard.capacity_reserve_mL == pytest.approx(5.5)
    assert guard.usable_capacity_mL == pytest.approx(29.5)
    assert guard.conservative_fit_unproven
    assert not guard.unavoidable_overflow
    assert guard.first_conservative_capacity_failure_cycle == 6
    assert guard.conservative_overflow_at_failure_mL == pytest.approx(.5)
    assert guard.contractual_reserve_headroom_mL == pytest.approx(2.5)
    assert guard.conservative_reserve_headroom_mL == pytest.approx(-.5)


@pytest.mark.parametrize("reserve", [-.001, float("nan"), float("inf"), 35.0, 36.0, True, "1"])
def test_capacity_reserve_rejects_invalid_or_nonphysical_values(reserve):
    with pytest.raises(WasteFluidAccountingError):
        screen_cartridge_overflow_guard(
            build_authority_waste_fluid_budget(),
            prime_events_by_cycle=[0] * 6,
            capacity_reserve_mL=reserve,
        )
