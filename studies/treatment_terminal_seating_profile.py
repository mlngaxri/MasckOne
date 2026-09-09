from __future__ import annotations

"""Smooth terminal seating-force architecture study for the treatment carrier.

The goal is not to make a tight rail feel precise. The long rail stays deliberately
clearance-fit. Precision is created only in the final fraction of travel:

FREE RAIL APPROACH
-> S-CURVE CAM ACQUISITION
-> RIGID X/Z MASTER DATUMS FULLY SEATED
-> AXIAL DETENT / LANDING EVENT
-> POSITIVE Y STOP.

The radial preload springs are independent so dimensional error on X does not force
Z out of contact (and vice versa). Each compliant shoe is intended to bottom the
carrier against one rigid master datum during normal 40 Hz reaction. A lossy backup
then a rigid stop catches abnormal reverse travel. Numeric values are study seeds,
not production tolerances, measured forces or physical validation.
"""

import json
import math
from pathlib import Path

SCHEMA = "MASCK_ONE_TREATMENT_TERMINAL_SEATING_PROFILE_V1"
SOURCE_CELL6_HEAD_SHA = "fcccde02b31cc1c4e01136630d92e550e4e09a11"
SOURCE_TREATMENT_DATUM_STUDY_SHA = "1b3a95b525112bbea9bb89267cdd24285f14b680"

CONTINUOUS_REACTION_REFERENCE_N = 0.20
TRANSIENT_REACTION_REFERENCE_N = 0.60

# Stronger than the first 0.24 N study seed. This is internal carrier preload, not
# facial treatment force. 0.30 N leaves 0.10 N ideal normal-contact margin above the
# 0.20 N continuous reaction reference on either axis when treated conservatively.
AXIS_PRELOAD_TARGET_N = 0.30
SPRING_MODULUS_STUDY_MPA = 190000.0
SPRING_LEAF_WIDTH_MM = 1.00
SPRING_LEAF_THICKNESS_MM = 0.17
SPRING_LEAF_LENGTH_MM = 5.00

# Final terminal cam only. Long service travel remains clearance-fit.
CAM_ACQUISITION_TRAVEL_MM = 0.65
CAM_FULL_SEAT_LAND_MM = 0.16

# Abnormal reverse-travel hierarchy. The lossy backup is not a normal 40 Hz stop.
LOSSY_BACKUP_GAP_MM = 0.04
LOSSY_BACKUP_COMPRESSION_TO_HARD_STOP_MM = 0.05
LOSSY_BACKUP_STIFFNESS_STUDY_N_PER_MM = 4.50

# Current Cell 6 detent linear proxy retained only as a comparison seed.
AXIAL_DETENT_FORCE_PROXY_N = 0.26


def spring_leaf_screen() -> dict[str, float]:
    b = SPRING_LEAF_WIDTH_MM
    t = SPRING_LEAF_THICKNESS_MM
    length = SPRING_LEAF_LENGTH_MM
    inertia = b * t**3 / 12.0
    stiffness = 3.0 * SPRING_MODULUS_STUDY_MPA * inertia / length**3
    preload_deflection = AXIS_PRELOAD_TARGET_N / stiffness
    backup_entry_force = AXIS_PRELOAD_TARGET_N + stiffness * LOSSY_BACKUP_GAP_MM
    hard_stop_force_without_bumper = AXIS_PRELOAD_TARGET_N + stiffness * (
        LOSSY_BACKUP_GAP_MM + LOSSY_BACKUP_COMPRESSION_TO_HARD_STOP_MM
    )
    preload_stress = 6.0 * AXIS_PRELOAD_TARGET_N * length / (b * t**2)
    backup_entry_stress = 6.0 * backup_entry_force * length / (b * t**2)
    hard_stop_stress = 6.0 * hard_stop_force_without_bumper * length / (b * t**2)
    return {
        "second_moment_mm4": inertia,
        "linear_tip_stiffness_N_per_mm": stiffness,
        "preload_target_N": AXIS_PRELOAD_TARGET_N,
        "preload_deflection_seed_mm": preload_deflection,
        "preload_root_stress_proxy_MPa": preload_stress,
        "force_at_lossy_backup_entry_N": backup_entry_force,
        "root_stress_at_lossy_backup_entry_proxy_MPa": backup_entry_stress,
        "spring_force_at_hard_stop_without_bumper_N": hard_stop_force_without_bumper,
        "root_stress_at_hard_stop_without_bumper_proxy_MPa": hard_stop_stress,
    }


def smoothstep(s: float) -> float:
    s = min(1.0, max(0.0, s))
    return 3.0 * s**2 - 2.0 * s**3


def smoothstep_derivative(s: float) -> float:
    s = min(1.0, max(0.0, s))
    return 6.0 * s - 6.0 * s**2


def terminal_cam_profile(samples: int = 101) -> dict[str, object]:
    if samples < 5:
        raise ValueError("at least five samples required")
    spring = spring_leaf_screen()
    delta_max = spring["preload_deflection_seed_mm"]
    k = spring["linear_tip_stiffness_N_per_mm"]
    rows: list[dict[str, float]] = []
    max_axial = 0.0
    for i in range(samples):
        s = i / (samples - 1)
        q = smoothstep(s)
        qp = smoothstep_derivative(s)
        radial_deflection = delta_max * q
        radial_force = k * radial_deflection
        ddelta_dy = delta_max * qp / CAM_ACQUISITION_TRAVEL_MM
        # Ideal frictionless cam reaction. Friction, edge radius and real contact are
        # intentionally excluded and remain physical-validation inputs.
        axial_cam_force = radial_force * ddelta_dy
        max_axial = max(max_axial, axial_cam_force)
        rows.append(
            {
                "normalized_travel": s,
                "radial_deflection_mm": radial_deflection,
                "radial_force_N": radial_force,
                "ideal_frictionless_axial_cam_force_N": axial_cam_force,
            }
        )
    return {
        "cam_type": "C1_SMOOTHSTEP_ZERO_SLOPE_AT_ENTRY_AND_FULL_SEAT",
        "acquisition_travel_mm": CAM_ACQUISITION_TRAVEL_MM,
        "full_seat_land_mm": CAM_FULL_SEAT_LAND_MM,
        "per_axis_peak_ideal_frictionless_axial_cam_force_N": max_axial,
        "two_axis_peak_upper_bound_if_coincident_N": 2.0 * max_axial,
        "rows": rows,
    }


