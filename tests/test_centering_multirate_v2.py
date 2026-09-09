from __future__ import annotations

import pytest

from studies.centering_multirate_v2 import build_manifest, run


@pytest.fixture(scope="module")
def centering_v2_manifest():
    return build_manifest()


def test_v2_removes_the_delayed_derivative_latency_cliff(centering_v2_manifest):
    checks = centering_v2_manifest["digital_checks"]
    assert centering_v2_manifest["selected_controller_study"]["derivative_feedback_removed"] is True
    assert centering_v2_manifest["selected_controller_study"]["passive_bias_required_N"] == 0.0
    assert checks["nominal_full_stroke_through_10ms_delay"] is True
    assert checks["nominal_no_saturation_through_10ms_delay"] is True


def test_v2_noise_and_load_studies_respect_actuator_force_authority(centering_v2_manifest):
    checks = centering_v2_manifest["digital_checks"]
    assert checks["acquires_through_20um_noise_at_4ms"] is True
    assert checks["30um_noise_is_not_claimed"] is True

    rows = centering_v2_manifest["load_sweep_at_4ms"]
    inside_authority = [row for row in rows if row["load_N"] <= 0.20]
    above_force_ceiling = [row for row in rows if row["load_N"] >= 0.28]

    assert all(row["full_stroke_under_nominal"] and not row["hard_stop_exceeded"] for row in inside_authority)
    assert all(not row["full_stroke_under_nominal"] for row in above_force_ceiling)
    assert all(not row["hard_stop_exceeded"] for row in rows)
    # The old all-load assertion is intentionally false: 0.28-0.32 N exceeds the
    # 0.27 N study actuator ceiling and must not be represented as full-stroke authority.
    assert checks["load_0p12_to_0p32N_full_stroke_at_4ms"] is False
    assert centering_v2_manifest["physical_validation_eligible"] is False


def test_v2_supervisor_withdraws_step_and_overload_without_repeated_stop_impact(centering_v2_manifest):
    assert centering_v2_manifest["digital_checks"]["4_to_10ms_step_and_overload_supervisor_avoids_hard_stop"] is True
    for row in centering_v2_manifest["disturbance_sweep"]:
        if row["disturbance"] in {"step", "overload"}:
            assert row["fault_waveform_withdrawal_s"] is not None
            assert row["hard_stop_exceeded"] is False


def test_v2_rejects_unknown_disturbance():
    with pytest.raises(ValueError):
        run(disturbance="unknown")
