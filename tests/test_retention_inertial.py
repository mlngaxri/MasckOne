import math
import pytest

from masck_one.retention_inertial import InertialRetentionInputs, evaluate_inertial_retention, inertial_retention_doe


def base(**kw):
    values = dict(loaded_mass_g=255.0, lateral_accel_g=0.5, fore_aft_accel_g=0.5,
                  cg_lateral_mm=5.0, cg_anterior_mm=25.0, cg_vertical_mm=20.0,
                  bilateral_support_span_mm=120.0, vertical_support_span_mm=80.0)
    values.update(kw)
    return InertialRetentionInputs(**values)


def test_translation_uses_prescribed_acceleration_and_mass():
    r = evaluate_inertial_retention(base(lateral_accel_g=1.0, fore_aft_accel_g=0.0))
    assert r.lateral_force_n == pytest.approx(0.255 * 9.80665)
    assert r.translational_resultant_n == pytest.approx(abs(r.lateral_force_n))


def test_yaw_is_cross_product_not_scalar_offset_sum():
    r = evaluate_inertial_retention(base(lateral_accel_g=0.5, fore_aft_accel_g=0.5))
    expected = (0.005 * r.fore_aft_force_n) - (0.025 * r.lateral_force_n)
    assert r.yaw_moment_nm == pytest.approx(expected)


def test_fore_aft_force_parallel_to_anterior_offset_creates_no_pitch():
    r = evaluate_inertial_retention(base(lateral_accel_g=0.0, cg_vertical_mm=0.0,
                                         cg_lateral_mm=0.0, cg_anterior_mm=40.0))
    assert r.pitch_moment_nm == 0.0


def test_vertical_cg_offset_creates_pitch_from_fore_aft_force():
    r = evaluate_inertial_retention(base(lateral_accel_g=0.0, cg_vertical_mm=20.0))
    assert r.pitch_moment_nm == pytest.approx(-0.020 * r.fore_aft_force_n)


def test_vertical_cg_offset_creates_roll_from_lateral_force():
    r = evaluate_inertial_retention(base(lateral_accel_g=0.5, fore_aft_accel_g=0.0,
                                         cg_vertical_mm=20.0))
    assert r.roll_moment_nm == pytest.approx(0.020 * r.lateral_force_n)


def test_zero_vertical_offset_eliminates_pitch_and_roll_not_yaw():
    r = evaluate_inertial_retention(base(cg_vertical_mm=0.0, lateral_accel_g=0.5,
                                         fore_aft_accel_g=0.0))
    assert r.pitch_moment_nm == 0.0 and r.roll_moment_nm == 0.0
    assert r.yaw_moment_nm != 0.0


def test_rotational_inertia_creates_moment_without_translation():
    r = evaluate_inertial_retention(base(lateral_accel_g=0.0, fore_aft_accel_g=0.0,
        pitch_inertia_kg_m2=0.002, pitch_angular_accel_rad_s2=3.0))
    assert r.translational_resultant_n == 0.0
    assert r.translational_pitch_moment_nm == 0.0
    assert r.rotational_pitch_moment_nm == pytest.approx(0.006)
    assert r.pitch_moment_nm == pytest.approx(0.006)
    assert r.pitch_couple_force_n == pytest.approx(0.006 / 0.080)


def test_rotational_and_translational_moments_superpose_with_sign():
    p = base(lateral_accel_g=0.0, fore_aft_accel_g=0.5,
             pitch_inertia_kg_m2=0.002, pitch_angular_accel_rad_s2=3.0)
    r = evaluate_inertial_retention(p)
    assert r.pitch_moment_nm == pytest.approx(r.translational_pitch_moment_nm + r.rotational_pitch_moment_nm)


def test_rotational_moment_requires_reaction_span_even_without_translation():
    r = evaluate_inertial_retention(base(lateral_accel_g=0.0, fore_aft_accel_g=0.0,
        bilateral_support_span_mm=0.0, yaw_inertia_kg_m2=0.001, yaw_angular_accel_rad_s2=4.0))
    assert not r.yaw_load_path_closed and r.yaw_couple_force_n is None
    assert not r.bilateral_load_path_closed and r.bilateral_resultant_couple_force_n is None


def test_nonzero_yaw_moment_requires_bilateral_span():
    r = evaluate_inertial_retention(base(bilateral_support_span_mm=0.0, fore_aft_accel_g=0.0,
                                         cg_vertical_mm=0.0))
    assert not r.yaw_load_path_closed and r.yaw_couple_force_n is None


