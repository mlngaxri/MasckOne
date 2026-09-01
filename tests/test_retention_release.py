import math
import pytest

from masck_one.retention_release import (
    RetentionInputs,
    evaluate_retention,
    release_trajectory_clearance,
    retention_doe,
)


def baseline(**overrides):
    data = dict(
        loaded_mass_g=255.0,
        cg_anterior_mm=30.0,
        support_vertical_offset_mm=0.0,
        occipital_share=0.30,
        crown_share=0.50,
        facial_preload_n=2.0,
        friction_coefficient=0.40,
        release_force_n=8.0,
        release_travel_mm=6.0,
        accidental_pull_n=3.0,
        grip_clearance_mm=14.0,
        hair_keepout_mm=6.0,
    )
    data.update(overrides)
    return RetentionInputs(**data)


def test_load_path_closes_weight_ledger():
    r = evaluate_retention(baseline())
    assert r.occipital_vertical_n + r.crown_vertical_n + r.facial_vertical_n == pytest.approx(r.weight_n)
    assert r.pitch_moment_nm == pytest.approx(r.weight_n * 0.030)
    assert r.evidence_status == "DIGITAL_SENSITIVITY_ONLY"


def test_more_crown_support_reduces_residual_facial_vertical_load():
    low = evaluate_retention(baseline(crown_share=0.30))
    high = evaluate_retention(baseline(crown_share=0.60))
    assert high.facial_vertical_n < low.facial_vertical_n


def test_slip_margin_exposes_low_friction_failure_hypothesis():
    r = evaluate_retention(baseline(friction_coefficient=0.05, facial_preload_n=1.0))
    assert r.vertical_slip_margin_n < 0


def test_release_force_is_not_silently_promoted_to_pass():
    r = evaluate_retention(baseline(release_force_n=8.0, accidental_pull_n=9.0))
    assert r.accidental_release_margin_n < 0
    assert r.release_work_mj == pytest.approx(48.0)


def test_grip_and_hair_keepouts_are_explicit():
    r = evaluate_retention(baseline(grip_clearance_mm=11.9, hair_keepout_mm=4.9))
    assert not r.grip_access_ok
    assert not r.hair_keepout_ok


def test_invalid_and_nonfinite_inputs_fail_closed():
    with pytest.raises(ValueError):
        evaluate_retention(baseline(crown_share=0.8, occipital_share=0.3))
    with pytest.raises(ValueError):
        evaluate_retention(baseline(release_force_n=math.inf))


def test_doe_spans_cg_friction_and_crown_uncertainty():
    results = retention_doe(baseline())
    assert len(results) == 27
    assert max(r.pitch_moment_nm for r in results) > min(r.pitch_moment_nm for r in results)
    assert max(r.vertical_slip_margin_n for r in results) > min(r.vertical_slip_margin_n for r in results)


def test_release_trajectory_reports_minimum_sampled_clearance():
    d = release_trajectory_clearance(
        ((0.0, 0.0), (5.0, 0.0), (10.0, 0.0)),
        ((5.0, 5.0),),
        minimum_clearance_mm=4.0,
    )
    assert d == pytest.approx(5.0)


def test_empty_release_trajectory_fails_closed():
    with pytest.raises(ValueError):
        release_trajectory_clearance((), ((0.0, 0.0),), minimum_clearance_mm=1.0)
