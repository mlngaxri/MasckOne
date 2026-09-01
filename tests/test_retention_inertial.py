import math
import pytest

from masck_one.retention_inertial import (
    InertialRetentionInputs,
    evaluate_inertial_retention,
    inertial_retention_doe,
)


def base(**kw):
    values = dict(
        loaded_mass_g=255.0,
        lateral_accel_g=0.5,
        fore_aft_accel_g=0.5,
        cg_lateral_mm=5.0,
        cg_anterior_mm=25.0,
        bilateral_support_span_mm=120.0,
        vertical_support_span_mm=80.0,
    )
    values.update(kw)
    return InertialRetentionInputs(**values)


def test_translation_uses_prescribed_acceleration_and_mass():
    r = evaluate_inertial_retention(base(lateral_accel_g=1.0, fore_aft_accel_g=0.0))
    assert r.lateral_force_n == pytest.approx(0.255 * 9.80665)
    assert r.translational_resultant_n == pytest.approx(abs(r.lateral_force_n))


def test_nonzero_yaw_moment_requires_bilateral_span():
    r = evaluate_inertial_retention(base(bilateral_support_span_mm=0.0, fore_aft_accel_g=0.0))
    assert not r.yaw_load_path_closed
    assert r.yaw_couple_force_n is None


def test_nonzero_pitch_moment_requires_vertical_span():
    r = evaluate_inertial_retention(base(vertical_support_span_mm=0.0, lateral_accel_g=0.0))
    assert not r.pitch_load_path_closed
    assert r.pitch_couple_force_n is None


def test_support_span_reduces_required_couple_force():
    small = evaluate_inertial_retention(base(bilateral_support_span_mm=60.0))
    large = evaluate_inertial_retention(base(bilateral_support_span_mm=120.0))
    assert small.yaw_couple_force_n == pytest.approx(2.0 * large.yaw_couple_force_n)


def test_zero_acceleration_closes_without_artificial_couple():
    r = evaluate_inertial_retention(base(lateral_accel_g=0.0, fore_aft_accel_g=0.0,
                                         bilateral_support_span_mm=0.0, vertical_support_span_mm=0.0))
    assert r.yaw_load_path_closed and r.pitch_load_path_closed
    assert r.yaw_couple_force_n == 0.0 and r.pitch_couple_force_n == 0.0


def test_signed_acceleration_preserves_moment_direction():
    pos = evaluate_inertial_retention(base(lateral_accel_g=0.5, fore_aft_accel_g=0.0))
    neg = evaluate_inertial_retention(base(lateral_accel_g=-0.5, fore_aft_accel_g=0.0))
    assert pos.yaw_moment_nm == pytest.approx(-neg.yaw_moment_nm)
    assert pos.yaw_couple_force_n == pytest.approx(neg.yaw_couple_force_n)


def test_doe_is_cartesian_and_deterministic():
    r = inertial_retention_doe(base(), lateral_accel_g=(-0.5, 0.0, 0.5), fore_aft_accel_g=(-0.25, 0.25))
    assert len(r) == 6
    assert r == inertial_retention_doe(base(), lateral_accel_g=(-0.5, 0.0, 0.5), fore_aft_accel_g=(-0.25, 0.25))


@pytest.mark.parametrize("field,value", [
    ("loaded_mass_g", 0.0),
    ("bilateral_support_span_mm", -1.0),
    ("vertical_support_span_mm", -1.0),
    ("lateral_accel_g", math.inf),
    ("fore_aft_accel_g", math.nan),
])
def test_invalid_inputs_fail_closed(field, value):
    with pytest.raises(ValueError):
        evaluate_inertial_retention(base(**{field: value}))