def test_nonzero_pitch_moment_requires_vertical_span():
    r = evaluate_inertial_retention(base(vertical_support_span_mm=0.0, lateral_accel_g=0.0))
    assert not r.pitch_load_path_closed and r.pitch_couple_force_n is None


def test_nonzero_roll_moment_requires_bilateral_span():
    r = evaluate_inertial_retention(base(bilateral_support_span_mm=0.0, fore_aft_accel_g=0.0,
                                         cg_anterior_mm=0.0, cg_vertical_mm=20.0))
    assert not r.roll_load_path_closed and r.roll_couple_force_n is None


def test_bilateral_span_reduces_yaw_and_roll_couple_force():
    small = evaluate_inertial_retention(base(bilateral_support_span_mm=60.0))
    large = evaluate_inertial_retention(base(bilateral_support_span_mm=120.0))
    assert small.yaw_couple_force_n == pytest.approx(2.0 * large.yaw_couple_force_n)
    assert small.roll_couple_force_n == pytest.approx(2.0 * large.roll_couple_force_n)
    assert small.bilateral_resultant_couple_force_n == pytest.approx(2.0 * large.bilateral_resultant_couple_force_n)


def test_simultaneous_yaw_and_roll_resolve_to_bilateral_vector_demand():
    r = evaluate_inertial_retention(base(lateral_accel_g=0.5, fore_aft_accel_g=0.0))
    assert r.yaw_couple_force_n != 0.0 and r.roll_couple_force_n != 0.0
    expected = math.hypot(r.yaw_couple_force_n, r.roll_couple_force_n)
    assert r.bilateral_resultant_couple_force_n == pytest.approx(expected)
    assert r.bilateral_resultant_couple_force_n > max(r.yaw_couple_force_n, r.roll_couple_force_n)
    assert r.bilateral_load_path_closed


def test_single_axis_bilateral_demand_does_not_inflate_resultant():
    r = evaluate_inertial_retention(base(lateral_accel_g=0.5, fore_aft_accel_g=0.0,
                                         cg_vertical_mm=0.0))
    assert r.roll_couple_force_n == 0.0
    assert r.bilateral_resultant_couple_force_n == pytest.approx(r.yaw_couple_force_n)


def test_zero_acceleration_closes_without_artificial_couple():
    r = evaluate_inertial_retention(base(lateral_accel_g=0.0, fore_aft_accel_g=0.0,
                                         bilateral_support_span_mm=0.0, vertical_support_span_mm=0.0))
    assert r.yaw_load_path_closed and r.pitch_load_path_closed and r.roll_load_path_closed
    assert r.bilateral_load_path_closed
    assert r.yaw_couple_force_n == 0.0 and r.pitch_couple_force_n == 0.0 and r.roll_couple_force_n == 0.0
    assert r.bilateral_resultant_couple_force_n == 0.0


def test_signed_acceleration_preserves_moment_direction():
    pos = evaluate_inertial_retention(base(lateral_accel_g=0.5, fore_aft_accel_g=0.0))
    neg = evaluate_inertial_retention(base(lateral_accel_g=-0.5, fore_aft_accel_g=0.0))
    assert pos.yaw_moment_nm == pytest.approx(-neg.yaw_moment_nm)
    assert pos.roll_moment_nm == pytest.approx(-neg.roll_moment_nm)
    assert pos.yaw_couple_force_n == pytest.approx(neg.yaw_couple_force_n)
    assert pos.roll_couple_force_n == pytest.approx(neg.roll_couple_force_n)
    assert pos.bilateral_resultant_couple_force_n == pytest.approx(neg.bilateral_resultant_couple_force_n)


def test_doe_is_cartesian_and_deterministic():
    r = inertial_retention_doe(base(), lateral_accel_g=(-0.5, 0.0, 0.5), fore_aft_accel_g=(-0.25, 0.25))
    assert len(r) == 6
    assert r == inertial_retention_doe(base(), lateral_accel_g=(-0.5, 0.0, 0.5), fore_aft_accel_g=(-0.25, 0.25))


@pytest.mark.parametrize("field,value", [("loaded_mass_g", 0.0), ("bilateral_support_span_mm", -1.0),
    ("vertical_support_span_mm", -1.0), ("lateral_accel_g", math.inf),
    ("fore_aft_accel_g", math.nan), ("cg_vertical_mm", math.inf),
    ("pitch_inertia_kg_m2", -0.001), ("yaw_angular_accel_rad_s2", math.inf)])
def test_invalid_inputs_fail_closed(field, value):
    with pytest.raises(ValueError):
        evaluate_inertial_retention(base(**{field: value}))
