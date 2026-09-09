from __future__ import annotations

"""Latency-tolerant active-centering architecture study.

This is a successor to treatment strike `studies/centering_multirate.py` at
2bcdba02e9ee30e86baa74e7cecc9095e8bf4a71. The earlier controller differentiated a
delayed noisy position signal. That term was the dominant source of the apparent
1 ms latency cliff. V2 deliberately keeps the centering loop far below 40 Hz:

- known 40 Hz waveform is subtracted at the measurement timestamp;
- slow integral bias recenters static load;
- very small proportional correction remains;
- no delayed velocity/derivative feedback is used;
- acquisition uses a 100 ms position window and uncertainty of its mean rather than
  requiring raw sensor scatter to masquerade as mechanical standstill;
- a supervisor withdraws the treatment waveform before repeated stop impact.

This remains an inert numerical plant/controller DOE. It is not deployable firmware,
a human-use setting, an actuator capability measurement, or a sensor qualification.
"""

import json
import math
from pathlib import Path

import numpy as np

SCHEMA = "MASCK_ONE_CENTERING_MULTIRATE_V2"
SOURCE_TREATMENT_HEAD = "2bcdba02e9ee30e86baa74e7cecc9095e8bf4a71"
SOURCE_ORIGINAL_MODEL_BLOB = "6e285b73d35691281f0045805291ced598b2cce3"
SOURCE_ORIGINAL_RESULTS_BLOB = "907282885ea824ad91f5978993797e0f05fee3ed"

K_N_PER_MM = 0.07414875
REFERENCE_MASS_KG = 2.7e-6
WAVE_HZ = 40.0
WAVE_RAD_S = 2.0 * math.pi * WAVE_HZ
FORCE_LIMIT_N = 0.27
SAMPLE_S = 0.0005
DT_S = 0.0001

KP_N_PER_MM = 0.010
KD_N_S_PER_MM = 0.0
KI_N_PER_MM_S = 1.6
ERROR_FILTER_TAU_S = 0.005

ACQUISITION_WINDOW_S = 0.100
ACQUISITION_MEAN_LIMIT_MM = 0.008
ACQUISITION_MEAN_SE_LIMIT_MM = 0.0015
ACQUISITION_DRIFT_LIMIT_MM_S = 0.03
ACQUISITION_FORCE_LIMIT_N = 0.24

SUPERVISOR_POSITION_MM = 0.315
SUPERVISOR_BIAS_N = 0.235
WAVEFORM_WITHDRAWAL_S = 0.050


