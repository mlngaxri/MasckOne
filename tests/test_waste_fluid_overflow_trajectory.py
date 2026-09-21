from dataclasses import replace

import pytest

from masck_one.waste_fluid_accounting import WasteFluidAccountingError, build_authority_waste_fluid_budget
from masck_one.waste_fluid_overflow_guard import screen_cartridge_overflow_guard
from masck_one.waste_fluid_overflow_trajectory import build_cartridge_overflow_trajectory


def _guard(primes, ratio=1.0, reserve=0.0):
    return screen_cartridge_overflow_guard(
        build_authority_waste_fluid_budget(),
        prime_events_by_cycle=primes,
        prime_recovery_ratio_contract=ratio,
        capacity_reserve_mL=reserve,
    )


def test_authority_profile_has_zero_overflow_trajectory():
    trajectory = build_cartridge_overflow_trajectory(_guard([1] * 6, .90))
    assert len(trajectory.states) == 6
    assert all(state.contractual_overflow_mL == pytest.approx(0) for state in trajectory.states)
    assert all(state.conservative_overflow_mL == pytest.approx(0) for state in trajectory.states)


def test_trajectory_exposes_overflow_accumulation_after_first_failure():
    trajectory = build_cartridge_overflow_trajectory(_guard([20] * 6))
    contractual = [state.contractual_overflow_mL for state in trajectory.states]
    conservative = [state.conservative_overflow_mL for state in trajectory.states]
    assert contractual == sorted(contractual)
    assert conservative == sorted(conservative)
    assert trajectory.states[-1].contractual_overflow_mL > next(v for v in contractual if v > 0)
    assert trajectory.states[-1].conservative_overflow_mL > next(v for v in conservative if v > 0)
    assert sum(state.contractual_increment_mL for state in trajectory.states) == pytest.approx(trajectory.guard.contractual_end_of_service_overflow_mL)
    assert sum(state.conservative_increment_mL for state in trajectory.states) == pytest.approx(trajectory.guard.conservative_end_of_service_overflow_mL)


def test_reserved_capacity_is_applied_to_every_cycle_state():
    base = build_cartridge_overflow_trajectory(_guard([1] * 6, .90))
    reserved = build_cartridge_overflow_trajectory(_guard([1] * 6, .90, reserve=5.5))
    assert base.states[-1].conservative_overflow_mL == pytest.approx(0)
    assert reserved.states[-1].conservative_overflow_mL == pytest.approx(.5)
    assert reserved.states[-1].conservative_increment_mL == pytest.approx(.5)


def test_trajectory_rejects_tampered_intermediate_overflow_state():
    trajectory = build_cartridge_overflow_trajectory(_guard([20] * 6))
    states = list(trajectory.states)
    states[3] = replace(states[3], conservative_overflow_mL=states[3].conservative_overflow_mL + .1)
    with pytest.raises(WasteFluidAccountingError, match="stale or inconsistent"):
        replace(trajectory, states=tuple(states))


def test_trajectory_rejects_lookalike_guard():
    with pytest.raises(WasteFluidAccountingError, match="exact CartridgeOverflowGuard"):
        build_cartridge_overflow_trajectory(object())
