import math
import pytest

from masck_one.quick_release_force_trace import (
    ForceDisplacementPoint,
    evaluate_release_force_trace,
)


def trace(*rows):
    return tuple(ForceDisplacementPoint(x, f) for x, f in rows)


def test_nominal_trace_closes_peak_travel_drop_and_work_gates():
    result = evaluate_release_force_trace(
        trace((0, 0), (2, 4), (4, 8), (6, 3), (8, 1)),
        required_travel_mm=8,
    )
    assert result.peak_force_n == 8
    assert result.peak_force_travel_mm == 4
    assert result.work_mj == pytest.approx(31.0)
    assert result.validation_closed
    assert result.evidence_status == "PHYSICAL_TRACE_GATE_CLOSED"


def test_force_spike_above_corridor_cannot_hide_behind_low_terminal_force():
    result = evaluate_release_force_trace(
        trace((0, 0), (2, 5), (3, 13), (6, 2), (8, 1)),
        required_travel_mm=8,
    )
    assert result.peak_force_n == 13
    assert not result.force_corridor_ok
    assert not result.validation_closed


def test_incomplete_travel_fails_even_with_acceptable_peak():
    result = evaluate_release_force_trace(
        trace((0, 0), (2, 7), (4, 2)), required_travel_mm=8, travel_tolerance_mm=0.5
    )
    assert not result.travel_complete
    assert not result.validation_closed


def test_peak_at_terminal_point_fails_post_latch_drop_gate():
    result = evaluate_release_force_trace(
        trace((0, 0), (4, 4), (8, 8)), required_travel_mm=8
    )
    assert not result.post_latch_drop_ok
    assert not result.validation_closed


def test_excessive_work_fails_despite_acceptable_peak_force():
    result = evaluate_release_force_trace(
        trace((0, 8), (5, 8), (10, 8), (12, 5)),
        required_travel_mm=12,
        max_work_mj=80,
    )
    assert result.peak_force_n == 8
    assert result.work_mj > 80
    assert not result.work_ok
    assert not result.validation_closed


def test_trapezoidal_work_is_force_newtons_times_travel_mm_equal_millijoules():
    result = evaluate_release_force_trace(
        trace((0, 0), (2, 10), (4, 0)), required_travel_mm=4, min_post_latch_force_drop_n=2
    )
    assert result.work_mj == pytest.approx(20.0)


@pytest.mark.parametrize("rows", [
    ((0, 1), (0, 2)),
    ((1, 1), (0, 2)),
])
def test_non_monotonic_or_duplicate_travel_fails_closed(rows):
    with pytest.raises(ValueError):
        evaluate_release_force_trace(trace(*rows), required_travel_mm=1)


def test_nonfinite_measurement_fails_closed():
    with pytest.raises(ValueError):
        evaluate_release_force_trace(trace((0, 0), (8, math.inf)), required_travel_mm=8)


def test_negative_force_fails_closed():
    with pytest.raises(ValueError):
        evaluate_release_force_trace(trace((0, 0), (8, -1)), required_travel_mm=8)


def test_invalid_gate_bounds_fail_closed():
    with pytest.raises(ValueError):
        evaluate_release_force_trace(trace((0, 0), (8, 6)), required_travel_mm=8, min_peak_force_n=13, max_peak_force_n=12)
