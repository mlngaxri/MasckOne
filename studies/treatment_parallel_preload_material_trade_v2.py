from __future__ import annotations

"""Material/topology trade for the axis-tuned terminal preload stages.

The new parallel-leaf study fixes an important kinematic problem: the preload shoe
should translate into the rigid datum instead of rotating into it. This file asks the
next question: should that fixed-guided pair be integral polymer or a spring-metal
insert?

The answer is deliberately architecture-level. The preload elements do NOT carry the
normal 40 Hz reaction; they only keep the carrier closed against rigid master datums.
However, losing preload through creep/relaxation would reopen a gap and reintroduce
rattle. For that reason preload retention is weighted more heavily than minimum part
count.

No exact polymer or spring grade is selected. Moduli are study assumptions only.
"""

from dataclasses import dataclass
import json
import math
from pathlib import Path

from studies.treatment_parallel_preload_flexure import (
    AXIS_CLEARANCE_MM,
    CONTINUOUS_REACTION_REFERENCE_N,
    ENTRY_OVERCLOSURE_MM,
    FULL_SEAT_PRELOAD_N,
    LOSSY_BACKUP_TRAVEL_SEED_MM,
    TRANSIENT_REACTION_REFERENCE_N,
    build_axis as build_metal_axis,
)

SCHEMA = "MASCK_ONE_TREATMENT_PARALLEL_PRELOAD_MATERIAL_TRADE_V2"
SOURCE_PARALLEL_PRELOAD_HEAD_SHA = "83c22492fa4ab63d501b74c6680c46712c1582c2"

# Generic engineered-polymer screening properties only. Geometry is intentionally
# longer/wider than the prior single-cantilever V5 because fixed-guided translation
# needs two leaves per axis and continuous strain/creep must be reduced.
POLYMER_E_STUDY_MPA = 2500.0
POLYMER_LEAF_WIDTH_MM = 0.75
POLYMER_X_LENGTH_MM = 7.00
POLYMER_Z_LENGTH_MM = 7.00

SPRING_METAL_INSERTS_PER_STATION = 2
POLYMER_INTEGRAL_EXTRA_PARTS_PER_STATION = 0


@dataclass(frozen=True, slots=True)
class PolymerAxis:
    axis: str
    target_deflection_mm: float
    required_pair_stiffness_N_per_mm: float
    selected_length_mm: float
    required_thickness_mm: float
    equivalent_surface_strain_proxy: float
    linear_stress_proxy_MPa: float
    seated_preload_N: float
    backup_first_engagement_force_N: float

    def manifest(self) -> dict[str, float | str]:
        return {
            "axis": self.axis,
            "target_deflection_mm": self.target_deflection_mm,
            "required_pair_stiffness_N_per_mm": self.required_pair_stiffness_N_per_mm,
            "selected_length_mm": self.selected_length_mm,
            "leaf_width_mm": POLYMER_LEAF_WIDTH_MM,
            "required_thickness_mm": self.required_thickness_mm,
            "equivalent_surface_strain_proxy": self.equivalent_surface_strain_proxy,
            "equivalent_surface_strain_percent_proxy": 100.0 * self.equivalent_surface_strain_proxy,
            "linear_stress_proxy_MPa": self.linear_stress_proxy_MPa,
            "seated_preload_N": self.seated_preload_N,
            "backup_first_engagement_force_N": self.backup_first_engagement_force_N,
        }


