import pytest

from retention_adjuster_wear_sequence import AdjusterWearState, evaluate_adjuster_wear_sequence


def evaluate(states):
    return evaluate_adjuster_wear_sequence(
        states=states,
        initial_reachable_travel_mm=24.0,
        required_travel_mm=21.0,
        initial_increment_mm=1.0,
        retention_stiffness_n_per_mm=4.0,
        max_tension_error_n=2.5,
        initial_backdrive_capacity_n=30.0,
        max_service_tension_n=20.0,
        service_tension_uncertainty_n=2.0,
        required_backdrive_margin_n=3.0,
    )


def good():
    return [
        AdjusterWearState(0, 0.0, 0.0, 0.0),
        AdjusterWearState(1000, 0.05, 0.4, 1.0),
        AdjusterWearState(5000, 0.10, 1.0, 2.0),
    ]


def test_monotonic_sequence_closes():
    result = evaluate(good())
    assert result.monotonic_degradation
    assert result.every_state_closed
    assert result.first_failing_cycle is None
    assert result.screening_closed


def test_intermediate_failure_cannot_be_hidden_by_later_recovery():
    states = good()
    states[1] = AdjusterWearState(1000, 0.40, 0.4, 1.0)
    states[2] = AdjusterWearState(5000, 0.10, 1.0, 2.0)
    result = evaluate(states)
    assert result.first_failing_cycle == 1000
    assert not result.monotonic_degradation
    assert not result.screening_closed


def test_nonmonotonic_endpoint_loss_fails_even_if_each_state_passes():
    states = good()
    states[1] = AdjusterWearState(1000, 0.05, 0.8, 1.0)
    states[2] = AdjusterWearState(5000, 0.10, 0.7, 2.0)
    result = evaluate(states)
    assert result.every_state_closed
    assert not result.monotonic_degradation
    assert not result.screening_closed


def test_backdrive_failure_reports_first_cycle():
    states = good() + [AdjusterWearState(10000, 0.15, 1.5, 6.0)]
    result = evaluate(states)
    assert result.first_failing_cycle == 10000
    assert not result.every_state_closed


def test_requires_zero_cycle_baseline():
    with pytest.raises(ValueError):
        evaluate(good()[1:])


def test_duplicate_or_reversed_cycle_counts_fail_closed():
    with pytest.raises(ValueError):
        evaluate([good()[0], AdjusterWearState(0, 0.1, 0.1, 0.1)])


def test_empty_sequence_fails_closed():
    with pytest.raises(ValueError):
        evaluate([])


def test_negative_or_nonfinite_wear_is_rejected_by_underlying_gate():
    with pytest.raises(ValueError):
        evaluate([good()[0], AdjusterWearState(1, -0.1, 0.0, 0.0)])
