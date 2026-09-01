import math
import pytest

from masck_one.quick_release_validation import QuickReleaseEvidence, evaluate_quick_release_evidence


def evidence(**overrides):
    base = dict(
        wet_one_hand_peak_force_n=8.0,
        wet_one_hand_release_time_s=1.2,
        accidental_pull_force_n=4.0,
        reset_retention_force_n=11.0,
        release_trials=10,
        pinch_failures=0,
        hair_entanglement_failures=0,
        unpowered_trials=10,
        one_hand_trials=10,
    )
    base.update(overrides)
    return QuickReleaseEvidence(**base)


def test_complete_physical_evidence_closes_gate():
    r = evaluate_quick_release_evidence(evidence())
    assert r.validation_closed
    assert r.evidence_status == "PHYSICAL_VALIDATION_CLOSED"
    assert r.accidental_pull_margin_n == pytest.approx(4.0)
    assert r.reset_margin_n == pytest.approx(3.0)


@pytest.mark.parametrize("kwargs,field", [
    ({"wet_one_hand_peak_force_n": 4.9}, "force_corridor_ok"),
    ({"wet_one_hand_peak_force_n": 12.1, "reset_retention_force_n": 15.0}, "force_corridor_ok"),
    ({"wet_one_hand_release_time_s": 2.01}, "release_time_ok"),
    ({"accidental_pull_force_n": 6.1}, "accidental_pull_margin_ok"),
    ({"reset_retention_force_n": 9.9}, "reset_margin_ok"),
    ({"pinch_failures": 1}, "pinch_ok"),
    ({"hair_entanglement_failures": 1}, "hair_ok"),
    ({"unpowered_trials": 9}, "all_trials_unpowered"),
    ({"one_hand_trials": 9}, "all_trials_one_hand"),
])
def test_any_single_safety_failure_prevents_validation_closure(kwargs, field):
    r = evaluate_quick_release_evidence(evidence(**kwargs))
    assert getattr(r, field) is False
    assert r.validation_closed is False
    assert r.evidence_status == "PHYSICAL_TEST_REQUIRED"


def test_boundary_values_are_inclusive():
    r = evaluate_quick_release_evidence(evidence(
        wet_one_hand_peak_force_n=5.0,
        wet_one_hand_release_time_s=2.0,
        accidental_pull_force_n=3.0,
        reset_retention_force_n=7.0,
    ))
    assert r.validation_closed


@pytest.mark.parametrize("kwargs", [
    {"release_trials": 0},
    {"release_trials": 3, "pinch_failures": 4, "unpowered_trials": 3, "one_hand_trials": 3},
    {"release_trials": 3, "hair_entanglement_failures": 4, "unpowered_trials": 3, "one_hand_trials": 3},
    {"release_trials": 3, "unpowered_trials": 4, "one_hand_trials": 3},
    {"release_trials": 3, "unpowered_trials": 3, "one_hand_trials": 4},
    {"wet_one_hand_peak_force_n": math.inf},
    {"wet_one_hand_release_time_s": -0.1},
])
def test_malformed_or_impossible_evidence_fails_closed(kwargs):
    with pytest.raises(ValueError):
        evaluate_quick_release_evidence(evidence(**kwargs))


def test_invalid_gate_configuration_fails_closed():
    with pytest.raises(ValueError):
        evaluate_quick_release_evidence(evidence(), min_release_force_n=13.0, max_release_force_n=12.0)
