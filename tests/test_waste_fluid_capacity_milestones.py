from dataclasses import replace

import pytest

from masck_one.waste_fluid_accounting import WasteFluidAccountingError, build_authority_waste_fluid_budget
from masck_one.waste_fluid_capacity_milestones import screen_cartridge_capacity_milestones
from masck_one.waste_fluid_overflow_guard import screen_cartridge_overflow_guard


def _guard(primes, ratio=1.0, reserve=0.0):
    return screen_cartridge_overflow_guard(
        build_authority_waste_fluid_budget(), prime_events_by_cycle=primes,
        prime_recovery_ratio_contract=ratio, capacity_reserve_mL=reserve,
    )


def test_authority_profile_exposes_approaching_capacity_before_failure():
    evidence = screen_cartridge_capacity_milestones(_guard([1] * 6, .90))
    assert [m.utilization_fraction for m in evidence.milestones] == pytest.approx([.80, .90, 1.0])
    conservative_cycles = [m.first_conservative_cycle for m in evidence.milestones]
    assert all(c is None or 1 <= c <= 6 for c in conservative_cycles)
    assert evidence.guard.first_conservative_capacity_failure_cycle is None


def test_crossing_evidence_quantifies_discrete_cycle_overshoot():
    evidence = screen_cartridge_capacity_milestones(_guard([1] * 6, .90), utilization_fractions=(.80,))
    milestone = evidence.milestones[0]
    assert milestone.first_conservative_cycle is not None
    state = evidence.guard.routing.cycles[milestone.first_conservative_cycle - 1]
    limit = .80 * evidence.guard.usable_capacity_mL
    assert milestone.conservative_crossing_volume_mL == pytest.approx(state.cumulative_maximum_cartridge_inflow_mL)
    assert milestone.conservative_overshoot_mL == pytest.approx(state.cumulative_maximum_cartridge_inflow_mL - limit)
    assert milestone.conservative_overshoot_mL >= 0.0


def test_unreached_milestone_has_no_crossing_evidence():
    evidence = screen_cartridge_capacity_milestones(_guard([0] * 6), utilization_fractions=(1.0,))
    milestone = evidence.milestones[0]
    if milestone.first_contractual_cycle is None:
        assert milestone.contractual_crossing_volume_mL is None
        assert milestone.contractual_overshoot_mL is None


def test_high_prime_profile_reaches_full_capacity_no_later_than_overflow():
    evidence = screen_cartridge_capacity_milestones(_guard([20] * 6))
    full = evidence.milestones[-1]
    assert full.first_contractual_cycle is not None
    assert full.first_conservative_cycle is not None
    assert full.first_conservative_cycle <= full.first_contractual_cycle
    assert full.first_contractual_cycle <= evidence.guard.first_unavoidable_overflow_cycle
    assert full.first_conservative_cycle <= evidence.guard.first_conservative_capacity_failure_cycle
    assert full.contractual_overshoot_mL >= 0.0
    assert full.conservative_overshoot_mL >= 0.0


def test_capacity_reserve_moves_milestones_earlier_or_equal():
    base = screen_cartridge_capacity_milestones(_guard([1] * 6, .90))
    reserved = screen_cartridge_capacity_milestones(_guard([1] * 6, .90, reserve=5.5))
    for b, r in zip(base.milestones, reserved.milestones):
        if b.first_conservative_cycle is not None:
            assert r.first_conservative_cycle is not None
            assert r.first_conservative_cycle <= b.first_conservative_cycle


def test_custom_thresholds_must_be_strictly_increasing():
    with pytest.raises(WasteFluidAccountingError, match="strictly increasing"):
        screen_cartridge_capacity_milestones(_guard([1] * 6), utilization_fractions=(.9, .8))
    with pytest.raises(WasteFluidAccountingError, match="strictly increasing"):
        screen_cartridge_capacity_milestones(_guard([1] * 6), utilization_fractions=(.9, .9))


def test_invalid_thresholds_fail_closed():
    guard = _guard([1] * 6)
    for thresholds in ((), (0.0,), (1.01,), (float("nan"),), (True,)):
        with pytest.raises(WasteFluidAccountingError):
            screen_cartridge_capacity_milestones(guard, utilization_fractions=thresholds)


def test_milestone_evidence_rejects_tampered_cycle_or_overshoot():
    evidence = screen_cartridge_capacity_milestones(_guard([20] * 6))
    milestones = list(evidence.milestones)
    original = milestones[1]
    forged_cycle = None if original.first_conservative_cycle is None else original.first_conservative_cycle + 1
    milestones[1] = replace(original, first_conservative_cycle=forged_cycle)
    with pytest.raises(WasteFluidAccountingError, match="stale or inconsistent"):
        replace(evidence, milestones=tuple(milestones))
    milestones = list(evidence.milestones)
    original = milestones[0]
    milestones[0] = replace(original, conservative_overshoot_mL=original.conservative_overshoot_mL + .001)
    with pytest.raises(WasteFluidAccountingError, match="stale or inconsistent"):
        replace(evidence, milestones=tuple(milestones))


def test_lookalike_guard_fails_closed():
    with pytest.raises(WasteFluidAccountingError, match="exact CartridgeOverflowGuard"):
        screen_cartridge_capacity_milestones(object())
