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
    assert checks["load_0p12_to_0p20N_full_stroke_at_4ms"] is True
    assert checks["overauthority_0p28_to_0p32N_not_claimed_full_stroke"] is True
    assert checks["load_sweep_avoids_hard_stop"] is True
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