def build_polymer_axis(axis: str) -> PolymerAxis:
    clearance = AXIS_CLEARANCE_MM[axis]
    target_deflection = clearance + ENTRY_OVERCLOSURE_MM
    stiffness = FULL_SEAT_PRELOAD_N / target_deflection
    length = POLYMER_X_LENGTH_MM if axis == "X" else POLYMER_Z_LENGTH_MM
    # Fixed-guided pair: k_pair = 2 E b t^3 / L^3.
    thickness = (
        stiffness
        * length**3
        / (2.0 * POLYMER_E_STUDY_MPA * POLYMER_LEAF_WIDTH_MM)
    ) ** (1.0 / 3.0)
    # Surface strain for fixed-guided end translation: eps ~= 3 t delta / L^2.
    strain = 3.0 * thickness * target_deflection / length**2
    stress = POLYMER_E_STUDY_MPA * strain
    backup_force = FULL_SEAT_PRELOAD_N + stiffness * LOSSY_BACKUP_TRAVEL_SEED_MM
    return PolymerAxis(
        axis=axis,
        target_deflection_mm=target_deflection,
        required_pair_stiffness_N_per_mm=stiffness,
        selected_length_mm=length,
        required_thickness_mm=thickness,
        equivalent_surface_strain_proxy=strain,
        linear_stress_proxy_MPa=stress,
        seated_preload_N=FULL_SEAT_PRELOAD_N,
        backup_first_engagement_force_N=backup_force,
    )


def spring_metal_candidate() -> dict[str, object]:
    x, z = build_metal_axis("X"), build_metal_axis("Z")
    return {
        "topology": "TWO_AXIS_SPECIFIC_FIXED_GUIDED_SPRING_METAL_INSERTS_PER_STATION",
        "x_axis": x.manifest(),
        "z_axis": z.manifest(),
        "extra_insert_parts_per_station": SPRING_METAL_INSERTS_PER_STATION,
        "working_contact": "POLYMER_OR_ENGINEERING_DATUM_SHOE_TO_RIGID_SHOULDER_NOT_BARE_METAL_IMPACT",
        "damping_requirement": (
            "SPRING_ROOT_AND_NONFLEXING_BORDER_REQUIRE_LOSSY_POLYMER_CAPTURE_OR_EQUIVALENT; "
            "BARE_FREE_RINGING_INSERT_IS_NOT_ACCEPTABLE"
        ),
        "advantages": [
            "LOWER_LONG_TERM_PRELOAD_RELAXATION_RISK_THAN_GENERIC_POLYMER",
            "THIN_FIXED_GUIDED_LEAVES_LIMIT_SHOE_PITCH_YAW",
            "AXIS_SPECIFIC_STIFFNESS_MATCHES_X_Z_CLEARANCE",
            "SMALL_ENTRY_FORCE_AND_ZERO_SLOPE_CAM_ENDPOINTS",
        ],
        "penalties": [
            "TWO_INSERTS_PER_STATION_IN_CURRENT_SIMPLE_IMPLEMENTATION",
            "FORMING_OR_LASER_STAMP_PROCESS_AND_ROOT_CAPTURE_REQUIRED",
            "DAMPING_REQUIRED_TO_BLOCK_HIGH_Q_RINGING_PATH",
            "EXACT_GRADE_RESIDUAL_STRESS_AND_FATIGUE_OPEN",
        ],
    }


def integral_polymer_parallel_candidate() -> dict[str, object]:
    x, z = build_polymer_axis("X"), build_polymer_axis("Z")
    return {
        "topology": "INTEGRAL_AXIS_SPECIFIC_FIXED_GUIDED_POLYMER_LEAF_PAIRS",
        "x_axis": x.manifest(),
        "z_axis": z.manifest(),
        "extra_insert_parts_per_station": POLYMER_INTEGRAL_EXTRA_PARTS_PER_STATION,
        "advantages": [
            "NO_SEPARATE_SPRING_INSERTS",
            "NO_LOOSE_INSERT_RATTLE_PATH",
            "INHERENTLY_HIGHER_STRUCTURAL_LOSS_THAN_BARE_METAL",
            "CAN_BE_MOLDED_AS_ONE_CARRIER_IF ROOT_FLOW_AND_TOOLING_CLOSE",
        ],
        "penalties": [
            "CONTINUOUS_STATIC_STRAIN_REQUIRES CREEP_RELAXATION_PROOF",
            "PRELOAD_LOSS_DIRECTLY_REOPENS_DATUM_GAP_AND_RATTLE_RISK",
            "THICKER_FLEXURE_SECTIONS_AND_LONGER_RELIEF WINDOWS",
            "WET_CHEMICAL_TEMPERATURE_AND_MOLD_ROOT_QUALITY_ARE FIRST_ORDER",
        ],
    }


