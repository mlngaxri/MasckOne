import math
import pytest

from retention_adjuster_wear import evaluate_adjuster_wear


def base(**overrides):
    args = dict(
        initial_reachable_travel_mm=24.0,
        required_travel_mm=21.0,
        initial_increment_mm=1.0,
        increment_growth_mm=0.1,
        endpoint_position_loss_mm=1.0,
        retention_stiffness_n_per_mm=4.0,
        max_tension_error_n=2.5,
        initial_backdrive_capacity_n=30.0,
        backdrive_capacity_loss_n=2.0,
        max_service_tension_n=20.0,
        service_tension_uncertainty_n=2.0,
        required_backdrive_margin_n=3.0,
    )
    args.update(overrides)
    return evaluate_adjuster_wear(**args)


def test_nominal_worn_state_closes():
    result = base()
    assert result.travel_margin_mm == pytest.approx(2.0)
    assert result.max_tension_quantization_error_n == pytest.approx(2.2)
    assert result.worn_backdrive_capacity_n == pytest.approx(28.0)
    assert result.screening_closed
    assert result.evidence_status == "DIGITAL_SENSITIVITY_ONLY"


def test_endpoint_wear_can_break_fit_range():
    result = base(endpoint_position_loss_mm=3.5)
    assert not result.travel_ok
    assert not result.screening_closed


def test_increment_wear_can_break_tension_resolution():
    result = base(increment_growth_mm=0.4)
    assert not result.resolution_ok
    assert not result.screening_closed


def test_backdrive_wear_and_service_uncertainty_compound():
    result = base(backdrive_capacity_loss_n=6.0, service_tension_uncertainty_n=3.0)
    assert not result.backdrive_ok
    assert not result.screening_closed


def test_zero_capacity_never_hides_required_load():
    result = base(initial_backdrive_capacity_n=0.0, backdrive_capacity_loss_n=0.0)
    assert result.worn_backdrive_capacity_n == 0.0
    assert not result.backdrive_ok


@pytest.mark.parametrize("field", [
    "initial_reachable_travel_mm", "required_travel_mm", "initial_increment_mm",
    "increment_growth_mm", "endpoint_position_loss_mm", "retention_stiffness_n_per_mm",
    "max_tension_error_n", "initial_backdrive_capacity_n", "backdrive_capacity_loss_n",
    "max_service_tension_n", "service_tension_uncertainty_n", "required_backdrive_margin_n",
])
def test_nonfinite_inputs_fail_closed(field):
    with pytest.raises(ValueError):
        base(**{field: math.nan})


def test_bool_is_not_accepted_as_numeric():
    with pytest.raises(ValueError):
        base(endpoint_position_loss_mm=True)


def test_negative_wear_is_not_credit():
    with pytest.raises(ValueError):
        base(backdrive_capacity_loss_n=-1.0)