def abnormal_reverse_travel_screen() -> dict[str, float | bool]:
    spring = spring_leaf_screen()
    spring_k = spring["linear_tip_stiffness_N_per_mm"]
    force_at_backup = spring["force_at_lossy_backup_entry_N"]
    bumper_addition = LOSSY_BACKUP_STIFFNESS_STUDY_N_PER_MM * LOSSY_BACKUP_COMPRESSION_TO_HARD_STOP_MM
    total_at_hard_stop = (
        AXIS_PRELOAD_TARGET_N
        + spring_k * (LOSSY_BACKUP_GAP_MM + LOSSY_BACKUP_COMPRESSION_TO_HARD_STOP_MM)
        + bumper_addition
    )
    return {
        "continuous_reference_N": CONTINUOUS_REACTION_REFERENCE_N,
        "transient_reference_N": TRANSIENT_REACTION_REFERENCE_N,
        "normal_master_datum_contact_margin_N": AXIS_PRELOAD_TARGET_N - CONTINUOUS_REACTION_REFERENCE_N,
        "lossy_backup_gap_mm": LOSSY_BACKUP_GAP_MM,
        "force_at_lossy_backup_entry_N": force_at_backup,
        "lossy_backup_compression_to_hard_stop_mm": LOSSY_BACKUP_COMPRESSION_TO_HARD_STOP_MM,
        "lossy_backup_stiffness_study_N_per_mm": LOSSY_BACKUP_STIFFNESS_STUDY_N_PER_MM,
        "combined_force_at_hard_stop_proxy_N": total_at_hard_stop,
        "normal_40hz_should_not_reach_backup": AXIS_PRELOAD_TARGET_N > CONTINUOUS_REACTION_REFERENCE_N,
        "backup_should_engage_before_transient_reference": force_at_backup < TRANSIENT_REACTION_REFERENCE_N,
        "hard_stop_proxy_reaches_transient_reference": total_at_hard_stop >= TRANSIENT_REACTION_REFERENCE_N,
    }


def build_manifest() -> dict[str, object]:
    spring = spring_leaf_screen()
    cam = terminal_cam_profile()
    abnormal = abnormal_reverse_travel_screen()
    return {
        "schema": SCHEMA,
        "source_cell6_head_sha": SOURCE_CELL6_HEAD_SHA,
        "source_treatment_datum_study_sha": SOURCE_TREATMENT_DATUM_STUDY_SHA,
        "selected_seating_sequence": (
            "FREE_CLEARANCE_RAIL -> ZERO_SLOPE_S_CURVE_TERMINAL_CAM -> "
            "INDEPENDENT_X_Z_PRELOAD_SHOES -> RIGID_MASTER_DATUMS -> "
            "GENTLE_AXIAL_DETENT -> POSITIVE_Y_SEAT"
        ),
        "selected_abnormal_load_sequence": (
            "MASTER_DATUM_CLOSED_IN_NORMAL_USE -> SMALL_REVERSE_TRAVEL -> "
            "LOSSY_BACKUP -> PROGRESSIVE_COMPRESSION -> RIGID_OVERLOAD_STOP"
        ),
        "spring_leaf_screen": spring,
        "terminal_cam_profile": cam,
        "abnormal_reverse_travel_screen": abnormal,
        "axial_detent_force_proxy_N": AXIAL_DETENT_FORCE_PROXY_N,
        "ideal_terminal_insertion_force_comment": (
            "THE_TWO_RADIAL_CAM_REACTIONS_ARE_SMALLER_THAN_THE_CURRENT_DETENT_PROXY; "
            "THE_DETENT/LANDING_SHOULD_DEFINE_THE_MUTED_FINAL_EVENT_WHILE THE CAMS "
            "REMOVE_PLAY_PROGRESSIVELY BEFORE THAT EVENT"
        ),
        "buttery_mechanics_rule": (
            "DO_NOT_REMOVE_RAIL_CLEARANCE_TO_HIDE_PLAY; ACQUIRE FREELY, PRELOAD ONLY AT THE "
            "TERMINAL SEAT, USE ZERO-SLOPE CAM ENDS, KEEP NORMAL REACTION ON RIGID DATUMS, "
            "AND RESERVE LOSSY/HARD STOPS FOR ABNORMAL LOAD"
        ),
        "physical_validation_eligible": False,
        "physical_validation": (
            "OPEN_REAL_SPRING_GRADE_NONLINEAR_STRESS_FATIGUE_CAM_FRICTION_CONTACT_PRESSURE_"
            "TOLERANCE_FORCE_TRAVEL_DAMPING_ACOUSTICS_WEAR_WET_CONTAMINATION_AND_ASSEMBLY"
        ),
    }


def write_manifest(path: str | Path) -> dict[str, object]:
    payload = build_manifest()
    Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


if __name__ == "__main__":
    print(json.dumps(build_manifest(), indent=2, sort_keys=True))
