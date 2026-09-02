import math
import pytest

from masck_one.retention_migration_margin import evaluate_migration_margin


def test_nominal_margin_closes():
    result = evaluate_migration_margin(
        normal_reaction_n=10.0,
        tangential_demand_n=2.0,
        friction_coefficient_lower_bound=0.4,
        minimum_margin_n=1.0,
    )
    assert result.available_friction_n == pytest.approx(4.0)
    assert result.friction_margin_n == pytest.approx(2.0)
    assert result.utilization == pytest.approx(0.5)
    assert result.migration_resistance_ok


def test_uncertainties_compound_against_margin():
    nominal = evaluate_migration_margin(
        normal_reaction_n=10.0, tangential_demand_n=2.0,
        friction_coefficient_lower_bound=0.4,
    )
    bounded = evaluate_migration_margin(
        normal_reaction_n=10.0, tangential_demand_n=2.0,
        friction_coefficient_lower_bound=0.4,
        normal_reaction_uncertainty_fraction=0.2,
        tangential_demand_uncertainty_fraction=0.25,
    )
    assert bounded.available_friction_n < nominal.available_friction_n
    assert bounded.required_tangential_n > nominal.required_tangential_n
    assert bounded.friction_margin_n < nominal.friction_margin_n


def test_wet_lower_bound_can_flip_pass_to_fail():
    dry = evaluate_migration_margin(
        normal_reaction_n=8.0, tangential_demand_n=2.0,
        friction_coefficient_lower_bound=0.5,
        minimum_margin_n=0.5,
    )
    wet = evaluate_migration_margin(
        normal_reaction_n=8.0, tangential_demand_n=2.0,
        friction_coefficient_lower_bound=0.25,
        minimum_margin_n=0.5,
    )
    assert dry.migration_resistance_ok
    assert not wet.migration_resistance_ok


def test_zero_capacity_nonzero_demand_fails_closed():
    result = evaluate_migration_margin(
        normal_reaction_n=10.0, tangential_demand_n=1.0,
        friction_coefficient_lower_bound=0.0,
    )
    assert math.isinf(result.utilization)
    assert not result.migration_resistance_ok


def test_zero_capacity_zero_demand_is_defined():
    result = evaluate_migration_margin(
        normal_reaction_n=0.0, tangential_demand_n=0.0,
        friction_coefficient_lower_bound=0.0,
    )
    assert result.utilization == 0.0
    assert result.migration_resistance_ok


@pytest.mark.parametrize("kwargs", [
    {"normal_reaction_n": -1.0},
    {"tangential_demand_n": -1.0},
    {"friction_coefficient_lower_bound": -0.1},
    {"normal_reaction_uncertainty_fraction": 1.0},
    {"normal_reaction_uncertainty_fraction": -0.1},
    {"tangential_demand_uncertainty_fraction": -0.1},
    {"minimum_margin_n": -0.1},
    {"normal_reaction_n": float("nan")},
])
def test_invalid_inputs_fail_closed(kwargs):
    base = dict(
        normal_reaction_n=10.0,
        tangential_demand_n=2.0,
        friction_coefficient_lower_bound=0.4,
    )
    base.update(kwargs)
    with pytest.raises(ValueError):
        evaluate_migration_margin(**base)
