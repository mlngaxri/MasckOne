import pytest

from engineering.cell3.retention_adjuster_condition_sequence import evaluate_condition_sequences
from engineering.cell3.retention_adjuster_wear_sequence import WearCheckpoint


BASE = dict(
    nominal_usable_travel_mm=24.0,
    required_path_span_mm=20.0,
    nominal_increment_mm=1.0,
    retention_stiffness_n_per_mm=1.0,
    max_tension_error_n=0.75,
    nominal_backdrive_capacity_n=30.0,
    max_service_tension_n=15.0,
    required_backdrive_margin=1.25,
)


def cp(cycle, endpoint=0.0, growth=0.0, degradation=0.0):
    return WearCheckpoint(cycle, endpoint, growth, degradation)


def test_all_required_conditions_must_pass():
    result = evaluate_condition_sequences(
        {"dry": [cp(0), cp(1000, endpoint=0.5)], "wet": [cp(0), cp(1000, endpoint=0.5)]},
        required_conditions=("dry", "wet"), **BASE)
    assert result.passed


def test_missing_condition_blocks_closure():
    result = evaluate_condition_sequences(
        {"dry": [cp(0), cp(1000)]}, required_conditions=("dry", "wet"), **BASE)
    assert not result.passed
    assert result.missing_conditions == ("wet",)


def test_one_bad_condition_cannot_be_hidden_by_dry_pass():
    result = evaluate_condition_sequences(
        {"dry": [cp(0), cp(1000)], "wet": [cp(0), cp(500, endpoint=3.0)]},
        required_conditions=("dry", "wet"), **BASE)
    assert not result.passed
    assert result.failing_conditions == ("wet",)
    assert result.first_failure_cycle_by_condition["wet"] == 500


def test_condition_names_are_normalized_but_duplicates_rejected():
    with pytest.raises(ValueError):
        evaluate_condition_sequences(
            {"Wet": [cp(0)], " wet ": [cp(0)]}, required_conditions=("wet",), **BASE)


def test_required_condition_duplicates_rejected():
    with pytest.raises(ValueError):
        evaluate_condition_sequences(
            {"wet": [cp(0)]}, required_conditions=("wet", "WET"), **BASE)


def test_empty_required_matrix_rejected():
    with pytest.raises(ValueError):
        evaluate_condition_sequences({}, required_conditions=(), **BASE)
