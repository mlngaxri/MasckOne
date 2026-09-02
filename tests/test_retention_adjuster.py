import math
import pytest

from masck_one.retention_adjuster import evaluate_retention_adjuster


def base(**overrides):
    args = dict(
        required_adjustment_span_mm=20.0,
        nominal_travel_mm=24.0,
        end_stop_uncertainty_mm=1.0,
        position_increment_mm=1.0,
        member_stiffness_n_per_mm=2.0,
        maximum_allowed_tension_error_n=1.0,
        minimum_backdrive_load_n=20.0,
        maximum_service_tension_n=15.0,
        backdrive_load_uncertainty_n=1.0,
        service_tension_uncertainty_n=1.0,
    )
    args.update(overrides)
    return evaluate_retention_adjuster(**args)


def test_nominal_adjuster_closes():
    r = base()
    assert r.usable_travel_mm == 22.0
    assert r.reachable_discrete_travel_mm == 22.0
    assert r.required_positions == 21
    assert r.available_positions == 23
    assert r.maximum_quantization_error_mm == 0.5
    assert r.maximum_quantization_tension_error_n == 1.0
    assert r.retention_margin_n == 3.0
    assert r.discrete_range_ok
    assert r.adjuster_ok


def test_end_stop_uncertainty_can_consume_travel():
    r = base(end_stop_uncertainty_mm=2.5)
    assert r.usable_travel_mm == 19.0
    assert r.travel_margin_mm == -1.0
    assert not r.adjuster_ok


def test_continuous_travel_can_pass_while_discrete_positions_cannot_reach_span():
    r = base(
        required_adjustment_span_mm=20.5,
        nominal_travel_mm=23.5,
        end_stop_uncertainty_mm=1.0,
        position_increment_mm=1.0,
        member_stiffness_n_per_mm=1.0,
    )
    assert r.usable_travel_mm == 21.5
    assert r.travel_margin_mm == 1.0
    assert r.reachable_discrete_travel_mm == 21.0
    assert r.discrete_travel_margin_mm == 0.5
    assert r.required_positions == 22
    assert r.available_positions == 22
    assert r.discrete_range_ok

    failing = base(
        required_adjustment_span_mm=21.25,
        nominal_travel_mm=23.5,
        end_stop_uncertainty_mm=1.0,
        position_increment_mm=1.0,
        member_stiffness_n_per_mm=1.0,
    )
    assert failing.usable_travel_mm == 21.5
    assert failing.travel_margin_mm == 0.25
    assert failing.reachable_discrete_travel_mm == 21.0
    assert failing.discrete_travel_margin_mm == pytest.approx(-0.25)
    assert not failing.discrete_range_ok
    assert not failing.adjuster_ok


def test_required_position_count_uses_ceiling_not_floor():
    r = base(required_adjustment_span_mm=20.01, position_increment_mm=1.0, member_stiffness_n_per_mm=1.0)
    assert r.required_positions == 22


def test_coarse_increment_can_fail_tension_resolution():
    r = base(position_increment_mm=1.2)
    assert r.maximum_quantization_tension_error_n == pytest.approx(1.2)
    assert not r.resolution_ok
    assert not r.adjuster_ok


def test_uncertainties_compound_backdrive_margin():
    nominal = base(backdrive_load_uncertainty_n=0.0, service_tension_uncertainty_n=0.0)
    adverse = base(backdrive_load_uncertainty_n=2.0, service_tension_uncertainty_n=2.0)
    assert adverse.retention_margin_n < nominal.retention_margin_n


def test_backdrive_capacity_below_service_demand_fails():
    r = base(minimum_backdrive_load_n=16.0, backdrive_load_uncertainty_n=1.0, service_tension_uncertainty_n=1.0)
    assert r.retention_margin_n == -1.0
    assert not r.retention_ok
    assert not r.adjuster_ok


def test_zero_required_span_needs_one_position():
    r = base(required_adjustment_span_mm=0.0)
    assert r.required_positions == 1


@pytest.mark.parametrize("field", [
    "required_adjustment_span_mm", "nominal_travel_mm", "end_stop_uncertainty_mm",
    "position_increment_mm", "member_stiffness_n_per_mm", "maximum_allowed_tension_error_n",
    "minimum_backdrive_load_n", "maximum_service_tension_n", "backdrive_load_uncertainty_n",
    "service_tension_uncertainty_n",
])
def test_nonfinite_inputs_fail_closed(field):
    with pytest.raises(ValueError):
        base(**{field: math.nan})


def test_boolean_is_not_accepted_as_numeric():
    with pytest.raises(ValueError):
        base(position_increment_mm=True)
