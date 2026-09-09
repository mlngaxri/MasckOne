from __future__ import annotations

"""Axis-tuned terminal preload flexure study.

The treatment carrier has different X and Z running clearances (0.16 and 0.12 mm).
Using one spring deflection for both axes creates an unnecessary early-load step on
one axis. This study instead sizes two independent parallel-leaf flexures so each
axis has:

- ~5 um nominal overclosure at first cam contact;
- nearly zero initial seating force;
- the same 0.30 N full-seat preload target;
- zero force-gradient at cam entry and full seat through a smoothstep acquisition;
- matched mid-travel force gradient despite different running clearances;
- a separate lossy/rigid overload backup before the spring carries the 0.60 N
  transient study reference.

The parallel-leaf topology is selected over a single cantilever because the rigid
shoe should translate with low pitch/yaw rather than tip into the reaction shoulder.
All numbers are architecture-study seeds, not production material/tolerance or
physical force/acoustic evidence.
"""

from dataclasses import dataclass
import json
import math
from pathlib import Path

SCHEMA = "MASCK_ONE_TREATMENT_PARALLEL_PRELOAD_FLEXURE_V1"
SOURCE_TREATMENT_V4_HEAD_SHA = "7246c0c1787d28e9e5cb99c9fbcb0d6fbf7da7db"

E_STUDY_MPA = 190000.0
SHEET_THICKNESS_MM = 0.12
LEAF_WIDTH_MM = 0.65
LEAVES_PER_AXIS = 2
CAM_TRAVEL_MM = 0.65
ENTRY_OVERCLOSURE_MM = 0.005
FULL_SEAT_PRELOAD_N = 0.30
CONTINUOUS_REACTION_REFERENCE_N = 0.20
TRANSIENT_REACTION_REFERENCE_N = 0.60
LOSSY_BACKUP_TRAVEL_SEED_MM = 0.04

AXIS_CLEARANCE_MM = {"X": 0.16, "Z": 0.12}


@dataclass(frozen=True, slots=True)
class AxisFlexure:
    axis: str
    running_clearance_mm: float
    target_deflection_mm: float
    required_pair_stiffness_N_per_mm: float
    selected_leaf_length_mm: float
    seated_preload_N: float
    entry_force_N: float
    continuous_contact_margin_N: float
    backup_first_engagement_force_N: float
    leaf_root_stress_proxy_seated_MPa: float
    leaf_root_stress_proxy_backup_MPa: float
    maximum_cam_force_gradient_N_per_mm: float

    def manifest(self) -> dict[str, float | str]:
        return {
            "axis": self.axis,
            "running_clearance_mm": self.running_clearance_mm,
            "target_deflection_mm": self.target_deflection_mm,
            "required_pair_stiffness_N_per_mm": self.required_pair_stiffness_N_per_mm,
            "selected_leaf_length_mm": self.selected_leaf_length_mm,
            "seated_preload_N": self.seated_preload_N,
            "entry_force_N": self.entry_force_N,
            "continuous_contact_margin_N": self.continuous_contact_margin_N,
            "backup_travel_seed_mm": LOSSY_BACKUP_TRAVEL_SEED_MM,
            "backup_first_engagement_force_N": self.backup_first_engagement_force_N,
            "leaf_root_stress_proxy_seated_MPa": self.leaf_root_stress_proxy_seated_MPa,
            "leaf_root_stress_proxy_backup_MPa": self.leaf_root_stress_proxy_backup_MPa,
            "maximum_cam_force_gradient_N_per_mm": self.maximum_cam_force_gradient_N_per_mm,
        }


def _smoothstep(s: float) -> float:
    s = min(1.0, max(0.0, float(s)))
    return 3.0 * s**2 - 2.0 * s**3


def _smoothstep_derivative(s: float) -> float:
    s = min(1.0, max(0.0, float(s)))
    return 6.0 * s * (1.0 - s)


def pair_stiffness_N_per_mm(length_mm: float) -> float:
    """Two fixed-guided leaf beams translating one rigid shoe.

    Each leaf has k=12EI/L^3; I=b*t^3/12. Two leaves therefore give
    k_pair=2*E*b*t^3/L^3.
    """
    if length_mm <= 0.0:
        raise ValueError("leaf length must be positive")
    return (
        2.0
        * E_STUDY_MPA
        * LEAF_WIDTH_MM
        * SHEET_THICKNESS_MM**3
        / length_mm**3
    )


def required_leaf_length_mm(clearance_mm: float) -> float:
    target_deflection = clearance_mm + ENTRY_OVERCLOSURE_MM
    k_required = FULL_SEAT_PRELOAD_N / target_deflection
    numerator = 2.0 * E_STUDY_MPA * LEAF_WIDTH_MM * SHEET_THICKNESS_MM**3
    return (numerator / k_required) ** (1.0 / 3.0)


def _root_stress_proxy_MPa(force_total_N: float, length_mm: float) -> float:
    # For two fixed-guided leaves, each leaf carries F/2 and has end moment
    # approximately (F/2)*L/2 = F*L/4. Rectangular-section bending stress is 6M/(b t^2).
    return (
        1.5
        * force_total_N
        * length_mm
        / (LEAF_WIDTH_MM * SHEET_THICKNESS_MM**2)
    )


