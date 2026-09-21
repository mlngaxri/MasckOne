from dataclasses import replace

import pytest

from masck_one.waste_fluid_accounting import WasteFluidAccountingError, build_authority_waste_fluid_budget
from masck_one.waste_fluid_overflow_guard import CartridgeOverflowGuard, screen_cartridge_overflow_guard


def _authority_guard(**kwargs):
    return screen_cartridge_overflow_guard(build_authority_waste_fluid_budget(), prime_events_by_cycle=[1] * 6, prime_recovery_ratio_contract=.90, prime_residual_ratio_contract=.08, prime_external_leakage_ratio_contract=.02, **kwargs)


def test_authority_profile_is_conservatively_inside_cartridge_capacity():
    guard = _authority_guard()
    assert guard.capacity_proven_by_conservative_screen
    assert not guard.conservative_fit_unproven
    assert not guard.unavoidable_overflow
    assert guard.retained_capacity_mL == pytest.approx(35)
    assert guard.capacity_reserve_mL == pytest.approx(0)
    assert guard.usable_capacity_mL == pytest.approx(35)
    assert guard.contractual_required_usable_capacity_mL == pytest.approx(27.0)
    assert guard.conservative_required_usable_capacity_mL == pytest.approx(30.0)
    assert guard.sizing_uncertainty_mL == pytest.approx(3.0)
    assert guard.first_conservative_capacity_failure_cycle is None
    assert guard.first_unavoidable_overflow_cycle is None
    assert guard.minimum_overflow_at_failure_mL == pytest.approx(0)
    assert guard.conservative_overflow_at_failure_mL == pytest.approx(0)
    assert guard.contractual_end_of_service_overflow_mL == pytest.approx(0)
    assert guard.conservative_end_of_service_overflow_mL == pytest.approx(0)
    assert guard.contractual_reserve_headroom_mL == pytest.approx(8.0)
    assert guard.conservative_reserve_headroom_mL == pytest.approx(5.0)


def test_guard_distinguishes_unproven_fit_from_unavoidable_overflow():
    guard = screen_cartridge_overflow_guard(build_authority_waste_fluid_budget(), prime_events_by_cycle=[0, 0, 0, 0, 0, 20], prime_recovery_ratio_contract=.50)
    assert guard.conservative_fit_unproven
    assert not guard.capacity_proven_by_conservative_screen
    assert not guard.unavoidable_overflow
    assert guard.first_conservative_capacity_failure_cycle == 6
    assert guard.conservative_overflow_at_failure_mL == pytest.approx(.6)
    assert guard.contractual_required_usable_capacity_mL == pytest.approx(28.84)
    assert guard.conservative_required_usable_capacity_mL == pytest.approx(35.6)
    assert guard.contractual_reserve_headroom_mL == pytest.approx(6.16)
    assert guard.conservative_reserve_headroom_mL == pytest.approx(-.6)
    assert guard.contractual_end_of_service_overflow_mL == pytest.approx(0)
    assert guard.conservative_end_of_service_overflow_mL == pytest.approx(.6)


def test_guard_quantifies_first_unavoidable_overflow_without_sink_credit():
    guard = screen_cartridge_overflow_guard(build_authority_waste_fluid_budget(), prime_events_by_cycle=[0, 0, 0, 0, 0, 30], prime_recovery_ratio_contract=1.0)
    assert guard.unavoidable_overflow
    assert guard.conservative_fit_unproven
    assert guard.first_unavoidable_overflow_cycle == 6
    assert guard.first_conservative_capacity_failure_cycle == 6
    assert guard.minimum_overflow_at_failure_mL == pytest.approx(1.84)
    assert guard.conservative_overflow_at_failure_mL == pytest.approx(4.6)
    assert guard.contractual_required_usable_capacity_mL == pytest.approx(36.84)
    assert guard.conservative_required_usable_capacity_mL == pytest.approx(39.6)
    assert guard.contractual_end_of_service_overflow_mL == pytest.approx(1.84)
    assert guard.conservative_end_of_service_overflow_mL == pytest.approx(4.6)


def test_end_of_service_overflow_reports_accumulated_shortfall_after_early_failure():
    guard = screen_cartridge_overflow_guard(build_authority_waste_fluid_budget(), prime_events_by_cycle=[20, 20, 20, 20, 20, 20], prime_recovery_ratio_contract=1.0)
    assert guard.first_unavoidable_overflow_cycle is not None
    assert guard.first_unavoidable_overflow_cycle < len(guard.routing.cycles)
    assert guard.contractual_end_of_service_overflow_mL > guard.minimum_overflow_at_failure_mL
    assert guard.conservative_end_of_service_overflow_mL > guard.conservative_overflow_at_failure_mL
    assert guard.contractual_end_of_service_overflow_mL == pytest.approx(max(0.0, guard.contractual_required_usable_capacity_mL - guard.usable_capacity_mL))
    assert guard.conservative_end_of_service_overflow_mL == pytest.approx(max(0.0, guard.conservative_required_usable_capacity_mL - guard.usable_capacity_mL))


