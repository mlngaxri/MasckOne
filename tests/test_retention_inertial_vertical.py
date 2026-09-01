import math
import pytest
from masck_one.retention_inertial import InertialRetentionInputs, evaluate_inertial_retention, inertial_retention_doe


def case(**kw):
    p = dict(loaded_mass_g=255.0, lateral_accel_g=0.0, fore_aft_accel_g=0.0,
             vertical_accel_g=0.5, cg_lateral_mm=5.0, cg_anterior_mm=25.0,
             cg_vertical_mm=20.0, bilateral_support_span_mm=120.0,
             vertical_support_span_mm=80.0)
    p.update(kw)
    return InertialRetentionInputs(**p)


def test_vertical_translation_enters_3d_resultant():
    r = evaluate_inertial_retention(case())
    assert r.vertical_force_n == pytest.approx(0.255 * 0.5 * 9.80665)
    assert r.translational_resultant_n == pytest.approx(abs(r.vertical_force_n))


def test_vertical_translation_at_anterior_offset_creates_pitch():
    r = evaluate_inertial_retention(case(cg_lateral_mm=0.0, cg_vertical_mm=0.0))
    assert r.pitch_moment_nm == pytest.approx(0.025 * r.vertical_force_n)
    assert r.roll_moment_nm == 0.0


def test_vertical_translation_at_lateral_offset_creates_signed_roll():
    r = evaluate_inertial_retention(case(cg_anterior_mm=0.0, cg_vertical_mm=0.0))
    assert r.roll_moment_nm == pytest.approx(-0.005 * r.vertical_force_n)
    assert r.pitch_moment_nm == 0.0


def test_vertical_translation_requires_pitch_reaction_span():
    r = evaluate_inertial_retention(case(vertical_support_span_mm=0.0, cg_lateral_mm=0.0))
    assert not r.pitch_load_path_closed
    assert r.pitch_couple_force_n is None


def test_vertical_doe_is_cartesian_and_deterministic():
    args = dict(lateral_accel_g=(-0.5, 0.5), fore_aft_accel_g=(-0.25, 0.25),
                vertical_accel_g=(-0.2, 0.0, 0.2))
    r = inertial_retention_doe(case(), **args)
    assert len(r) == 12
    assert r == inertial_retention_doe(case(), **args)


def test_nonfinite_vertical_acceleration_fails_closed():
    with pytest.raises(ValueError):
        evaluate_inertial_retention(case(vertical_accel_g=math.inf))
