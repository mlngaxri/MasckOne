from dataclasses import replace

import pytest

from masck_one.waste_fluid_accounting import WasteFluidAccountingError, build_authority_waste_fluid_budget
from masck_one.waste_fluid_cycle_routing import screen_cycle_resolved_routing_closure
from masck_one.waste_fluid_sink_threshold_trajectory import evaluate_sink_recovery_threshold_trajectory


def _routing(events):
    return screen_cycle_resolved_routing_closure(
        build_authority_waste_fluid_budget(),
        prime_events_by_cycle=events,
        prime_recovery_ratio_contract=.90,
        prime_residual_ratio_contract=.08,
        prime_external_leakage_ratio_contract=.02,
    )


def test_one_prime_per_cycle_exposes_accumulating_recovery_gap():
    trajectory = evaluate_sink_recovery_threshold_trajectory(_routing([1] * 6))
    assert trajectory.first_cycle_requiring_recovery_above_floor == 1
    assert [state.additional_recovery_above_requirement_floor_mL for state in trajectory.cycles] == pytest.approx(
        [.05, .10, .15, .20, .25, .30]
    )
    final = trajectory.cycles[-1]
    assert final.cumulative_nominal_introduced_mL == pytest.approx(27.60)
    assert final.requirement_floor_recovery_mL == pytest.approx(24.84)
    assert final.minimum_recovery_for_sink_closure_mL == pytest.approx(25.14)
    assert final.minimum_recovery_ratio_for_sink_closure == pytest.approx(25.14 / 27.60)
    assert final.cumulative_prime_residual_mL == pytest.approx(.192)
    assert final.cumulative_prime_external_leakage_mL == pytest.approx(.048)
    assert final.cumulative_classified_sink_capacity_after_prime_mL == pytest.approx(2.46)
    assert trajectory.peak_additional_recovery_above_floor_mL == pytest.approx(.30)


def test_zero_prime_profile_retains_baseline_requirement_mismatch_per_cycle():
    trajectory = evaluate_sink_recovery_threshold_trajectory(_routing([0] * 6))
    assert [state.additional_recovery_above_requirement_floor_mL for state in trajectory.cycles] == pytest.approx(
        [.01, .02, .03, .04, .05, .06]
    )
    assert trajectory.cycles[-1].minimum_recovery_for_sink_closure_mL == pytest.approx(24.90)


def test_delayed_prime_event_identifies_when_incremental_gap_changes():
    trajectory = evaluate_sink_recovery_threshold_trajectory(_routing([0, 0, 1, 0, 0, 0]))
    gaps = [state.additional_recovery_above_requirement_floor_mL for state in trajectory.cycles]
    assert gaps == pytest.approx([.01, .02, .07, .08, .09, .10])


def test_trajectory_rejects_forged_cycle_or_service_evidence():
    routing = _routing([1] * 6)
    forged_cycle = replace(routing.cycles[2], classified_sink_capacity_after_prime_mL=99.0)
    with pytest.raises(WasteFluidAccountingError):
        evaluate_sink_recovery_threshold_trajectory(replace(routing, cycles=routing.cycles[:2] + (forged_cycle,) + routing.cycles[3:]))

    forged_service = replace(routing.service, shared_sink_unclassified_nonrecovery_mL=0.0)
    with pytest.raises(WasteFluidAccountingError):
        evaluate_sink_recovery_threshold_trajectory(replace(routing, service=forged_service))


def test_exact_routing_evidence_is_required():
    with pytest.raises(WasteFluidAccountingError):
        evaluate_sink_recovery_threshold_trajectory(object())
