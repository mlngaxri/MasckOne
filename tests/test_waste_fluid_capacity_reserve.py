import math

import pytest

from masck_one.waste_fluid_accounting import WasteFluidAccountingError, build_authority_waste_fluid_budget
from masck_one.waste_fluid_capacity_reserve import (
    CapacityReservedOverflowGuard,
    CapacityReservedServiceProfile,
    CartridgeCapacityReserve,
    screen_cartridge_capacity_reserve,
    screen_cartridge_capacity_reserve_evidence,
    screen_service_profile_with_capacity_reserve,
    screen_service_profile_with_capacity_reserve_evidence,
)
from masck_one.waste_fluid_overflow_guard import screen_cartridge_overflow_guard
from masck_one.waste_fluid_profile import screen_service_profile


def _screen(reserve):
    return screen_cartridge_capacity_reserve(
        build_authority_waste_fluid_budget(), reserve, prime_events_by_cycle=[1] * 6,
        prime_recovery_ratio_contract=.90, prime_residual_ratio_contract=.08,
        prime_external_leakage_ratio_contract=.02,
    )


def test_reserve_components_sum_without_changing_authority_capacity():
    reserve = CartridgeCapacityReserve(1.0, 1.5, .5, 1.0)
    guard = _screen(reserve)
    assert reserve.total_mL == pytest.approx(4.0)
    assert dict(reserve.breakdown_mL) == {"fill_sensor_trip_mL": 1.0, "foam_allowance_mL": 1.5, "manufacturing_tolerance_mL": .5, "other_integration_mL": 1.0}
    assert guard.capacity_reserve_mL == pytest.approx(4.0)
    assert guard.usable_capacity_mL == pytest.approx(31.0)
    assert guard.capacity_proven_by_conservative_screen
    assert build_authority_waste_fluid_budget().cartridge_retained_capacity_requirement_mL == pytest.approx(35.0)


def test_composed_reserve_exposes_conservative_capacity_failure():
    guard = _screen(CartridgeCapacityReserve(fill_sensor_trip_mL=2.0, foam_allowance_mL=3.5))
    assert guard.usable_capacity_mL == pytest.approx(29.5)
    assert guard.first_conservative_capacity_failure_cycle == 6
    assert guard.conservative_overflow_at_failure_mL == pytest.approx(.5)
    assert guard.first_unavoidable_overflow_cycle is None


def test_overflow_evidence_retains_exact_reserve_source():
    budget = build_authority_waste_fluid_budget()
    reserve = CartridgeCapacityReserve(2.0, 2.0, .5, 1.0)
    evidence = screen_cartridge_capacity_reserve_evidence(
        budget, reserve, prime_events_by_cycle=[1] * 6,
        prime_recovery_ratio_contract=.90, prime_residual_ratio_contract=.08,
        prime_external_leakage_ratio_contract=.02,
    )
    assert evidence.reserve is reserve
    assert evidence.guard.capacity_reserve_mL == pytest.approx(5.5)
    assert evidence.guard.usable_capacity_mL == pytest.approx(29.5)
    assert evidence.guard.first_conservative_capacity_failure_cycle == 6


def test_overflow_evidence_rejects_mismatched_scalar_guard():
    budget = build_authority_waste_fluid_budget()
    reserve = CartridgeCapacityReserve(fill_sensor_trip_mL=2.0)
    mismatched = screen_cartridge_overflow_guard(budget, prime_events_by_cycle=[0] * 6, capacity_reserve_mL=1.0)
    with pytest.raises(WasteFluidAccountingError, match="does not match typed reserve"):
        CapacityReservedOverflowGuard(reserve, mismatched)


def test_same_typed_reserve_drives_overflow_and_service_profile_capacity():
    budget = build_authority_waste_fluid_budget()
    reserve = CartridgeCapacityReserve(2.0, 2.0, .5, 1.0)
    guard = screen_cartridge_capacity_reserve(budget, reserve, prime_events_by_cycle=[1] * 6, prime_recovery_ratio_contract=.90, prime_residual_ratio_contract=.08, prime_external_leakage_ratio_contract=.02)
    profile = screen_service_profile_with_capacity_reserve(budget, reserve, prime_events_by_cycle=[1] * 6)
    assert guard.capacity_reserve_mL == pytest.approx(5.5)
    assert profile.capacity_reserve_mL == pytest.approx(guard.capacity_reserve_mL)
    assert profile.usable_capacity_mL == pytest.approx(29.5)
    assert profile.first_overflow_cycle == 6
    assert profile.final.projected_service_end_margin_mL == pytest.approx(-.5)


def test_service_profile_evidence_retains_exact_reserve_source():
    budget = build_authority_waste_fluid_budget()
    reserve = CartridgeCapacityReserve(2.0, 2.0, .5, 1.0)
    evidence = screen_service_profile_with_capacity_reserve_evidence(budget, reserve, prime_events_by_cycle=[1] * 6)
    assert evidence.reserve is reserve
    assert evidence.profile.capacity_reserve_mL == pytest.approx(5.5)
    assert dict(evidence.reserve.breakdown_mL)["foam_allowance_mL"] == pytest.approx(2.0)


def test_service_profile_evidence_rejects_mismatched_scalar_profile():
    budget = build_authority_waste_fluid_budget()
    reserve = CartridgeCapacityReserve(fill_sensor_trip_mL=2.0)
    mismatched = screen_service_profile(budget, prime_events_by_cycle=[0], capacity_reserve_mL=1.0)
    with pytest.raises(WasteFluidAccountingError, match="does not match typed reserve"):
        CapacityReservedServiceProfile(reserve, mismatched)


def test_typed_reserve_profile_propagates_future_prime_contingency():
    profile = screen_service_profile_with_capacity_reserve(build_authority_waste_fluid_budget(), CartridgeCapacityReserve(1.0, 1.0), prime_events_by_cycle=[1, 0], target_cycles=6, future_prime_events_per_remaining_cycle=1)
    assert profile.capacity_reserve_mL == pytest.approx(2.0)
    assert profile.usable_capacity_mL == pytest.approx(33.0)
    assert profile.final.reserved_future_prime_events == 4
    assert profile.final.reserved_future_prime_mL == pytest.approx(1.6)


@pytest.mark.parametrize("bad", [-.01, math.inf, -math.inf, math.nan, True, "1"])
def test_invalid_reserve_component_fails_closed(bad):
    with pytest.raises(WasteFluidAccountingError):
        _screen(CartridgeCapacityReserve(foam_allowance_mL=bad))


def test_reserve_cannot_consume_entire_controlled_capacity():
    with pytest.raises(WasteFluidAccountingError):
        _screen(CartridgeCapacityReserve(other_integration_mL=35.0))


def test_exact_reserve_type_is_required():
    with pytest.raises(WasteFluidAccountingError):
        screen_cartridge_capacity_reserve(build_authority_waste_fluid_budget(), object(), prime_events_by_cycle=[1] * 6)


def test_service_profile_requires_exact_reserve_type_too():
    with pytest.raises(WasteFluidAccountingError):
        screen_service_profile_with_capacity_reserve(build_authority_waste_fluid_budget(), object(), prime_events_by_cycle=[1] * 6)
