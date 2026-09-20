import math

import pytest

from masck_one.waste_fluid_accounting import WasteFluidAccountingError, build_authority_waste_fluid_budget
from masck_one.waste_fluid_capacity_reserve import (
    CartridgeCapacityReserve,
    screen_cartridge_capacity_reserve,
)


def _screen(reserve):
    return screen_cartridge_capacity_reserve(
        build_authority_waste_fluid_budget(),
        reserve,
        prime_events_by_cycle=[1] * 6,
        prime_recovery_ratio_contract=.90,
        prime_residual_ratio_contract=.08,
        prime_external_leakage_ratio_contract=.02,
    )


def test_reserve_components_sum_without_changing_authority_capacity():
    reserve = CartridgeCapacityReserve(
        fill_sensor_trip_mL=1.0,
        foam_allowance_mL=1.5,
        manufacturing_tolerance_mL=.5,
        other_integration_mL=1.0,
    )
    guard = _screen(reserve)
    assert reserve.total_mL == pytest.approx(4.0)
    assert guard.capacity_reserve_mL == pytest.approx(4.0)
    assert guard.usable_capacity_mL == pytest.approx(31.0)
    assert guard.capacity_proven_by_conservative_screen
    assert build_authority_waste_fluid_budget().cartridge_retained_capacity_requirement_mL == pytest.approx(35.0)


def test_composed_reserve_exposes_conservative_capacity_failure():
    reserve = CartridgeCapacityReserve(fill_sensor_trip_mL=2.0, foam_allowance_mL=3.5)
    guard = _screen(reserve)
    assert guard.usable_capacity_mL == pytest.approx(29.5)
    assert guard.first_conservative_capacity_failure_cycle == 6
    assert guard.conservative_overflow_at_failure_mL == pytest.approx(.5)
    assert guard.first_unavoidable_overflow_cycle is None


@pytest.mark.parametrize("bad", [-.01, math.inf, -math.inf, math.nan, True, "1"])
def test_invalid_reserve_component_fails_closed(bad):
    reserve = CartridgeCapacityReserve(foam_allowance_mL=bad)
    with pytest.raises(WasteFluidAccountingError):
        _screen(reserve)


def test_reserve_cannot_consume_entire_controlled_capacity():
    with pytest.raises(WasteFluidAccountingError):
        _screen(CartridgeCapacityReserve(other_integration_mL=35.0))


def test_exact_reserve_type_is_required():
    with pytest.raises(WasteFluidAccountingError):
        screen_cartridge_capacity_reserve(
            build_authority_waste_fluid_budget(),
            object(),
            prime_events_by_cycle=[1] * 6,
        )