def run(
    *,
    delay_ms: float = 4.0,
    noise_um: float = 2.0,
    mass_g: float = 2.7,
    foil_mm: float = 0.05,
    load_N: float = 0.20,
    seal_k_N_mm: float = 0.02,
    seal_c_N_s_mm: float = 0.00015,
    stop_k_N_mm: float = 4.0,
    disturbance: str = "none",
    identified_fixture_impedance: bool = False,
    supervisor_enabled: bool = True,
    duration_s: float = 2.5,
    seed: int = 5483,
) -> dict[str, object]:
    if delay_ms < 0.0 or noise_um < 0.0 or mass_g <= 0.0 or foil_mm <= 0.0:
        raise ValueError("invalid centering V2 input")
    if disturbance not in {"none", "ramp", "step", "overload"}:
        raise ValueError("unknown disturbance")

    hold = round(SAMPLE_S / DT_S)
    count = round(duration_s / DT_S)
    delay_samples = round(delay_ms / 1000.0 / SAMPLE_S)
    flexure_k = K_N_PER_MM * (foil_mm / 0.05) ** 3
    plant_k = flexure_k + seal_k_N_mm
    mass_kg = mass_g / 1e6

    # Actual unpowered static equilibrium with the same unilateral-stop DOE as the
    # source model. No passive bias is required by the selected V2 controller.
    x = -load_N / plant_k if abs(load_N / plant_k) < 0.35 else -math.copysign(
        (abs(load_N) + stop_k_N_mm * 0.35) / (plant_k + stop_k_N_mm), load_N
    )
    v = 0.0
    integ = 0.0
    force = 0.0
    lp_error = x
    bias = 0.0
    waveform_start = None
    fault_time = None
    history: list[tuple[float, float]] = []
    ready_history: list[float] = []
    rows: list[tuple[float, float, float, float, float, float, float]] = []
    rng = np.random.default_rng(seed)

    def waveform(t: float) -> tuple[float, float, float]:
        if waveform_start is None:
            return 0.0, 0.0, 0.0
        tr = t - waveform_start
        if tr <= 0.0:
            return 0.0, 0.0, 0.0
        ramp_s = 0.25
        if tr < ramp_s:
            amp = 0.13 * (1.0 - math.cos(math.pi * tr / ramp_s))
            damp = 0.13 * math.pi / ramp_s * math.sin(math.pi * tr / ramp_s)
            ddamp = 0.13 * (math.pi / ramp_s) ** 2 * math.cos(math.pi * tr / ramp_s)
        else:
            amp, damp, ddamp = 0.26, 0.0, 0.0
        if fault_time is not None:
            tau = t - fault_time
            if tau >= WAVEFORM_WITHDRAWAL_S:
                amp = damp = ddamp = 0.0
            elif tau > 0.0:
                f = 0.5 * (1.0 + math.cos(math.pi * tau / WAVEFORM_WITHDRAWAL_S))
                df = -0.5 * math.pi / WAVEFORM_WITHDRAWAL_S * math.sin(math.pi * tau / WAVEFORM_WITHDRAWAL_S)
                ddf = -0.5 * (math.pi / WAVEFORM_WITHDRAWAL_S) ** 2 * math.cos(math.pi * tau / WAVEFORM_WITHDRAWAL_S)
                a0, da0, dda0 = amp, damp, ddamp
                amp = a0 * f
                damp = da0 * f + a0 * df
                ddamp = dda0 * f + 2.0 * da0 * df + a0 * ddf
        return (
            amp * math.sin(WAVE_RAD_S * tr),
            damp * math.sin(WAVE_RAD_S * tr) + amp * WAVE_RAD_S * math.cos(WAVE_RAD_S * tr),
            ddamp * math.sin(WAVE_RAD_S * tr) + 2.0 * damp * WAVE_RAD_S * math.cos(WAVE_RAD_S * tr) - amp * WAVE_RAD_S**2 * math.sin(WAVE_RAD_S * tr),
        )

    window_samples = round(ACQUISITION_WINDOW_S / SAMPLE_S)
    for n in range(count):
        t = n * DT_S
        r, rv, ra = waveform(t)
        actual_load = load_N
        if disturbance == "ramp" and t > 1.6:
            actual_load += 0.03 * min(1.0, (t - 1.6) / 0.2)
        elif disturbance == "step" and t > 1.6:
            actual_load += 0.05
        elif disturbance == "overload" and t > 1.6:
            actual_load += 0.12

        if n % hold == 0:
            history.append((x + rng.normal(0.0, noise_um / 1000.0), r))
            y, delayed_reference = history[max(0, len(history) - 1 - delay_samples)]
            error = y - delayed_reference
            lp_error += SAMPLE_S / (ERROR_FILTER_TAU_S + SAMPLE_S) * (error - lp_error)
            trial = integ + lp_error * SAMPLE_S
            trial_bias = -KI_N_PER_MM_S * trial
            if identified_fixture_impedance:
                feedforward = mass_kg * ra + plant_k * r + seal_c_N_s_mm * rv
            else:
                feedforward = REFERENCE_MASS_KG * ra + (K_N_PER_MM + 0.02) * r + 0.00015 * rv
            command = trial_bias + feedforward - KP_N_PER_MM * error
            if abs(command) < FORCE_LIMIT_N or command * lp_error > 0.0:
                integ = trial
            bias = -KI_N_PER_MM_S * integ
            command = bias + feedforward - KP_N_PER_MM * error
            force = float(np.clip(command, -FORCE_LIMIT_N, FORCE_LIMIT_N))

            if supervisor_enabled and waveform_start is not None and fault_time is None:
                if abs(y) > SUPERVISOR_POSITION_MM or abs(bias) > SUPERVISOR_BIAS_N:
                    fault_time = t

            if waveform_start is None:
                ready_history.append(error)
                window = np.asarray(ready_history[-window_samples:])
                if len(window) == window_samples:
                    slope = float(np.polyfit(np.arange(window_samples) * SAMPLE_S, window, 1)[0])
                    mean_se = float(window.std(ddof=1) / math.sqrt(window_samples))
                    if (
                        abs(window.mean()) < ACQUISITION_MEAN_LIMIT_MM
                        and mean_se < ACQUISITION_MEAN_SE_LIMIT_MM
                        and abs(slope) < ACQUISITION_DRIFT_LIMIT_MM_S
                        and abs(force) < ACQUISITION_FORCE_LIMIT_N
                    ):
                        waveform_start = t

        def rhs(xx: float, vv: float) -> tuple[float, float]:
            stop_force = -stop_k_N_mm * max(xx - 0.35, 0.0) + stop_k_N_mm * max(-xx - 0.35, 0.0)
            if xx > 0.35 and vv > 0.0:
                stop_force -= 0.003 * vv
            if xx < -0.35 and vv < 0.0:
                stop_force -= 0.003 * vv
            return vv, (force - plant_k * xx - seal_c_N_s_mm * vv - actual_load + stop_force) / mass_kg

        a, b = rhs(x, v)
        c, e = rhs(x + DT_S * a / 2.0, v + DT_S * b / 2.0)
        f, g = rhs(x + DT_S * c / 2.0, v + DT_S * e / 2.0)
        h, j = rhs(x + DT_S * f, v + DT_S * g)
        x += DT_S * (a + 2.0 * c + 2.0 * f + h) / 6.0
        v += DT_S * (b + 2.0 * e + 2.0 * g + j) / 6.0
        if n % hold == 0:
            rows.append((t, x, v, force, r, bias, actual_load))

    data = np.asarray(rows)
    steady = (data[:, 0] > max((waveform_start or duration_s) + 0.5, 1.2)) & (data[:, 0] < 1.59)
    after = data[:, 0] > 1.65
    return {
        "delay_ms": delay_ms,
        "noise_um": noise_um,
        "mass_g": mass_g,
        "foil_mm": foil_mm,
        "load_N": load_N,
        "disturbance": disturbance,
        "identified_fixture_impedance": identified_fixture_impedance,
        "supervisor_enabled": supervisor_enabled,
        "acquired": waveform_start is not None,
        "waveform_start_s": waveform_start,
        "fault_waveform_withdrawal_s": fault_time,
        "peak_displacement_mm": float(max(abs(data[:, 1]))),
        "hard_stop_exceeded": bool(max(abs(data[:, 1])) >= 0.45),
        "steady_peak_tracking_error_mm": float(max(abs(data[steady, 1] - data[steady, 4]))) if any(steady) else None,
        "steady_peak_displacement_mm": float(max(abs(data[steady, 1]))) if any(steady) else None,
        "disturbed_peak_displacement_mm": float(max(abs(data[after, 1]))) if any(after) else None,
        "saturation_fraction": float(np.mean(abs(data[:, 3]) >= FORCE_LIMIT_N - 1e-5)),
        "peak_force_N": float(max(abs(data[:, 3]))),
        "full_stroke_under_nominal": bool(any(steady) and max(abs(data[steady, 1] - data[steady, 4])) < 0.03 and max(abs(data[steady, 1])) < 0.32),
        "evidence": "LINEAR_FLEXURE_PLUS_UNILATERAL_STOP_CONTROLLER_DOE_NOT_DEPLOYABLE_FIRMWARE_OR_HUMAN_USE",
    }


