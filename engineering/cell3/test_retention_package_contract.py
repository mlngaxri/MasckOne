import math
import pytest

from retention_package_contract import AABB, RetentionDatums, evaluate_retention_package


def geometry(right_yoke=(45.0, 0.0, 0.0), right_junction=(55.0, 30.0, 10.0)):
    return RetentionDatums(
        left_yoke=(-45.0, 0.0, 0.0), right_yoke=right_yoke,
        left_junction=(-55.0, 30.0, 10.0), right_junction=right_junction,
        crown_apex=(0.0, 35.0, 75.0), occipital_center=(0.0, 65.0, 5.0),
    )


def run(g=None, keepouts=None, symmetry=1.0):
    return evaluate_retention_package(
        g or geometry(), keepouts or {}, minimum_member_length_mm=5.0,
        minimum_keepout_clearance_mm=2.0, bilateral_symmetry_tolerance_mm=symmetry,
        sweep_samples_per_member=80,
    )


def test_symmetric_complete_load_path_passes_without_keepouts():
    result = run()
    assert result.passed
    assert result.symmetry_error_mm == pytest.approx(0.0)
    assert math.isinf(result.minimum_keepout_clearance_mm)


def test_asymmetric_side_link_fails():
    result = run(geometry(right_junction=(62.0, 38.0, 10.0)), symmetry=0.5)
    assert not result.passed
    assert "bilateral_side_link_asymmetry" in result.failures


def test_member_crossing_protected_keepout_fails():
    box = AABB(lo=(-8.0, 30.0, 55.0), hi=(8.0, 40.0, 68.0))
    result = run(keepouts={"hair_release_corridor": box})
    assert not result.passed
    assert any("hair_release_corridor" in f for f in result.failures)
    assert result.minimum_keepout_clearance_mm < 0.0


def test_near_miss_below_clearance_fails_even_without_penetration():
    box = AABB(lo=(-2.0, 35.0, 76.0), hi=(2.0, 39.0, 80.0))
    result = run(keepouts={"exterior_service_keepout": box})
    assert not result.passed
    assert 0.0 <= result.minimum_keepout_clearance_mm < 2.0


def test_degenerate_load_path_fails():
    g = geometry(right_junction=(45.0, 0.0, 0.0))
    result = run(g, symmetry=100.0)
    assert not result.passed
    assert "right_yoke_link:degenerate_load_path" in result.failures


@pytest.mark.parametrize("bad", [float("nan"), float("inf")])
def test_nonfinite_datum_rejected(bad):
    g = geometry(right_yoke=(bad, 0.0, 0.0))
    with pytest.raises(ValueError):
        run(g)


def test_boolean_limit_rejected():
    with pytest.raises(ValueError):
        evaluate_retention_package(geometry(), {}, minimum_member_length_mm=True,
                                   minimum_keepout_clearance_mm=2.0,
                                   bilateral_symmetry_tolerance_mm=1.0)


def test_invalid_keepout_rejected():
    with pytest.raises(ValueError):
        run(keepouts={"bad": AABB(lo=(1.0, 0.0, 0.0), hi=(0.0, 1.0, 1.0))})
