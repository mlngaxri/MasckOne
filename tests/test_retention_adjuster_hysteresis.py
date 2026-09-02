import math

import pytest

from masck_one.retention_adjuster_hysteresis import evaluate_adjuster_hysteresis


def _base(**overrides):
    values = dict(
        measured_lost_motion_mm=0.20,
        lost_motion_uncertainty_mm=0.05,
        maximum_allowed_lost_motion_mm=0.30,
        member_stiffness_n_per_mm=4.0,
        maximum_allowed_reversal_tension_deadband_n=1.2,
        reachable_discrete_span_mm=22.0,
        required_adjustment_span_mm=21.5,
    )
    values.update(overrides)
    return evaluate_adjuster_hysteresis(**values)


def test_nominal_hysteresis_closes():
    result = _base()
    assert result.hysteresis_ok
    assert result.conservative_lost_motion_mm == pytest.approx(0.25)
    assert result.reversal_tension_deadband_n == pytest.approx(1.0)
    assert result.conservative_reachable_span_mm == pytest.approx(21.75)


def test_uncertainty_can_consume_endpoint_fit_margin():
    result = _base(
        measured_lost_motion_mm=0.20,
        lost_motion_uncertainty_mm=0.35,
        maximum_allowed_lost_motion_mm=1.0,
        maximum_allowed_reversal_tension_deadband_n=3.0,
    )
    assert not result.span_ok
    assert not result.hysteresis_ok


def test_stiffness_can_make_small_lost_motion_unacceptable():
    result = _base(member_stiffness_n_per_mm=6.0)
    assert result.lost_motion_ok
    assert not result.tension_deadband_ok
    assert not result.hysteresis_ok


def test_uncertainty_is_adversarial_not_credit():
    low = _base(lost_motion_uncertainty_mm=0.0)
    high = _base(lost_motion_uncertainty_mm=0.10)
    assert high.conservative_lost_motion_mm > low.conservative_lost_motion_mm
    assert high.reversal_tension_deadband_n > low.reversal_tension_deadband_n
    assert high.conservative_reachable_span_mm < low.conservative_reachable_span_mm


@pytest.mark.parametrize(
    "field,value",
    [
        ("measured_lost_motion_mm", -0.1),
        ("lost_motion_uncertainty_mm", -0.1),
        ("member_stiffness_n_per_mm", 0.0),
        ("reachable_discrete_span_mm", -1.0),
        ("measured_lost_motion_mm", math.inf),
        ("measured_lost_motion_mm", True),
    ],
)
def test_invalid_inputs_fail_closed(field, value):
    kwargs = dict(
        measured_lost_motion_mm=0.20,
        lost_motion_uncertainty_mm=0.05,
        maximum_allowed_lost_motion_mm=0.30,
        member_stiffness_n_per_mm=4.0,
        maximum_allowed_reversal_tension_deadband_n=1.2,
        reachable_discrete_span_mm=22.0,
        required_adjustment_span_mm=21.5,
    )
    kwargs[field] = value
    with pytest.raises(ValueError):
        evaluate_adjuster_hysteresis(**kwargs)
