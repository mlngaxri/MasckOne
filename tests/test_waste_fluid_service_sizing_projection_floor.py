import pytest

from masck_one.waste_fluid_accounting import (
    WasteFluidAccountingError,
    build_authority_waste_fluid_budget,
)
from masck_one.waste_fluid_profile import screen_service_profile
from masck_one.waste_fluid_service_sizing import derive_service_capacity_sizing_interval


def test_sizing_rejects_projected_recovery_below_already_recovered_volume():
    budget = build_authority_waste_fluid_budget()
    profile = screen_service_profile(budget, prime_events_by_cycle=(1,), target_cycles=1)

    # Simulate stale/corrupted future evidence while leaving the accumulated
    # cycle evidence intact. The capacity reducer must not accept a projection
    # that effectively removes liquid already assigned to mandatory recovery.
    object.__setattr__(profile.cycles[0], "minimum_projected_service_end_recovered_mL", 0.0)

    with pytest.raises(WasteFluidAccountingError, match="below already recovered volume"):
        derive_service_capacity_sizing_interval(profile)


def test_sizing_rejects_projected_inflow_below_already_accumulated_inflow():
    budget = build_authority_waste_fluid_budget()
    profile = screen_service_profile(budget, prime_events_by_cycle=(1,), target_cycles=1)

    # A service-end cartridge projection cannot be smaller than cartridge
    # inflow already accumulated at the current cycle boundary.
    object.__setattr__(profile.cycles[0], "minimum_projected_service_end_inflow_mL", 0.0)

    with pytest.raises(WasteFluidAccountingError, match="below already accumulated cartridge inflow"):
        derive_service_capacity_sizing_interval(profile)
