import math
import pytest

from masck_one.retention_preload_window import evaluate_preload_window


def test_full_adjustment_range_decouples_size_from_tension():
    result = evaluate_preload_window(
        nominal_path_length_mm=420, path_length_variation_mm=40,
        adjustment_travel_each_side_mm=22, member_stiffness_n_per_mm=0.5,
        nominal_tension_n=8, minimum_tension_n=5, maximum_tension_n=12,
        assembly_length_uncertainty_mm=2, stiffness_uncertainty_fraction=0.2,
    )
    assert result.preload_window_ok
    assert result.worst_short_tension_n == pytest.approx(8)
    assert result.worst_long_tension_n == pytest.approx(8)
    assert result.adjustment_margin_mm == pytest.approx(0)


def test_insufficient_travel_exposes_tension_excursion():
    result = evaluate_preload_window(
        nominal_path_length_mm=420, path_length_variation_mm=40,
        adjustment_travel_each_side_mm=15, member_stiffness_n_per_mm=0.5,
        nominal_tension_n=8, minimum_tension_n=5, maximum_tension_n=12,
        assembly_length_uncertainty_mm=2, stiffness_uncertainty_fraction=0.2,
    )
    assert not result.preload_window_ok
    assert result.adjustment_margin_mm == pytest.approx(-14)
    assert result.worst_short_tension_n == pytest.approx(3.8)
    assert result.worst_long_tension_n == pytest.approx(12.2)


def test_assembly_uncertainty_consumes_adjustment_range():
    base = evaluate_preload_window(
        nominal_path_length_mm=400, path_length_variation_mm=20,
        adjustment_travel_each_side_mm=12, member_stiffness_n_per_mm=0.4,
        nominal_tension_n=7, minimum_tension_n=4, maximum_tension_n=10,
    )
    uncertain = evaluate_preload_window(
        nominal_path_length_mm=400, path_length_variation_mm=20,
        adjustment_travel_each_side_mm=12, member_stiffness_n_per_mm=0.4,
        nominal_tension_n=7, minimum_tension_n=4, maximum_tension_n=10,
        assembly_length_uncertainty_mm=3,
    )
    assert uncertain.adjustment_margin_mm < base.adjustment_margin_mm
    assert not uncertain.preload_window_ok


def test_stiffness_uncertainty_worsens_both_tension_extremes_when_travel_saturates():
    base = evaluate_preload_window(
        nominal_path_length_mm=400, path_length_variation_mm=30,
        adjustment_travel_each_side_mm=10, member_stiffness_n_per_mm=0.5,
        nominal_tension_n=8, minimum_tension_n=0, maximum_tension_n=20,
    )
    uncertain = evaluate_preload_window(
        nominal_path_length_mm=400, path_length_variation_mm=30,
        adjustment_travel_each_side_mm=10, member_stiffness_n_per_mm=0.5,
        nominal_tension_n=8, minimum_tension_n=0, maximum_tension_n=20,
        stiffness_uncertainty_fraction=0.25,
    )
    assert uncertain.worst_short_tension_n < base.worst_short_tension_n
    assert uncertain.worst_long_tension_n > base.worst_long_tension_n


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_nonfinite_inputs_fail_closed(value):
    with pytest.raises(ValueError):
        evaluate_preload_window(
            nominal_path_length_mm=400, path_length_variation_mm=value,
            adjustment_travel_each_side_mm=10, member_stiffness_n_per_mm=0.5,
            nominal_tension_n=8, minimum_tension_n=4, maximum_tension_n=12,
        )


def test_invalid_geometry_and_uncertainty_fail_closed():
    with pytest.raises(ValueError):
        evaluate_preload_window(
            nominal_path_length_mm=0, path_length_variation_mm=20,
            adjustment_travel_each_side_mm=10, member_stiffness_n_per_mm=0.5,
            nominal_tension_n=8, minimum_tension_n=4, maximum_tension_n=12,
        )
    with pytest.raises(ValueError):
        evaluate_preload_window(
            nominal_path_length_mm=400, path_length_variation_mm=20,
            adjustment_travel_each_side_mm=10, member_stiffness_n_per_mm=0.5,
            nominal_tension_n=8, minimum_tension_n=4, maximum_tension_n=12,
            stiffness_uncertainty_fraction=1.0,
        )
