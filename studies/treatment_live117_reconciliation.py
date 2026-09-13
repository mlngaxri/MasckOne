"""Source-bound reconciliation of the treatment-platform strike with live PR #117.

Digital architecture study only. This script does not establish human-use settings,
physical force capability, fatigue life, acoustic quality, comfort, or production
tolerance capability.

The intent is to convert the previous treatment-strike conclusions into a current
mount/control decision against the latest Cell 6 carrier/reaction interfaces without
silently modifying Cell 6's keyed socket geometry.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

SCHEMA = "MASCK_ONE_TREATMENT_LIVE117_RECONCILIATION_V1"

# Exact source bindings used to make this decision.
RELEASED_MAIN_SHA = "42fa11818184cde998c6df25d7c46d4fb0e4c3eb"
CELL6_HEAD_SHA = "3e840d52d641b429669928ab9e4c207f08086ca1"
TREATMENT_HEAD_SHA = "2bcdba02e9ee30e86baa74e7cecc9095e8bf4a71"
TREATMENT_MULTIRATE_RESULTS_BLOB_SHA = "907282885ea824ad91f5978993797e0f05fee3ed"
TREATMENT_PHYSICS_RESULTS_BLOB_SHA = "f9d576751282f545660fee546b90c2bd62b34615"

REACTION_X_MM = 69.0
REACTION_Y_MM = 48.0
RAIL_LENGTH_MM = 6.0
RAIL_ROOT_WIDTH_MM = 5.0
RAIL_CROWN_WIDTH_MM = 6.0
RAIL_HEIGHT_MM = 1.8
RAIL_NOMINAL_LATERAL_GAP_MM = 0.15
LANDING_NOMINAL_GAP_MM = 0.12
DETENT_NOMINAL_GAP_MM = 0.12
CARRIER_PAD_WIDTH_MM = 8.0
CARRIER_PAD_HEIGHT_MM = 8.0

TREATMENT_AXIS_DEG = 61.0
STATIONS = {
    "ACTUATOR_REACTION_SUPERIOR_LEFT": {
        "treatment_center_mm": (-36.0, 70.0, 7.0),
        "axis_rotation_about_y_deg": -TREATMENT_AXIS_DEG,
        "reaction_center_xy_mm": (-REACTION_X_MM, REACTION_Y_MM),
    },
    "ACTUATOR_REACTION_SUPERIOR_RIGHT": {
        "treatment_center_mm": (36.0, 70.0, 7.0),
        "axis_rotation_about_y_deg": TREATMENT_AXIS_DEG,
        "reaction_center_xy_mm": (REACTION_X_MM, REACTION_Y_MM),
    },
    "ACTUATOR_REACTION_INFERIOR_LEFT": {
        "treatment_center_mm": (-52.0, -45.0, 3.0),
        "axis_rotation_about_y_deg": -TREATMENT_AXIS_DEG,
        "reaction_center_xy_mm": (-REACTION_X_MM, -REACTION_Y_MM),
    },
    "ACTUATOR_REACTION_INFERIOR_RIGHT": {
        "treatment_center_mm": (52.0, -45.0, 3.0),
        "axis_rotation_about_y_deg": TREATMENT_AXIS_DEG,
        "reaction_center_xy_mm": (REACTION_X_MM, -REACTION_Y_MM),
    },
}

SADDLE_OUTER_WIDTH_MM = 4.8
SADDLE_OUTER_HEIGHT_MM = 2.0
SADDLE_WALL_MM = 0.35
CONTINUOUS_FORCE_REFERENCE_N = 0.20
TRANSIENT_FORCE_REFERENCE_N = 0.60
ACTUATOR_FORCE_STUDY_LIMIT_N = 0.27
TREATMENT_STROKE_PP_MM = 0.52
SADDLE_NOMINAL_DEFLECTION_ALLOCATION_MM = 0.05

CONTROL_CASES = {
    "nominal_1ms": {"sensor_delay_ms": 1.0, "preload_N": 0.20, "peak_force_N": 0.22773206250507494, "saturation_fraction": 0.0, "full_stroke": True, "hard_stop_exceeded": False},
    "delay_2ms": {"sensor_delay_ms": 2.0, "preload_N": 0.20, "peak_force_N": 0.27, "saturation_fraction": 0.1804, "full_stroke": False, "hard_stop_exceeded": False},
    "delay_4ms": {"sensor_delay_ms": 4.0, "preload_N": 0.20, "peak_force_N": 0.27, "saturation_fraction": 0.296, "full_stroke": False, "hard_stop_exceeded": True},
    "ramp_disturbance": {"sensor_delay_ms": 1.0, "preload_N": 0.20, "peak_force_N": 0.25734594282922046, "saturation_fraction": 0.0, "full_stroke": True, "hard_stop_exceeded": False},
    "step_disturbance": {"sensor_delay_ms": 1.0, "preload_N": 0.20, "peak_force_N": 0.27, "saturation_fraction": 0.0418, "full_stroke": True, "hard_stop_exceeded": False},
    "overload_disturbance": {"sensor_delay_ms": 1.0, "preload_N": 0.20, "peak_force_N": 0.27, "saturation_fraction": 0.2868, "full_stroke": True, "hard_stop_exceeded": False},
    "supervised_step": {"sensor_delay_ms": 1.0, "preload_N": 0.20, "peak_force_N": 0.27, "fault_waveform_withdrawal_s": 1.611, "disturbance_start_s": 1.6, "disturbed_peak_displacement_mm": 0.20565232394161964, "hard_stop_exceeded": False},
    "supervised_overload": {"sensor_delay_ms": 1.0, "preload_N": 0.20, "peak_force_N": 0.27, "fault_waveform_withdrawal_s": 1.607, "disturbance_start_s": 1.6, "disturbed_peak_displacement_mm": 0.35898837748212475, "hard_stop_exceeded": False},
}

POSITION_OBSERVER_CASES = {
    "1ms_2um_2p7g": {"sensor_delay_ms": 1.0, "noise_um": 2.0, "mass_g": 2.7, "acquisition_peak_mm": 0.47174447555170407, "steady_tracking_peak_error_mm": 0.011658326975873573, "peak_force_N": 0.27},
    "2ms_5um_2p7g": {"sensor_delay_ms": 2.0, "noise_um": 5.0, "mass_g": 2.7, "acquisition_peak_mm": 0.928040442283244, "steady_tracking_peak_error_mm": 0.03368894943943548, "peak_force_N": 0.27},
}

FLEXURE_CASES = {
    0.04: {"axial_k_N_mm": 0.03831442176248423, "radial_k_N_mm": 23.196202844296003, "first_mode_Hz": 18.959172908265103, "free_drive_peak_N": 0.03438040899496837},
    0.05: {"axial_k_N_mm": 0.07426932388580454, "radial_k_N_mm": 28.995261031209253, "first_mode_Hz": 26.396295693443594, "free_drive_peak_N": 0.02503213444290509},
    0.06: {"axial_k_N_mm": 0.12736054805174035, "radial_k_N_mm": 34.79432414324904, "first_mode_Hz": 34.56652399780268, "free_drive_peak_N": 0.011228416159761778},
    0.07: {"axial_k_N_mm": 0.20068757136113644, "radial_k_N_mm": 40.59339311952053, "first_mode_Hz": 43.39088301643542, "free_drive_peak_N": 0.007836609900681205},
}


def rotate_y(point: tuple[float, float, float], angle_deg: float) -> tuple[float, float, float]:
    x, y, z = point
    a = math.radians(angle_deg)
    return (x * math.cos(a) + z * math.sin(a), y, -x * math.sin(a) + z * math.cos(a))


def add3(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return tuple(float(x + y) for x, y in zip(a, b))


def saddle_section_I_mm4() -> float:
    bi = SADDLE_OUTER_WIDTH_MM - 2.0 * SADDLE_WALL_MM
    hi = SADDLE_OUTER_HEIGHT_MM - 2.0 * SADDLE_WALL_MM
    return (SADDLE_OUTER_WIDTH_MM * SADDLE_OUTER_HEIGHT_MM**3 - bi * hi**3) / 12.0


def cantilever_deflection_mm(force_N: float, length_mm: float, E_MPa: float) -> float:
    return force_N * length_mm**3 / (3.0 * E_MPa * saddle_section_I_mm4())


def required_modulus_MPa(force_N: float, length_mm: float, max_deflection_mm: float) -> float:
    return force_N * length_mm**3 / (3.0 * saddle_section_I_mm4() * max_deflection_mm)


def station_geometry() -> dict[str, dict[str, object]]:
    out: dict[str, dict[str, object]] = {}
    local_rear_hub = (0.0, 2.8, -9.0)
    for reaction_id, item in STATIONS.items():
        center = item["treatment_center_mm"]
        angle = float(item["axis_rotation_about_y_deg"])
        rear_hub = add3(center, rotate_y(local_rear_hub, angle))
        rcx, rcy = item["reaction_center_xy_mm"]
        planar_span = math.hypot(rear_hub[0] - rcx, rear_hub[1] - rcy)
        direct_center_span = math.hypot(center[0] - rcx, center[1] - rcy)
        moment_nominal_Nmm = CONTINUOUS_FORCE_REFERENCE_N * planar_span
        moment_transient_Nmm = TRANSIENT_FORCE_REFERENCE_N * planar_span
        out[reaction_id] = {
            "treatment_center_mm": list(center),
            "axis_rotation_about_y_deg": angle,
            "axis_unit_vector_xyz": [math.sin(math.radians(angle)), 0.0, math.cos(math.radians(angle))],
            "reaction_center_xy_mm": [rcx, rcy],
            "rear_hub_target_mm": list(rear_hub),
            "direct_center_to_reaction_planar_span_mm": direct_center_span,
            "rear_hub_to_reaction_planar_span_mm": planar_span,
            "continuous_load_moment_upper_bound_Nmm": moment_nominal_Nmm,
            "transient_load_moment_upper_bound_Nmm": moment_transient_Nmm,
            "equivalent_contact_pair_force_at_6mm_spacing_N": {"continuous": moment_nominal_Nmm / RAIL_CROWN_WIDTH_MM, "transient": moment_transient_Nmm / RAIL_CROWN_WIDTH_MM},
        }
    return out


def saddle_stiffness(stations: dict[str, dict[str, object]]) -> dict[str, object]:
    worst_name, worst_item = max(stations.items(), key=lambda kv: float(kv[1]["rear_hub_to_reaction_planar_span_mm"]))
    L = float(worst_item["rear_hub_to_reaction_planar_span_mm"])
    F_nominal_z = CONTINUOUS_FORCE_REFERENCE_N * math.cos(math.radians(TREATMENT_AXIS_DEG))
    F_transient_z = TRANSIENT_FORCE_REFERENCE_N * math.cos(math.radians(TREATMENT_AXIS_DEG))
    materials = {
        "UNFILLED_ENGINEERING_POLYMER_STUDY_2P5GPA": 2500.0,
        "HIGH_STIFFNESS_POLYMER_COMPOSITE_STUDY_10GPA": 10000.0,
        "ALUMINUM_CLASS_STUDY_70GPA": 70000.0,
        "SPRING_STEEL_CLASS_STUDY_200GPA": 200000.0,
    }
    rows = {name: {"elastic_modulus_MPa_assumption": E, "continuous_z_component_deflection_mm": cantilever_deflection_mm(F_nominal_z, L, E), "transient_z_component_deflection_mm": cantilever_deflection_mm(F_transient_z, L, E)} for name, E in materials.items()}
    return {
        "worst_station": worst_name,
        "worst_planar_span_mm": L,
        "tube_second_moment_mm4": saddle_section_I_mm4(),
        "continuous_z_component_N": F_nominal_z,
        "transient_z_component_N": F_transient_z,
        "nominal_deflection_design_allocation_mm": SADDLE_NOMINAL_DEFLECTION_ALLOCATION_MM,
        "minimum_modulus_MPa_for_current_section_at_allocation": required_modulus_MPa(F_nominal_z, L, SADDLE_NOMINAL_DEFLECTION_ALLOCATION_MM),
        "material_class_studies": rows,
        "decision": "CURRENT_4P8x2P0x0P35_MM_SADDLE_SECTION_REQUIRES_HIGH_MODULUS_INSERT_CLASS_OR_LARGER_SECTION; UNFILLED_POLYMER_INTEGRAL_SADDLE_REJECTED_FOR_CURRENT_GEOMETRY",
        "evidence_status": "LINEAR_CANTILEVER_SCREEN_ONLY; JOINT_COMPLIANCE_AND_FATIGUE_PHYSICAL_OR_FEA_OPEN",
    }


def flexure_decision() -> dict[str, object]:
    rows = {}
    for t, case in FLEXURE_CASES.items():
        rows[f"{t:.2f}"] = {**case, "radial_to_axial_stiffness_ratio": case["radial_k_N_mm"] / case["axial_k_N_mm"], "first_mode_fractional_separation_from_40Hz": abs(case["first_mode_Hz"] - 40.0) / 40.0, "unpowered_linear_static_deflection_at_0p2N_mm": CONTINUOUS_FORCE_REFERENCE_N / case["axial_k_N_mm"]}
    return {"cases": rows, "selected_study_seed_mm": 0.05, "reason": "0P05_MM_RETAINS_ABOUT_390X_RADIAL_AXIAL_STIFFNESS_RATIO_AND_KEEPS_THE_FIRST_MODE_MATERIALLY_BELOW_40HZ; 0P06_0P07_FORCE_REDUCTION_IS_TOO_COUPLED_TO_NEAR_RESONANT_BEHAVIOR_FOR_V1_WITHOUT_IDENTIFIED_DAMPING", "physical_validation_open": True}


def control_decision() -> dict[str, object]:
    nominal = CONTROL_CASES["nominal_1ms"]
    ramp = CONTROL_CASES["ramp_disturbance"]
    return {
        "force_limit_N_study": ACTUATOR_FORCE_STUDY_LIMIT_N,
        "nominal_1ms_force_margin_N": ACTUATOR_FORCE_STUDY_LIMIT_N - nominal["peak_force_N"],
        "nominal_1ms_force_margin_fraction": (ACTUATOR_FORCE_STUDY_LIMIT_N - nominal["peak_force_N"]) / ACTUATOR_FORCE_STUDY_LIMIT_N,
        "ramp_force_margin_N": ACTUATOR_FORCE_STUDY_LIMIT_N - ramp["peak_force_N"],
        "cases": CONTROL_CASES,
        "position_observer_cases": POSITION_OBSERVER_CASES,
        "selected_v1_control_study": "WAVEFORM_SUBTRACTED_DIRECT_POSITION_MULTIRATE_CENTERING_WITH_STABLE_WINDOW_ACQUISITION_AND_EXPLICIT_WAVEFORM_WITHDRAWAL_SUPERVISOR",
        "observer_only_status": "REJECTED_AS_V1_BASELINE: 1MS_2UM_CASE_ACQUISITION_PEAK_EXCEEDS_0P45_MM_CURRENT_HARD_STOP_COORDINATE_IN_THE_MULTIRATE_PLANT",
        "latency_dependency": "END_TO_END_MEASUREMENT_CONTROL_DELAY_MUST_BE_DEMONSTRATED_IN_THE_1MS_CLASS_FOR_THIS_ARCHITECTURE; 2MS_CURRENT_MODEL_FAILS_ACQUISITION_AND_SATURATES",
        "note": "THE 1MS NOMINAL CASE HAS ONLY ~0.042 N PEAK FORCE MARGIN; THE RAMP CASE HAS ONLY ~0.013 N. STEP/OVERLOAD CASES REACH THE STUDY FORCE CEILING, SO SUPERVISED WAVEFORM WITHDRAWAL IS ARCHITECTURAL, NOT OPTIONAL.",
        "physical_validation_open": True,
    }


def mount_decision() -> dict[str, object]:
    return {
        "selected_reaction_path": ["CELL6_KEYED_FRAME_SOCKET", "CELL6_EXISTING_KEYED_MALE_REACTION_MATE_AND_SHOULDER", "CELL6_TAPERED_CARRIER_RAIL", "NEW_CELL7_FEMALE_SLIDE_SHOE_WITH_RIGID_UNDERSIDE_CAPTURE", "HIGH_MODULUS_POSTERIOR_SADDLE_INSERT", "FIXED_ACTUATOR_REAR_HUB", "ACTUATOR", "COMPLIANT_OUTPUT_COUPLING", "BEARINGLESS_MOVING_TREATMENT_STAGE"],
        "source_change": "DELETE_THE_TREATMENT_STRIKE_REQUIREMENT_FOR_NEW_CENTRAL_DRAW_PIN_BORE_AND_ASYMMETRIC_KEY_PORT_IN_CELL6; LATEST_CELL6_ALREADY_PROVIDES_A_KEYED_REACTION_MATE_PLUS_RAIL_PRELOAD_LANDING_AND_DETENT_STACK",
        "female_counterpart_requirements": {
            "service_insertion_axis": "+Y_TO_-Y",
            "nominal_lateral_gap_seed_mm": RAIL_NOMINAL_LATERAL_GAP_MM,
            "landing_gap_seed_mm": LANDING_NOMINAL_GAP_MM,
            "detent_gap_seed_mm": DETENT_NOMINAL_GAP_MM,
            "must_rigidly_react_working_load_dofs": ["X", "Z", "RX", "RY", "RZ"],
            "capture_after_seating": ["Y"],
            "anti_rattle_only_features": ["CELL6_PRELOAD_LEAF", "CELL6_COMPLIANT_DETENT"],
            "working_moment_rule": "PRELOAD_LEAF_AND_DETENT_MUST_NOT_CARRY_PRIMARY_MASSAGE_BENDING_MOMENT; RIGID_CHANNEL_SHOULDERS_AND_REACTION_MATE_MUST",
        },
        "whole_carrier_service_sweep": "OPEN_REQUIRES_BREP_ON_NEXT_INCREMENT",
        "production_tolerance_status": "NOMINAL_DIGITAL_SEEDS_ONLY",
    }


def build_report() -> dict[str, object]:
    stations = station_geometry()
    report = {
        "schema": SCHEMA,
        "source_bindings": {"released_main_sha": RELEASED_MAIN_SHA, "cell6_head_sha": CELL6_HEAD_SHA, "treatment_head_sha": TREATMENT_HEAD_SHA, "treatment_multirate_results_blob_sha": TREATMENT_MULTIRATE_RESULTS_BLOB_SHA, "treatment_physics_results_blob_sha": TREATMENT_PHYSICS_RESULTS_BLOB_SHA},
        "authority_references": {"treatment_axis_seed_deg": TREATMENT_AXIS_DEG, "treatment_stroke_pp_mm": TREATMENT_STROKE_PP_MM, "continuous_force_reference_N": CONTINUOUS_FORCE_REFERENCE_N, "transient_force_reference_N": TRANSIENT_FORCE_REFERENCE_N},
        "four_station_candidate": stations,
        "saddle_stiffness": saddle_stiffness(stations),
        "flexure": flexure_decision(),
        "control": control_decision(),
        "mount": mount_decision(),
        "decisions": ["PRESERVE_ACTIVE_SLOW_CENTERING_PLUS_40HZ_WAVEFORM", "SELECT_0P05_MM_FLEXURE_AS_CONSERVATIVE_V1_STUDY_SEED_PENDING_NONLINEAR_FEA", "REJECT_POSITION_OBSERVER_ONLY_AS_CURRENT_V1_BASELINE", "REMOVE_NEW_CELL6_DRAW_BORE_AND_KEY_PORT_REQUIREMENT", "CONSUME_EXISTING_CELL6_KEYED_MATE_PLUS_RAIL_PRELOAD_LANDING_DETENT", "USE_RIGID_FEMALE_CHANNEL_TO_CLOSE_RX_AND_CARRY_WORKING_MOMENT", "KEEP_PRELOAD_LEAF_AND_DETENT_AS_ANTI_RATTLE_CAPTURE_NOT_PRIMARY_REACTION", "CURRENT_SUPERIOR_POSTERIOR_SADDLE_SECTION_REQUIRES_HIGH_MODULUS_INSERT_CLASS_OR_SECTION_GROWTH", "MIRROR_LEFT_STATION_AXIS_SIGN_SO_BOTH_SIDES_TILT_OUTBOARD"],
        "digital_closure": {"four_station_world_seed": "DEFINED_ANALYTICALLY", "frame_reaction_source": "BOUND_TO_LIVE_CELL6_HEAD", "control_failure_boundary": "QUANTIFIED_FROM_TREATMENT_RESULTS", "whole_carrier_brep": "OPEN", "whole_carrier_continuous_service_sweep": "OPEN", "exact_saddle_joint_stiffness": "OPEN", "final_sensor_hardware": "OPEN"},
        "physical_validation_required": ["ACTUATOR_FORCE_STROKE_AND_COPPER_LOSS", "FLEXURE_NONLINEAR_STIFFNESS_STRESS_FATIGUE", "SADDLE_JOINT_STIFFNESS_AND_VIBRATION", "SENSOR_LATENCY_NOISE_AND_CALIBRATION", "CARRIER_INSERTION_PRELOAD_DETENT_FORCE_WEAR_ACOUSTICS", "FACIAL_PRELOAD_AND_COMFORT"],
    }
    assert len(stations) == 4
    assert all(abs(v["axis_rotation_about_y_deg"]) == TREATMENT_AXIS_DEG for v in stations.values())
    assert report["control"]["nominal_1ms_force_margin_N"] > 0.0
    assert CONTROL_CASES["delay_2ms"]["full_stroke"] is False
    assert CONTROL_CASES["delay_4ms"]["hard_stop_exceeded"] is True
    assert report["saddle_stiffness"]["minimum_modulus_MPa_for_current_section_at_allocation"] > 25000.0
    assert report["saddle_stiffness"]["minimum_modulus_MPa_for_current_section_at_allocation"] < 70000.0
    return report


if __name__ == "__main__":
    report = build_report()
    out = Path(__file__).with_name("treatment_live117_reconciliation_results.json")
    out.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
