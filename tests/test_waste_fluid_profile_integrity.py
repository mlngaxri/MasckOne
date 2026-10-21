from dataclasses import replace

import pytest

from masck_one.waste_fluid_accounting import WasteFluidAccountingError, build_authority_waste_fluid_budget
from masck_one.waste_fluid_profile import screen_service_profile


def _profile():
    budget = build_authority_waste_fluid_budget()
    return screen_service_profile(
        budget,
        prime_events_by_cycle=(1, 0, 1),
        target_cycles=budget.service_cycles,
        future_prime_events_per_remaining_cycle=1,
    )


def test_profile_rejects_noncontiguous_cycle_sequence():
    profile = _profile()
    bad = replace(profile.cycles[1], cycle=4)
    with pytest.raises(WasteFluidAccountingError):
        replace(profile, cycles=(profile.cycles[0], bad, profile.cycles[2]))


def test_profile_rejects_corrupt_cumulative_prime_count():
    profile = _profile()
    bad = replace(profile.cycles[1], cumulative_prime_events=profile.cycles[1].cumulative_prime_events + 1)
    with pytest.raises(WasteFluidAccountingError):
        replace(profile, cycles=(profile.cycles[0], bad, profile.cycles[2]))


def test_profile_rejects_nonfinite_cycle_volume():
    profile = _profile()
    bad = replace(profile.cycles[0], maximum_cartridge_inflow_mL=float("nan"))
    with pytest.raises(WasteFluidAccountingError):
        replace(profile, cycles=(bad,) + profile.cycles[1:])


def test_profile_rejects_broken_recovery_inflow_closure():
    profile = _profile()
    state = profile.cycles[0]
    bad = replace(state, occupancy_uncertainty_mL=state.occupancy_uncertainty_mL + 0.1)
    with pytest.raises(WasteFluidAccountingError):
        replace(profile, cycles=(bad,) + profile.cycles[1:])


def test_profile_rejects_stale_future_prime_reservation():
    profile = _profile()
    state = profile.cycles[0]
    bad = replace(state, reserved_future_prime_events=state.reserved_future_prime_events + 1)
    with pytest.raises(WasteFluidAccountingError):
        replace(profile, cycles=(bad,) + profile.cycles[1:])


def test_profile_rejects_stale_first_failure_marker():
    profile = _profile()
    marker = 1 if profile.first_overflow_cycle is None else None
    with pytest.raises(WasteFluidAccountingError):
        replace(profile, first_overflow_cycle=marker)
