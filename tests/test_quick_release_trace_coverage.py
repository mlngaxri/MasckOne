import pytest

from tools.mechanisms.quick_release_trace_coverage import (
    ReleaseTraceRecord,
    evaluate_release_trace_coverage,
)


def rec(specimen, cycle, condition="wet", closed=True):
    return ReleaseTraceRecord(specimen, cycle, condition, closed, "cal-1", 8.0, 40.0)


def test_closes_only_with_specimen_and_repeat_cycle_coverage():
    rows = [rec(s, c) for s in ("A", "B", "C") for c in (1, 2, 3)]
    result = evaluate_release_trace_coverage(rows)
    assert result.coverage_closed
    assert result.minimum_cycles_per_specimen_condition == 3


def test_one_good_specimen_cannot_substitute_for_specimen_coverage():
    rows = [rec("A", c) for c in range(1, 10)]
    assert not evaluate_release_trace_coverage(rows).coverage_closed


def test_one_failing_trace_blocks_coverage():
    rows = [rec(s, c) for s in ("A", "B", "C") for c in (1, 2, 3)]
    rows[-1] = rec("C", 3, closed=False)
    assert not evaluate_release_trace_coverage(rows).coverage_closed


def test_each_specimen_must_cover_each_required_condition():
    rows = [rec(s, c, "wet") for s in ("A", "B", "C") for c in (1, 2, 3)]
    result = evaluate_release_trace_coverage(
        rows, required_conditions=("wet", "wet_hair_surrogate")
    )
    assert not result.coverage_closed
    assert result.minimum_cycles_per_specimen_condition == 0


def test_duplicate_identity_fails_closed():
    with pytest.raises(ValueError):
        evaluate_release_trace_coverage([rec("A", 1), rec("A", 1)])


def test_nonfinite_measurement_rejected():
    with pytest.raises(ValueError):
        evaluate_release_trace_coverage([
            ReleaseTraceRecord("A", 1, "wet", True, "cal-1", float("nan"), 1.0)
        ])
