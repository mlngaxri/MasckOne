import pytest

from masck_one.waste_fluid_accounting import WasteFluidAccountingError, build_authority_waste_fluid_budget
from masck_one.waste_fluid_capacity_reserve import (
    CartridgeCapacityReserve,
    screen_cartridge_capacity_reserve,
    screen_service_profile_with_capacity_reserve,
)


def _overflowing_reserve() -> CartridgeCapacityReserve:
    # Each owner-supplied allowance is finite, but their composition overflows.
    return CartridgeCapacityReserve(
        fill_sensor_trip_mL=1e308,
        foam_allowance_mL=1e308,
    )


def test_composed_reserve_total_rejects_finite_components_that_overflow_sum():
    with pytest.raises(WasteFluidAccountingError, match="total must remain finite"):
        _ = _overflowing_reserve().total_mL


def test_overflow_guard_rejects_nonfinite_composed_reserve_before_capacity_math():
    with pytest.raises(WasteFluidAccountingError, match="total must remain finite"):
        screen_cartridge_capacity_reserve(
            build_authority_waste_fluid_budget(),
            _overflowing_reserve(),
            prime_events_by_cycle=[0] * 6,
        )


def test_service_profile_rejects_nonfinite_composed_reserve_before_capacity_math():
    with pytest.raises(WasteFluidAccountingError, match="total must remain finite"):
        screen_service_profile_with_capacity_reserve(
            build_authority_waste_fluid_budget(),
            _overflowing_reserve(),
            prime_events_by_cycle=[0] * 6,
        )
