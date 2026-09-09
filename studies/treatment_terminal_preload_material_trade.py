from __future__ import annotations

"""Preload element trade for the deterministic terminal treatment mount.

The purpose is to avoid adding spring-metal inserts merely because they sound
premium. The preload element does not carry normal 40 Hz reaction; it only keeps the
carrier closed against rigid master datums. That makes an integral engineered-polymer
flexure a serious V1 candidate because it can provide the required small preload with
low part count, no insert rattle and inherently lossy structural behavior.

All properties are architecture-study assumptions. No polymer grade or spring alloy
is selected, and creep/fatigue/chemical/wet behavior remain physical validation.
"""

import json
from pathlib import Path

SCHEMA = "MASCK_ONE_TREATMENT_TERMINAL_PRELOAD_MATERIAL_TRADE_V1"
SOURCE_TREATMENT_HEAD_SHA = "7246c0c1787d28e9e5cb99c9fbcb0d6fbf7da7db"

PRELOAD_TARGET_N = 0.30
CONTINUOUS_REACTION_REFERENCE_N = 0.20
LOSSY_BACKUP_GAP_MM = 0.04


def cantilever_screen(*, modulus_mpa: float, width_mm: float, thickness_mm: float, length_mm: float) -> dict[str, float]:
    inertia = width_mm * thickness_mm**3 / 12.0
    stiffness = 3.0 * modulus_mpa * inertia / length_mm**3
    deflection = PRELOAD_TARGET_N / stiffness
    stress = 6.0 * PRELOAD_TARGET_N * length_mm / (width_mm * thickness_mm**2)
    backup_force = PRELOAD_TARGET_N + stiffness * LOSSY_BACKUP_GAP_MM
    return {
        "modulus_study_MPa": modulus_mpa,
        "width_mm": width_mm,
        "thickness_mm": thickness_mm,
        "length_mm": length_mm,
        "linear_tip_stiffness_N_per_mm": stiffness,
        "preload_deflection_seed_mm": deflection,
        "preload_root_stress_proxy_MPa": stress,
        "force_at_lossy_backup_entry_N": backup_force,
    }


def spring_metal_candidate() -> dict[str, object]:
    return {
        "topology": "SEPARATE_SPRING_METAL_INSERT",
        "screen": cantilever_screen(
            modulus_mpa=190000.0,
            width_mm=1.00,
            thickness_mm=0.17,
            length_mm=5.00,
        ),
        "advantages": [
            "LOW_CREEP_POTENTIAL_WITH_CORRECT_GRADE",
            "REPEATABLE_ELASTIC_FORCE_POTENTIAL",
            "COMPACT_CROSS_SECTION",
        ],
        "penalties": [
            "EXTRA_PART_AND_ROOT_CAPTURE",
            "INSERT_ASSEMBLY_AND_INSPECTION",
            "POTENTIAL_HIGH_Q_RINGING_PATH",
            "GALVANIC_AND_WET_ISOLATION_DETAIL",
        ],
    }


def integral_polymer_candidate() -> dict[str, object]:
    # Geometry selected to fit as a relieved tongue in the carrier yoke. 2.5 GPa is
    # a generic engineering-polymer study modulus, not a material selection.
    return {
        "topology": "INTEGRAL_RELIEVED_ENGINEERED_POLYMER_FLEXURE",
        "screen": cantilever_screen(
            modulus_mpa=2500.0,
            width_mm=1.20,
            thickness_mm=0.55,
            length_mm=4.00,
        ),
        "advantages": [
            "ZERO_EXTRA_SPRING_PARTS",
            "NO_INSERT_ROOT_RATTLE",
            "INHERENTLY_LOSSIER_THAN_BARE_SPRING_METAL",
            "SIMPLE_SOURCE_BOUND_CARRIER_INTEGRATION",
        ],
        "penalties": [
            "CREEP_AND_TEMPERATURE_SENSITIVITY_MUST_BE_PROVED",
            "CHEMICAL_WET_FATIGUE_GRADE_SELECTION_REQUIRED",
            "MOLD_FLOW_AND_FLEXURE_ROOT_QUALITY_ARE_CTQS",
        ],
    }


def build_manifest() -> dict[str, object]:
    metal = spring_metal_candidate()
    polymer = integral_polymer_candidate()
    ps = polymer["screen"]
    return {
        "schema": SCHEMA,
        "source_treatment_head_sha": SOURCE_TREATMENT_HEAD_SHA,
        "preload_target_N": PRELOAD_TARGET_N,
        "continuous_reaction_reference_N": CONTINUOUS_REACTION_REFERENCE_N,
        "spring_metal_candidate": metal,
        "integral_polymer_candidate": polymer,
        "selected_v1_digital_candidate": "INTEGRAL_RELIEVED_ENGINEERED_POLYMER_FLEXURE",
        "selection_reason": (
            "THE_PRELOAD_ELEMENT_IS_NOT_THE_NORMAL_WORKING_REACTION_MEMBER; A RELIEVED INTEGRAL FLEXURE "
            "CAN PROVIDE THE STUDY PRELOAD WITH NO INSERT PART, NO ROOT-CAPTURE RATTLE PATH AND LOWER "
            "ACOUSTIC-Q. SPRING METAL REMAINS THE BACKUP IF PHYSICAL CREEP/FATIGUE TESTING REJECTS POLYMER."
        ),
        "digital_screen_checks": {
            "preload_exceeds_continuous_reference": PRELOAD_TARGET_N > CONTINUOUS_REACTION_REFERENCE_N,
            "polymer_preload_deflection_below_0p20_mm": ps["preload_deflection_seed_mm"] < 0.20,
            "polymer_linear_stress_proxy_below_25_MPa": ps["preload_root_stress_proxy_MPa"] < 25.0,
            "backup_engages_before_transient_reference": ps["force_at_lossy_backup_entry_N"] < 0.60,
        },
        "physical_validation_eligible": False,
        "physical_validation": (
            "OPEN_EXACT_POLYMER_GRADE_CREEP_RELAXATION_FATIGUE_WET_CHEMICAL_TEMPERATURE_MOLDING_"
            "ROOT_NOTCH_WEAR_FORCE_TRAVEL_ACOUSTICS_AND_SPRING_METAL_FALLBACK_COMPARISON"
        ),
    }


def write_manifest(path: str | Path) -> dict[str, object]:
    payload = build_manifest()
    Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


if __name__ == "__main__":
    print(json.dumps(build_manifest(), indent=2, sort_keys=True))