def build_axis(axis: str) -> AxisFlexure:
    clearance = AXIS_CLEARANCE_MM[axis]
    target_deflection = clearance + ENTRY_OVERCLOSURE_MM
    k_required = FULL_SEAT_PRELOAD_N / target_deflection
    length = required_leaf_length_mm(clearance)
    k_selected = pair_stiffness_N_per_mm(length)
    entry_force = k_selected * ENTRY_OVERCLOSURE_MM
    seated = k_selected * target_deflection
    backup_force = seated + k_selected * LOSSY_BACKUP_TRAVEL_SEED_MM
    max_gradient = (
        k_selected
        * clearance
        * _smoothstep_derivative(0.5)
        / CAM_TRAVEL_MM
    )
    return AxisFlexure(
        axis=axis,
        running_clearance_mm=clearance,
        target_deflection_mm=target_deflection,
        required_pair_stiffness_N_per_mm=k_selected,
        selected_leaf_length_mm=length,
        seated_preload_N=seated,
        entry_force_N=entry_force,
        continuous_contact_margin_N=seated - CONTINUOUS_REACTION_REFERENCE_N,
        backup_first_engagement_force_N=backup_force,
        leaf_root_stress_proxy_seated_MPa=_root_stress_proxy_MPa(seated, length),
        leaf_root_stress_proxy_backup_MPa=_root_stress_proxy_MPa(backup_force, length),
        maximum_cam_force_gradient_N_per_mm=max_gradient,
    )


def force_profile(axis: str, samples: int = 21) -> list[dict[str, float]]:
    if samples < 3:
        raise ValueError("at least three samples required")
    row = build_axis(axis)
    k = row.required_pair_stiffness_N_per_mm
    clearance = row.running_clearance_mm
    output: list[dict[str, float]] = []
    for i in range(samples):
        s = i / (samples - 1)
        travel = CAM_TRAVEL_MM * s
        deflection = ENTRY_OVERCLOSURE_MM + clearance * _smoothstep(s)
        force = k * deflection
        gradient = k * clearance * _smoothstep_derivative(s) / CAM_TRAVEL_MM
        output.append(
            {
                "normalized_travel": s,
                "axial_travel_mm": travel,
                "spring_deflection_mm": deflection,
                "preload_force_N": force,
                "force_gradient_N_per_mm": gradient,
            }
        )
    return output


def build_manifest() -> dict[str, object]:
    x = build_axis("X")
    z = build_axis("Z")
    return {
        "schema": SCHEMA,
        "source_treatment_v4_head_sha": SOURCE_TREATMENT_V4_HEAD_SHA,
        "spring_material_assumption": {
            "elastic_modulus_study_MPa": E_STUDY_MPA,
            "sheet_thickness_mm": SHEET_THICKNESS_MM,
            "leaf_width_mm": LEAF_WIDTH_MM,
            "leaves_per_axis": LEAVES_PER_AXIS,
            "status": "ANALYTICAL_STUDY_ONLY_GRADE_AND_FATIGUE_OPEN",
        },
        "cam": {
            "travel_mm": CAM_TRAVEL_MM,
            "profile": "CUBIC_SMOOTHSTEP_ZERO_SLOPE_AT_ENTRY_AND_FULL_SEAT",
            "entry_overclosure_mm": ENTRY_OVERCLOSURE_MM,
        },
        "axes": {"X": x.manifest(), "Z": z.manifest()},
        "force_profiles": {"X": force_profile("X"), "Z": force_profile("Z")},
        "selected_direction": (
            "TWO_INDEPENDENT_PARALLEL_LEAF_PRELOAD_STAGES_WITH_AXIS_SPECIFIC_STIFFNESS; "
            "LOW_FORCE_ENTRY -> MATCHED_SMOOTH_FORCE_BUILD -> 0.30N_SEATED_PRELOAD -> "
            "LOSSY_BACKUP -> RIGID_OVERLOAD_STOP"
        ),
        "buttery_reasoning": (
            "DIFFERENT_X_Z_CLEARANCES_ARE_NOT_FORCED_THROUGH_ONE_SPRING_DEFLECTION; "
            "ZERO_SLOPE_CAM_ENDPOINTS_REMOVE_FORCE_JERK; PARALLEL_LEAVES_LIMIT_SHOE_TIP; "
            "NORMAL_40HZ_CONTACT_STAYS_CLOSED_WITHOUT CYCLING A HARD GAP"
        ),
        "physical_validation_eligible": False,
        "physical_validation": (
            "OPEN_NONLINEAR_FEA_SPRING_GRADE_FORMING_RESIDUAL_STRESS_FATIGUE_CONTACT_FRICTION_"
            "WEAR_CREEP_DAMPING_ACOUSTICS_WET_CONTAMINATION_TOLERANCE_AND_INSERTION_FORCE"
        ),
    }


def write_manifest(path: str | Path) -> dict[str, object]:
    payload = build_manifest()
    Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


if __name__ == "__main__":
    print(json.dumps(build_manifest(), indent=2, sort_keys=True))
