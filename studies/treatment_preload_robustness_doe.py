from __future__ import annotations

"""Robustness DOE for the terminal no-rattle preload architecture.

This study asks a more useful question than whether the nominal 0.30 N design closes:
how quickly does the rigid-datum contact margin disappear when spring preload and
radial geometry move away from nominal?

The error/relaxation values are deliberately architecture-screen seeds. They are NOT
claims about molding capability, spring relaxation, supplier performance or a final
tolerance specification. The selected corner is intentionally conservative enough to
separate fragile from robust topologies before detailed DFM/physical data exist.
"""

from dataclasses import dataclass
import json
import math
from pathlib import Path

import numpy as np

SCHEMA = "MASCK_ONE_TREATMENT_PRELOAD_ROBUSTNESS_DOE_V1"
SOURCE_V6_HEAD_PARENT_SHA = "bb5c6aa3de893cc7e837032dd200b041ae6b0b61"

CONTINUOUS_REACTION_REFERENCE_N = 0.20
TRANSIENT_REACTION_REFERENCE_N = 0.60
DETENT_FORCE_PROXY_N = 0.26
X_CLEARANCE_MM = 0.16
Z_CLEARANCE_MM = 0.12
LOSSY_BACKUP_TRAVEL_MM = 0.04
E_STUDY_MPA = 190000.0

PRELOAD_TARGETS_N = (0.30, 0.34, 0.36, 0.38, 0.40)
ENTRY_OVERCLOSURES_MM = (0.005, 0.015, 0.020, 0.030)
CAM_TRAVELS_MM = (0.65, 0.80, 0.95)
RADIAL_ERROR_SEEDS_MM = (0.02, 0.03, 0.05)
RELAXATION_SEEDS = (0.10, 0.20, 0.30)

# Geometry options for the two-leaf fixed-guided spring cassette. Width is the width
# of ONE leaf; pair envelope is roughly 2*width + inter-leaf gap.
SPRING_GEOMETRY_OPTIONS = (
    (0.65, 0.12),
    (0.80, 0.15),
    (1.00, 0.12),
    (1.20, 0.12),
)
LEAF_PAIR_GAP_MM = 0.20

# Architecture comparison corner only. It is deliberately not named a production
# tolerance requirement.
ROBUSTNESS_CORNER_RADIAL_ERROR_MM = 0.05
ROBUSTNESS_CORNER_RELAXATION = 0.20


@dataclass(frozen=True, slots=True)
class AxisResult:
    axis: str
    clearance_mm: float
    stiffness_N_per_mm: float
    entry_force_N: float
    seated_force_N: float
    backup_entry_force_N: float
    robustness_corner_retained_force_N: float
    robustness_corner_margin_N: float
    peak_ideal_cam_axial_force_N: float


def _smoothstep(s: np.ndarray) -> np.ndarray:
    return 3.0 * s**2 - 2.0 * s**3


def _smoothstep_derivative(s: np.ndarray) -> np.ndarray:
    return 6.0 * s * (1.0 - s)


def axis_result(
    *,
    axis: str,
    preload_target_N: float,
    overclosure_mm: float,
    cam_travel_mm: float,
) -> AxisResult:
    clearance = X_CLEARANCE_MM if axis == "X" else Z_CLEARANCE_MM
    total_deflection = clearance + overclosure_mm
    k = preload_target_N / total_deflection
    entry_force = k * overclosure_mm
    backup_force = preload_target_N + k * LOSSY_BACKUP_TRAVEL_MM

    retained_before_relaxation = preload_target_N - k * ROBUSTNESS_CORNER_RADIAL_ERROR_MM
    retained = retained_before_relaxation * (1.0 - ROBUSTNESS_CORNER_RELAXATION)
    margin = retained - CONTINUOUS_REACTION_REFERENCE_N

    s = np.linspace(0.0, 1.0, 2001)
    q = _smoothstep(s)
    qp = _smoothstep_derivative(s)
    force = k * (overclosure_mm + clearance * q)
    ddelta_dy = clearance * qp / cam_travel_mm
    axial = force * ddelta_dy
    peak = float(np.max(axial))
    return AxisResult(
        axis,
        clearance,
        k,
        entry_force,
        preload_target_N,
        backup_force,
        retained,
        margin,
        peak,
    )


def spring_geometry_screen(*, k_N_per_mm: float, force_N: float) -> list[dict[str, float]]:
    rows = []
    for width, thickness in SPRING_GEOMETRY_OPTIONS:
        length = (
            2.0 * E_STUDY_MPA * width * thickness**3 / k_N_per_mm
        ) ** (1.0 / 3.0)
        stress = 1.5 * force_N * length / (width * thickness**2)
        rows.append(
            {
                "leaf_width_mm": width,
                "leaf_thickness_mm": thickness,
                "two_leaf_transverse_envelope_seed_mm": 2.0 * width + LEAF_PAIR_GAP_MM,
                "required_effective_leaf_length_mm": length,
                "linear_fixed_guided_root_stress_proxy_MPa": stress,
            }
        )
    return rows