def test_guard_preserves_prefix_service_screening():
    guard = screen_cartridge_overflow_guard(build_authority_waste_fluid_budget(), prime_events_by_cycle=[0, 2, 0], prime_recovery_ratio_contract=1.0)
    assert len(guard.routing.cycles) == 3
    assert guard.capacity_proven_by_conservative_screen
    assert guard.contractual_reserve_headroom_mL == pytest.approx(21.78)
    assert guard.conservative_reserve_headroom_mL == pytest.approx(20.4)


def test_explicit_capacity_reserve_preserves_physical_capacity_and_reduces_usable_volume():
    budget = build_authority_waste_fluid_budget()
    guard = _authority_guard(capacity_reserve_mL=5.5)
    assert budget.cartridge_retained_capacity_requirement_mL == pytest.approx(35)
    assert guard.retained_capacity_mL == pytest.approx(35)
    assert guard.capacity_reserve_mL == pytest.approx(5.5)
    assert guard.usable_capacity_mL == pytest.approx(29.5)
    assert guard.retained_capacity_mL == pytest.approx(guard.usable_capacity_mL + guard.capacity_reserve_mL)
    assert guard.contractual_required_usable_capacity_mL == pytest.approx(27.0)
    assert guard.conservative_required_usable_capacity_mL == pytest.approx(30.0)
    assert guard.conservative_fit_unproven
    assert guard.first_conservative_capacity_failure_cycle == 6
    assert guard.conservative_overflow_at_failure_mL == pytest.approx(.5)
    assert guard.contractual_end_of_service_overflow_mL == pytest.approx(0)
    assert guard.conservative_end_of_service_overflow_mL == pytest.approx(.5)
    assert guard.contractual_reserve_headroom_mL == pytest.approx(2.5)
    assert guard.conservative_reserve_headroom_mL == pytest.approx(-.5)


@pytest.mark.parametrize("field,value", [
    ("retained_capacity_mL", 34.9), ("usable_capacity_mL", 34.9),
    ("contractual_required_usable_capacity_mL", 26.9), ("conservative_required_usable_capacity_mL", 30.1),
    ("first_conservative_capacity_failure_cycle", 6), ("minimum_overflow_at_failure_mL", .1),
    ("conservative_overflow_at_failure_mL", .1), ("contractual_reserve_headroom_mL", 7.9),
    ("conservative_reserve_headroom_mL", 4.9),
])
def test_guard_rejects_tampered_derived_evidence(field, value):
    guard = _authority_guard()
    with pytest.raises(WasteFluidAccountingError):
        replace(guard, **{field: value})


def test_guard_rejects_reserve_reinterpretation_without_matching_usable_capacity():
    guard = _authority_guard()
    with pytest.raises(WasteFluidAccountingError, match="usable capacity plus reserve"):
        replace(guard, capacity_reserve_mL=1.0)


def test_guard_rejects_lookalike_routing_evidence():
    guard = _authority_guard()
    with pytest.raises(WasteFluidAccountingError):
        CartridgeOverflowGuard(routing=object(), retained_capacity_mL=guard.retained_capacity_mL, capacity_reserve_mL=guard.capacity_reserve_mL, usable_capacity_mL=guard.usable_capacity_mL, contractual_required_usable_capacity_mL=guard.contractual_required_usable_capacity_mL, conservative_required_usable_capacity_mL=guard.conservative_required_usable_capacity_mL, first_unavoidable_overflow_cycle=guard.first_unavoidable_overflow_cycle, first_conservative_capacity_failure_cycle=guard.first_conservative_capacity_failure_cycle, minimum_overflow_at_failure_mL=guard.minimum_overflow_at_failure_mL, conservative_overflow_at_failure_mL=guard.conservative_overflow_at_failure_mL, contractual_reserve_headroom_mL=guard.contractual_reserve_headroom_mL, conservative_reserve_headroom_mL=guard.conservative_reserve_headroom_mL)


@pytest.mark.parametrize("reserve", [-.001, float("nan"), float("inf"), 35.0, 36.0, True, "1"])
def test_capacity_reserve_rejects_invalid_or_nonphysical_values(reserve):
    with pytest.raises(WasteFluidAccountingError):
        screen_cartridge_overflow_guard(build_authority_waste_fluid_budget(), prime_events_by_cycle=[0] * 6, capacity_reserve_mL=reserve)
