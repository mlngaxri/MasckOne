from dataclasses import replace

import pytest

from masck_one.waste_fluid_accounting import WasteFluidAccountingError, build_authority_waste_fluid_budget
from masck_one.waste_fluid_capacity_crossing import quantify_cartridge_capacity_crossings
from masck_one.waste_fluid_capacity_milestones import screen_cartridge_capacity_milestones
from masck_one.waste_fluid_overflow_guard import screen_cartridge_overflow_guard


def _crossings(primes, ratio=1.0, reserve=0.0):
    guard = screen_cartridge_overflow_guard(
        build_authority_waste_fluid_budget(), prime_events_by_cycle=primes,
        prime_recovery_ratio_contract=ratio, capacity_reserve_mL=reserve,
    )
    return quantify_cartridge_capacity_crossings(screen_cartridge_capacity_milestones(guard))


def test_crossing_windows_bracket_each_reached_threshold_without_interpolation():
    evidence = _crossings([1] * 6, ratio=.90)
    assert evidence.windows
    usable = evidence.source.guard.usable_capacity_mL
    for window in evidence.windows:
        assert window.volume_before_cycle_mL < window.threshold_volume_mL + 1e-12
        assert window.crossing_volume_mL >= window.threshold_volume_mL - 1e-12
        assert window.volume_before_cycle_mL + window.cycle_increment_mL == pytest.approx(window.crossing_volume_mL)
        assert window.headroom_before_cycle_mL + window.overshoot_after_cycle_mL == pytest.approx(window.cycle_increment_mL)
        assert window.utilization_before_cycle == pytest.approx(window.volume_before_cycle_mL / usable)
        assert window.utilization_after_cycle == pytest.approx(window.crossing_volume_mL / usable)
        assert window.cycle_load_fraction_of_capacity == pytest.approx(window.cycle_increment_mL / usable)
        assert window.utilization_after_cycle - window.utilization_before_cycle == pytest.approx(
            window.cycle_load_fraction_of_capacity)
        assert window.increment_fraction_to_threshold == pytest.approx(
            window.headroom_before_cycle_mL / window.cycle_increment_mL)
        assert window.increment_fraction_after_threshold == pytest.approx(
            window.overshoot_after_cycle_mL / window.cycle_increment_mL)
        assert window.increment_fraction_to_threshold + window.increment_fraction_after_threshold == pytest.approx(1.0)


def test_high_prime_profile_quantifies_full_capacity_crossing_increment():
    evidence = _crossings([20] * 6)
    full = [w for w in evidence.windows if w.utilization_fraction == 1.0]
    assert {w.path for w in full} == {"contractual", "conservative"}
    assert all(w.cycle_increment_mL > 0.0 for w in full)
    assert all(w.cycle_load_fraction_of_capacity > 0.0 for w in full)
    assert all(w.utilization_before_cycle < 1.0 for w in full)
    assert all(w.utilization_after_cycle >= 1.0 for w in full)
    assert all(w.headroom_before_cycle_mL <= w.cycle_increment_mL + 1e-12 for w in full)
    assert all(0.0 < w.increment_fraction_to_threshold <= 1.0 for w in full)
    assert all(0.0 <= w.increment_fraction_after_threshold < 1.0 for w in full)


def test_capacity_reserve_changes_threshold_volume_and_normalized_cycle_load_not_routing_identity():
    base = _crossings([1] * 6, ratio=.90)
    reserved = _crossings([1] * 6, ratio=.90, reserve=5.5)
    assert reserved.source.guard.usable_capacity_mL < base.source.guard.usable_capacity_mL
    assert all(w.threshold_volume_mL == pytest.approx(w.utilization_fraction * reserved.source.guard.usable_capacity_mL)
               for w in reserved.windows)
    common = {(w.utilization_fraction, w.path, w.cycle): w for w in base.windows}
    for window in reserved.windows:
        key = (window.utilization_fraction, window.path, window.cycle)
        if key in common and window.cycle_increment_mL == pytest.approx(common[key].cycle_increment_mL):
            assert window.cycle_load_fraction_of_capacity >= common[key].cycle_load_fraction_of_capacity


def test_unreached_threshold_produces_no_fabricated_crossing_window():
    evidence = _crossings([0] * 6)
    reached = {(w.utilization_fraction, w.path) for w in evidence.windows}
    for milestone in evidence.source.milestones:
        if milestone.first_contractual_cycle is None:
            assert (milestone.utilization_fraction, "contractual") not in reached
        if milestone.first_conservative_cycle is None:
            assert (milestone.utilization_fraction, "conservative") not in reached


def test_crossing_evidence_fails_closed_on_tampered_window():
    evidence = _crossings([20] * 6)
    windows = list(evidence.windows)
    windows[0] = replace(windows[0], cycle_increment_mL=windows[0].cycle_increment_mL + .001)
    with pytest.raises(WasteFluidAccountingError):
        replace(evidence, windows=tuple(windows))


def test_crossing_normalized_load_fails_closed_on_tampered_utilization():
    evidence = _crossings([20] * 6)
    windows = list(evidence.windows)
    windows[0] = replace(windows[0], utilization_after_cycle=windows[0].utilization_after_cycle + .001)
    with pytest.raises(WasteFluidAccountingError):
        replace(evidence, windows=tuple(windows))


def test_crossing_normalized_load_fails_closed_on_tampered_cycle_fraction():
    evidence = _crossings([20] * 6)
    windows = list(evidence.windows)
    windows[0] = replace(
        windows[0], cycle_load_fraction_of_capacity=windows[0].cycle_load_fraction_of_capacity + .001)
    with pytest.raises(WasteFluidAccountingError, match="normalized cycle load"):
        replace(evidence, windows=tuple(windows))


def test_crossing_fraction_fails_closed_on_tampered_threshold_share():
    evidence = _crossings([20] * 6)
    windows = list(evidence.windows)
    windows[0] = replace(
        windows[0], increment_fraction_to_threshold=windows[0].increment_fraction_to_threshold + .001)
    with pytest.raises(WasteFluidAccountingError, match="threshold fraction"):
        replace(evidence, windows=tuple(windows))


def test_crossing_fraction_fails_closed_on_tampered_post_threshold_share():
    evidence = _crossings([20] * 6)
    windows = list(evidence.windows)
    windows[0] = replace(
        windows[0], increment_fraction_after_threshold=windows[0].increment_fraction_after_threshold + .001)
    with pytest.raises(WasteFluidAccountingError, match="post-threshold fraction"):
        replace(evidence, windows=tuple(windows))


def test_lookalike_milestone_evidence_fails_closed():
    with pytest.raises(WasteFluidAccountingError, match="exact milestone evidence"):
        quantify_cartridge_capacity_crossings(object())
