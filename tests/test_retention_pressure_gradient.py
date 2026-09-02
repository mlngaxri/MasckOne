import math
import pytest

from masck_one.retention_pressure_gradient import PressureGradientInputs, evaluate_pressure_gradient


def test_zero_moment_is_uniform():
    r = evaluate_pressure_gradient(PressureGradientInputs(10.0, 0.0, 40.0, 50.0))
    assert r.average_pressure_kpa == pytest.approx(5.0)
    assert r.edge_pressure_low_kpa == pytest.approx(5.0)
    assert r.edge_pressure_high_kpa == pytest.approx(5.0)
    assert r.full_contact_possible


def test_kern_boundary_reaches_zero_pressure_at_one_edge():
    force = 12.0
    width = 36.0
    moment = force * width / 6.0
    r = evaluate_pressure_gradient(PressureGradientInputs(force, moment, width, 40.0))
    assert r.edge_pressure_low_kpa == pytest.approx(0.0)
    assert r.full_contact_possible


def test_outside_kern_flags_loss_of_full_contact():
    r = evaluate_pressure_gradient(PressureGradientInputs(10.0, 80.0, 30.0, 40.0))
    assert abs(r.eccentricity_mm) > r.kern_half_width_mm
    assert not r.full_contact_possible
    assert r.edge_pressure_low_kpa < 0.0


def test_moment_sign_only_swaps_edges_not_extrema():
    a = evaluate_pressure_gradient(PressureGradientInputs(10.0, 30.0, 40.0, 50.0))
    b = evaluate_pressure_gradient(PressureGradientInputs(10.0, -30.0, 40.0, 50.0))
    assert a.edge_pressure_low_kpa == pytest.approx(b.edge_pressure_low_kpa)
    assert a.edge_pressure_high_kpa == pytest.approx(b.edge_pressure_high_kpa)


def test_zero_force_with_moment_fails_contact_closure():
    r = evaluate_pressure_gradient(PressureGradientInputs(0.0, 1.0, 40.0, 50.0))
    assert math.isinf(r.eccentricity_mm)
    assert not r.full_contact_possible


@pytest.mark.parametrize("field,value", [
    ("normal_force_n", -1.0),
    ("contact_width_mm", 0.0),
    ("contact_length_mm", -1.0),
    ("overturning_moment_nmm", float("nan")),
])
def test_invalid_inputs_fail_closed(field, value):
    kwargs = dict(normal_force_n=10.0, overturning_moment_nmm=0.0, contact_width_mm=40.0, contact_length_mm=50.0)
    kwargs[field] = value
    with pytest.raises(ValueError):
        evaluate_pressure_gradient(PressureGradientInputs(**kwargs))