def build_manifest() -> dict[str, object]:
    metal = spring_metal_candidate()
    polymer = integral_polymer_parallel_candidate()
    px = polymer["x_axis"]
    pz = polymer["z_axis"]
    return {
        "schema": SCHEMA,
        "source_parallel_preload_head_sha": SOURCE_PARALLEL_PRELOAD_HEAD_SHA,
        "design_requirements": {
            "full_seat_preload_N_per_axis": FULL_SEAT_PRELOAD_N,
            "continuous_reaction_reference_N": CONTINUOUS_REACTION_REFERENCE_N,
            "transient_reaction_reference_N": TRANSIENT_REACTION_REFERENCE_N,
            "lossy_backup_travel_seed_mm": LOSSY_BACKUP_TRAVEL_SEED_MM,
            "normal_40hz_reaction_member": "RIGID_MASTER_DATUM_NOT_PRELOAD_FLEXURE",
        },
        "spring_metal_candidate": metal,
        "integral_polymer_parallel_candidate": polymer,
        "polymer_screen": {
            "x_surface_strain_percent_proxy": px["equivalent_surface_strain_percent_proxy"],
            "z_surface_strain_percent_proxy": pz["equivalent_surface_strain_percent_proxy"],
            "interpretation": (
                "LINEAR_STRESS_IS_LOW_BUT CONTINUOUS ~0.5_PERCENT_CLASS_STRAIN MAKES CREEP_RELAXATION "
                "A FIRST_ORDER UNKNOWN; LOW STRESS ALONE DOES NOT PROVE PRELOAD RETENTION"
            ),
        },
        "selected_v1_architecture_candidate": (
            "AXIS_SPECIFIC_FIXED_GUIDED_SPRING_METAL_PRELOAD_INSERTS_WITH_LOSSY_ROOT_CAPTURE"
        ),
        "selection_reason": (
            "THE PREMIUM FAILURE TO AVOID IS PRELOAD RELAXATION THAT REOPENS A HARD DATUM GAP. "
            "PARALLEL SPRING-METAL LEAVES BETTER PROTECT LONG-TERM PRELOAD WHILE RIGID DATUMS STILL "
            "CARRY NORMAL 40HZ LOAD. TWO SMALL INSERTS PER STATION ARE CURRENTLY JUSTIFIED; A LATER "
            "MONOLITHIC TWO-AXIS INSERT MAY REDUCE PART COUNT ONLY IF IT PRESERVES INDEPENDENT X/Z EQUALIZATION."
        ),
        "rejected_for_current_v1_baseline": [
            "SINGLE_CANTILEVER_POLYMER_PRELOAD_V5_DUE_SHOE_TIP_AND_CREEP_UNCERTAINTY",
            "FULLY_RIGID_FOUR_FACE_TAPER_DUE_TOLERANCE_OVERCONSTRAINT",
            "TIGHT_LONG_RAIL_DUE_FRICTION_BINDING_AND_PROCESS_SENSITIVITY",
        ],
        "physical_validation_eligible": False,
        "physical_validation": (
            "OPEN_SPRING_GRADE_FORMING_RESIDUAL_STRESS_FATIGUE_ROOT_CAPTURE_DAMPING_RINGDOWN_"
            "INSERTION_RELEASE_FORCE_CONTACT_FRICTION_WEAR_WET_CONTAMINATION_AND_POLYMER_CREEP_FALLBACK_TEST"
        ),
    }


def write_manifest(path: str | Path) -> dict[str, object]:
    payload = build_manifest()
    Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


if __name__ == "__main__":
    print(json.dumps(build_manifest(), indent=2, sort_keys=True))
