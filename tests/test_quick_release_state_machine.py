import pytest

from masck_one.quick_release_state_machine import (
    MechanicalStateSample, ReleaseState, evaluate_mechanical_state_sequence,
)


def S(x, state, grip, engagement):
    return MechanicalStateSample(x, state, grip, engagement)


def valid_sequence():
    return [
        S(0.0, ReleaseState.LATCHED, False, 0.8),
        S(2.0, ReleaseState.RELEASING, True, 0.5),
        S(4.0, ReleaseState.RELEASED, True, 0.05),
        S(4.0, ReleaseState.RELEASED, False, 0.05),
        S(4.0, ReleaseState.RESET_REQUIRED, False, 0.05),
        S(0.0, ReleaseState.LATCHED, False, 0.8),
    ]


def test_valid_sequence_closes():
    r = evaluate_mechanical_state_sequence(valid_sequence())
    assert r.gate_closed
    assert r.release_travel_mm == 4.0


def test_self_reset_without_reset_required_fails():
    seq = valid_sequence()
    seq[4] = S(0.0, ReleaseState.LATCHED, False, 0.8)
    r = evaluate_mechanical_state_sequence(seq)
    assert not r.gate_closed
    assert not r.ordered_states_ok


def test_release_with_residual_latch_engagement_fails():
    seq = valid_sequence()
    seq[2] = S(4.0, ReleaseState.RELEASED, True, 0.25)
    r = evaluate_mechanical_state_sequence(seq)
    assert not r.released_disengagement_ok
    assert not r.gate_closed


def test_never_demonstrating_grip_release_before_reset_fails():
    seq = valid_sequence()
    seq[3] = S(4.0, ReleaseState.RELEASED, True, 0.05)
    seq[4] = S(4.0, ReleaseState.RESET_REQUIRED, True, 0.05)
    r = evaluate_mechanical_state_sequence(seq)
    assert not r.no_self_reset_ok


def test_inadequate_reset_engagement_fails():
    seq = valid_sequence()
    seq[-1] = S(0.0, ReleaseState.LATCHED, False, 0.3)
    r = evaluate_mechanical_state_sequence(seq)
    assert not r.deliberate_reset_ok


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -1.0])
def test_invalid_travel_fails_closed(bad):
    seq = valid_sequence()
    seq[1] = S(bad, ReleaseState.RELEASING, True, 0.5)
    with pytest.raises(ValueError):
        evaluate_mechanical_state_sequence(seq)


def test_boolean_numeric_confusion_rejected():
    seq = valid_sequence()
    seq[1] = S(True, ReleaseState.RELEASING, True, 0.5)
    with pytest.raises(ValueError):
        evaluate_mechanical_state_sequence(seq)