def build_manifest() -> dict[str, object]:
    nominal_delays = [run(delay_ms=d, supervisor_enabled=True) for d in (1, 2, 4, 6, 10)]
    noise_cases = [run(delay_ms=4, noise_um=n, supervisor_enabled=True) for n in (2, 5, 10, 20, 30)]
    disturbances = [run(delay_ms=d, disturbance=kind, supervisor_enabled=True) for d in (4, 6, 10) for kind in ("ramp", "step", "overload")]
    load_cases = [run(delay_ms=4, load_N=load, supervisor_enabled=True) for load in (0.12, 0.16, 0.20, 0.24, 0.28, 0.32)]
    return {
        "schema": SCHEMA,
        "source_treatment_head": SOURCE_TREATMENT_HEAD,
        "source_original_model_blob": SOURCE_ORIGINAL_MODEL_BLOB,
        "source_original_results_blob": SOURCE_ORIGINAL_RESULTS_BLOB,
        "selected_controller_study": {
            "sample_period_ms": SAMPLE_S * 1000.0,
            "kp_N_per_mm": KP_N_PER_MM,
            "kd_N_s_per_mm": KD_N_S_PER_MM,
            "ki_N_per_mm_s": KI_N_PER_MM_S,
            "derivative_feedback_removed": KD_N_S_PER_MM == 0.0,
            "passive_bias_required_N": 0.0,
            "waveform_withdrawal_ms": WAVEFORM_WITHDRAWAL_S * 1000.0,
        },
        "nominal_delay_sweep": nominal_delays,
        "noise_sweep_at_4ms": noise_cases,
        "disturbance_sweep": disturbances,
        "load_sweep_at_4ms": load_cases,
        "digital_checks": {
            "nominal_full_stroke_through_10ms_delay": all(row["acquired"] and row["full_stroke_under_nominal"] and not row["hard_stop_exceeded"] for row in nominal_delays),
            "nominal_no_saturation_through_10ms_delay": all(row["saturation_fraction"] == 0.0 for row in nominal_delays),
            "acquires_through_20um_noise_at_4ms": all(row["acquired"] for row in noise_cases if row["noise_um"] <= 20),
            "30um_noise_is_not_claimed": next(row for row in noise_cases if row["noise_um"] == 30)["acquired"] is False,
            "load_0p12_to_0p32N_full_stroke_at_4ms": all(row["full_stroke_under_nominal"] and not row["hard_stop_exceeded"] for row in load_cases),
            "4_to_10ms_step_and_overload_supervisor_avoids_hard_stop": all(not row["hard_stop_exceeded"] for row in disturbances if row["disturbance"] in {"step", "overload"}),
        },
        "interpretation": (
            "THE PREVIOUS ~1MS CLIFF IS NOT AN INHERENT SENSOR REQUIREMENT IN THIS PLANT MODEL. "
            "REMOVING DELAYED DERIVATIVE FEEDBACK AND KEEPING CENTERING SLOW PRESERVES NOMINAL FULL STROKE "
            "THROUGH 10MS STUDIED DELAY. THIS RELAXES THE ARCHITECTURE SCREEN BUT DOES NOT QUALIFY A SENSOR OR CONTROLLER."
        ),
        "physical_validation_eligible": False,
        "physical_validation": (
            "OPEN_ACTUAL_ACTUATOR_FORCE_FIXTURE_IMPEDANCE_SENSOR_TRANSFER_FUNCTION_SENSOR_NOISE_MAGNET_GEOMETRY_"
            "NONLINEAR_FLEXURE_CONTACT_DAMPING_EMBEDDED_TIMING_FAULT_INJECTION_AND_BENCH_VALIDATION"
        ),
    }


def write_manifest(path: str | Path) -> dict[str, object]:
    payload = build_manifest()
    Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    return payload


if __name__ == "__main__":
    print(json.dumps(build_manifest(), indent=2, sort_keys=True, allow_nan=False))
