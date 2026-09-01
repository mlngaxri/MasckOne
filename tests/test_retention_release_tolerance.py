import math
import pytest

from masck_one.retention_release import release_capsule_clearance, release_capsule_tolerance_clearance

PATH = ((0.0, 0.0, 0.0), (10.0, 0.0, 0.0))
PROTECTED = (((5.0, 8.0, 0.0), 2.0),)


def test_nominal_pass_can_fail_worst_case_tolerance_stack():
    assert release_capsule_clearance(PATH, PROTECTED, moving_radius_mm=2.0,
        minimum_surface_clearance_mm=3.5) == pytest.approx(4.0)
    with pytest.raises(ValueError, match="finite release sweep"):
        release_capsule_tolerance_clearance(PATH, PROTECTED, moving_radius_mm=2.0,
            moving_radius_plus_tol_mm=0.2, protected_radius_plus_tol_mm=0.2,
            trajectory_position_tol_mm=0.1, protected_position_tol_mm=0.1,
            minimum_surface_clearance_mm=3.5)


def test_worst_case_clearance_subtracts_all_bounded_uncertainties():
    d = release_capsule_tolerance_clearance(PATH, PROTECTED, moving_radius_mm=2.0,
        moving_radius_plus_tol_mm=0.2, protected_radius_plus_tol_mm=0.3,
        trajectory_position_tol_mm=0.4, protected_position_tol_mm=0.5,
        minimum_surface_clearance_mm=2.5)
    assert d == pytest.approx(2.6)


def test_zero_tolerances_reduce_exactly_to_nominal_capsule_model():
    nominal = release_capsule_clearance(PATH, PROTECTED, moving_radius_mm=2.0,
        minimum_surface_clearance_mm=3.0)
    worst = release_capsule_tolerance_clearance(PATH, PROTECTED, moving_radius_mm=2.0,
        moving_radius_plus_tol_mm=0.0, protected_radius_plus_tol_mm=0.0,
        trajectory_position_tol_mm=0.0, protected_position_tol_mm=0.0,
        minimum_surface_clearance_mm=3.0)
    assert worst == pytest.approx(nominal)


def test_each_uncertainty_term_monotonically_consumes_clearance():
    base = dict(moving_radius_mm=1.0, moving_radius_plus_tol_mm=0.0,
        protected_radius_plus_tol_mm=0.0, trajectory_position_tol_mm=0.0,
        protected_position_tol_mm=0.0, minimum_surface_clearance_mm=0.0)
    d0 = release_capsule_tolerance_clearance(PATH, PROTECTED, **base)
    for key in ("moving_radius_plus_tol_mm", "protected_radius_plus_tol_mm",
                "trajectory_position_tol_mm", "protected_position_tol_mm"):
        args = dict(base); args[key] = 0.25
        assert release_capsule_tolerance_clearance(PATH, PROTECTED, **args) == pytest.approx(d0 - 0.25)


@pytest.mark.parametrize("field,value", [
    ("moving_radius_plus_tol_mm", -0.1), ("protected_radius_plus_tol_mm", -0.1),
    ("trajectory_position_tol_mm", -0.1), ("protected_position_tol_mm", -0.1),
    ("trajectory_position_tol_mm", math.inf)])
def test_invalid_tolerance_inputs_fail_closed(field, value):
    args = dict(moving_radius_mm=1.0, moving_radius_plus_tol_mm=0.0,
        protected_radius_plus_tol_mm=0.0, trajectory_position_tol_mm=0.0,
        protected_position_tol_mm=0.0, minimum_surface_clearance_mm=0.0)
    args[field] = value
    with pytest.raises(ValueError):
        release_capsule_tolerance_clearance(PATH, PROTECTED, **args)