def candidate(
    preload_target_N: float,
    overclosure_mm: float,
    cam_travel_mm: float,
) -> dict[str, object]:
    x = axis_result(
        axis="X",
        preload_target_N=preload_target_N,
        overclosure_mm=overclosure_mm,
        cam_travel_mm=cam_travel_mm,
    )
    z = axis_result(
        axis="Z",
        preload_target_N=preload_target_N,
        overclosure_mm=overclosure_mm,
        cam_travel_mm=cam_travel_mm,
    )
    combined_cam = x.peak_ideal_cam_axial_force_N + z.peak_ideal_cam_axial_force_N
    max_entry = max(x.entry_force_N, z.entry_force_N)
    min_margin = min(x.robustness_corner_margin_N, z.robustness_corner_margin_N)
    max_backup = max(x.backup_entry_force_N, z.backup_entry_force_N)
    return {
        "preload_target_N": preload_target_N,
        "entry_overclosure_mm": overclosure_mm,
        "cam_travel_mm": cam_travel_mm,
        "X": x.__dict__,
        "Z": z.__dict__,
        "combined_peak_ideal_cam_axial_force_N": combined_cam,
        "maximum_entry_force_N": max_entry,
        "minimum_robustness_corner_contact_margin_N": min_margin,
        "maximum_backup_entry_force_N": max_backup,
        "comparative_checks": {
            "robustness_corner_keeps_positive_contact_margin": min_margin > 0.0,
            "combined_ideal_cam_peak_below_current_detent_proxy": combined_cam < DETENT_FORCE_PROXY_N,
            "backup_still_enters_before_transient_reference": max_backup < TRANSIENT_REACTION_REFERENCE_N,
        },
    }


def doe() -> list[dict[str, object]]:
    return [
        candidate(preload, overclosure, cam)
        for preload in PRELOAD_TARGETS_N
        for overclosure in ENTRY_OVERCLOSURES_MM
        for cam in CAM_TRAVELS_MM
    ]


def selected_candidate() -> dict[str, object]:
    # The 0.40 N / 0.015 mm / 0.80 mm point is selected as the current robustness
    # seed because it preserves a small positive contact margin at the deliberately
    # hostile 0.05 mm + 20% corner while keeping entry/cam force well below the
    # current axial-detent proxy. It is not a final force or tolerance requirement.
    return candidate(0.40, 0.015, 0.80)


def build_manifest() -> dict[str, object]:
    selected = selected_candidate()
    x = selected["X"]
    z = selected["Z"]
    return {
        "schema": SCHEMA,
        "source_v6_head_parent_sha": SOURCE_V6_HEAD_PARENT_SHA,
        "architecture_screen_seeds": {
            "radial_error_mm": list(RADIAL_ERROR_SEEDS_MM),
            "relaxation_fraction": list(RELAXATION_SEEDS),
            "robustness_corner_radial_error_mm": ROBUSTNESS_CORNER_RADIAL_ERROR_MM,
            "robustness_corner_relaxation_fraction": ROBUSTNESS_CORNER_RELAXATION,
            "status": "DOE_ONLY_NOT_PROCESS_CAPABILITY_OR_AGING_CLAIM",
        },
        "selected_current_robustness_seed": selected,
        "selected_spring_geometry_screens": {
            "X": spring_geometry_screen(k_N_per_mm=x["stiffness_N_per_mm"], force_N=x["maximum_backup_entry_force_N"] if "maximum_backup_entry_force_N" in x else x["backup_entry_force_N"]),
            "Z": spring_geometry_screen(k_N_per_mm=z["stiffness_N_per_mm"], force_N=z["backup_entry_force_N"]),
        },
        "selection_reason": (
            "THE_PREVIOUS_0P30N_0P005MM_SEED_HAS_TOO_LITTLE ROBUSTNESS TO DIMENSIONAL ERROR/RELAXATION. "
            "0P40N_PRELOAD_WITH_0P015MM_ENTRY_OVERCLOSURE_AND_0P80MM_CAM_TRAVEL PRESERVES A SMALL "
            "POSITIVE CONTACT MARGIN AT THE DELIBERATELY HOSTILE STUDY CORNER WHILE KEEPING THE "
            "RADIAL TAKEUP SUBORDINATE TO THE FINAL AXIAL EVENT."
        ),
        "doe": doe(),
        "physical_validation_eligible": False,
        "physical_validation": (
            "OPEN_ACTUAL_TOLERANCE_DISTRIBUTION_SPRING_RELAXATION_GRADE_FATIGUE_FORCE_TRAVEL_FRICTION_"
            "CONTACT_PRESSURE_DAMPING_ACOUSTICS_WET_CHEMICAL_CORROSION_AND_ASSEMBLY_PROCESS"
        ),
    }


def write_manifest(path: str | Path) -> dict[str, object]:
    payload = build_manifest()
    Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


if __name__ == "__main__":
    print(json.dumps(build_manifest(), indent=2, sort_keys=True))
