import math
import pytest

from masck_one.quick_release_trials import QuickReleaseTrial, evaluate_quick_release_trials


def trial(**changes):
    data = dict(
        peak_release_force_n=8.0,
        removal_time_s=1.2,
        accidental_pull_force_n=4.0,
        reset_retention_force_n=11.0,
        unpowered=True,
        one_hand=True,
        wet=True,
    )
    data.update(changes)
    return QuickReleaseTrial(**data)


def test_all_trials_must_close_individually():
    result = evaluate_quick_release_trials([trial(), trial()])
    assert result.validation_closed
    assert result.trial_count == 2


def test_one_slow_trial_cannot_be_hidden_by_fast_trial():
    result = evaluate_quick_release_trials([trial(removal_time_s=0.8), trial(removal_time_s=2.1)])
    assert not result.validation_closed
    assert result.time_failures == 1


def test_one_force_outlier_cannot_be_hidden():
    result = evaluate_quick_release_trials([trial(peak_release_force_n=8.0), trial(peak_release_force_n=12.1, reset_retention_force_n=15.0)])
    assert result.force_failures == 1
    assert not result.validation_closed


def test_wet_is_required_per_trial():
    result = evaluate_quick_release_trials([trial(), trial(wet=False)])
    assert result.qualification_failures == 1
    assert not result.validation_closed


def test_unpowered_and_one_hand_are_required_per_trial():
    result = evaluate_quick_release_trials([trial(unpowered=False), trial(one_hand=False)])
    assert result.qualification_failures == 2


def test_hair_or_pinch_failure_blocks_closure():
    result = evaluate_quick_release_trials([trial(pinch_failure=True), trial(hair_entanglement_failure=True)])
    assert result.pinch_failures == 1
    assert result.hair_failures == 1
    assert not result.validation_closed


def test_accidental_and_reset_margins_are_per_trial():
    result = evaluate_quick_release_trials([
        trial(accidental_pull_force_n=6.1),
        trial(reset_retention_force_n=9.9),
    ])
    assert result.accidental_margin_failures == 1
    assert result.reset_margin_failures == 1


def test_empty_evidence_fails_closed():
    with pytest.raises(ValueError):
        evaluate_quick_release_trials([])


def test_nonfinite_measurement_rejected():
    with pytest.raises(ValueError):
        evaluate_quick_release_trials([trial(removal_time_s=math.nan)])


def test_bool_must_not_be_numeric_measurement():
    with pytest.raises(ValueError):
        evaluate_quick_release_trials([trial(peak_release_force_n=True)])
