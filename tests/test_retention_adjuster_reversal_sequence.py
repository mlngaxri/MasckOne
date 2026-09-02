import pytest

from masck_one.retention_adjuster_reversal_sequence import ReversalSample, evaluate_reversal_sequence


def test_sequence_closes_when_all_checkpoints_close():
    result = evaluate_reversal_sequence(
        [ReversalSample(0, 0.10, 0.02), ReversalSample(1000, 0.14, 0.02)],
        member_stiffness_n_per_mm=2.0,
        max_effective_lost_motion_mm=0.20,
        max_tension_deadband_n=0.50,
    )
    assert result.passes
    assert result.first_failing_cycle is None


def test_intermediate_failure_is_preserved():
    result = evaluate_reversal_sequence(
        [ReversalSample(0, 0.10, 0.01), ReversalSample(500, 0.22, 0.01), ReversalSample(1000, 0.24, 0.01)],
        member_stiffness_n_per_mm=1.0,
        max_effective_lost_motion_mm=0.20,
        max_tension_deadband_n=1.0,
    )
    assert not result.passes
    assert result.first_failing_cycle == 500


def test_stiffness_can_fail_tension_deadband_before_motion_limit():
    result = evaluate_reversal_sequence(
        [ReversalSample(0, 0.10, 0.01), ReversalSample(100, 0.12, 0.01)],
        member_stiffness_n_per_mm=5.0,
        max_effective_lost_motion_mm=0.50,
        max_tension_deadband_n=0.60,
    )
    assert not result.passes
    assert result.first_failing_cycle == 100


def test_apparent_recovery_fails_closed():
    with pytest.raises(ValueError):
        evaluate_reversal_sequence(
            [ReversalSample(0, 0.10, 0.02), ReversalSample(100, 0.20, 0.02), ReversalSample(200, 0.15, 0.02)],
            member_stiffness_n_per_mm=1.0,
            max_effective_lost_motion_mm=1.0,
            max_tension_deadband_n=1.0,
        )


@pytest.mark.parametrize("samples", [[], [ReversalSample(10, 0.1, 0.0)], [ReversalSample(0, -0.1, 0.0)]])
def test_malformed_sequences_fail_closed(samples):
    with pytest.raises(ValueError):
        evaluate_reversal_sequence(samples, member_stiffness_n_per_mm=1.0, max_effective_lost_motion_mm=1.0, max_tension_deadband_n=1.0)


def test_duplicate_cycle_fails_closed():
    with pytest.raises(ValueError):
        evaluate_reversal_sequence(
            [ReversalSample(0, 0.1, 0.0), ReversalSample(0, 0.1, 0.0)],
            member_stiffness_n_per_mm=1.0,
            max_effective_lost_motion_mm=1.0,
            max_tension_deadband_n=1.0,
        )
