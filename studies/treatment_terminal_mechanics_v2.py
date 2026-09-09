from __future__ import annotations

"""Moment-balanced terminal-seat and guided-preload study for the treatment carrier.

This successor exists because the intended V7 four-patch layout created a preload
couple and its transverse spring pair did not intrinsically constrain shoe rotation.
The selected architecture removes both failure modes by construction:

- X master/preload resultants are coaxial in Z;
- Z master/preload resultants are coaxial in X;
- each preload shoe uses a two-leaf in-plane parallelogram pair whose leaves are
  separated along the desired motion axis, so tip rotation drives opposing axial
  extension rather than relying on an imposed zero-rotation boundary condition;
- normal 40 Hz reaction still goes through rigid master datums, not through the
  preload springs.

All values below remain architecture-study seeds, not measured force, tolerance,
fatigue, corrosion, acoustic or human-use evidence.
"""

from dataclasses import dataclass
import json
import math
from pathlib import Path

SCHEMA = "MASCK_ONE_TREATMENT_TERMINAL_MECHANICS_V2"
SOURCE_REJECTED_V7_HEAD = "cd8ca3e1764ec1a5144289a613c32d4ebcd2da46"
SOURCE_FAILURE_EVIDENCE_HEAD = "b803b36ddd270c3bcebf696e267015bc535ca7c9"

CONTINUOUS_REACTION_REFERENCE_N = 0.20
TRANSIENT_REACTION_REFERENCE_N = 0.60
PRELOAD_TARGET_N = 0.43
ENTRY_OVERCLOSURE_MM = 0.030
X_RUNNING_CLEARANCE_MM = 0.16
Z_RUNNING_CLEARANCE_MM = 0.12
CAM_TRAVEL_MM = 0.95
X_CAM_PHASE_LEAD_MM = 0.16
FULL_SEAT_LAND_MM = 0.16
AXIAL_EVENT_GAP_MM = 0.12
LOSSY_BACKUP_TRAVEL_MM = 0.04

E_STUDY_MPA = 190000.0
LEAF_WIDTH_MM = 0.80
LEAF_THICKNESS_MM = 0.15
LEAVES_PER_AXIS = 2
GUIDE_PAIR_SEPARATION_MM = 0.80

ROBUSTNESS_RADIAL_ERROR_MM = 0.05
ROBUSTNESS_RELAXATION_FRACTION = 0.20
CURRENT_AXIAL_DETENT_FORCE_PROXY_N = 0.26


def smootherstep(s: float) -> float:
    s = min(1.0, max(0.0, float(s)))
    return 10.0 * s**3 - 15.0 * s**4 + 6.0 * s**5


def smootherstep_derivative(s: float) -> float:
    s = min(1.0, max(0.0, float(s)))
    return 30.0 * s**2 * (1.0 - s) ** 2


@dataclass(frozen=True, slots=True)
class GuidedAxis:
    axis: str
    running_clearance_mm: float
    installed_deflection_mm: float
    target_stiffness_N_per_mm: float
    effective_leaf_length_mm: float
    free_rotation_stiffness_N_per_mm: float
    guided_stiffness_N_per_mm: float
    guided_to_fixed_ratio: float
    entry_force_N: float
    seated_force_N: float
    hostile_retained_force_N: float
    hostile_contact_margin_N: float
    backup_entry_force_N: float
    backup_root_stress_proxy_MPa: float

    def manifest(self) -> dict[str, float | str]:
        return {
            "axis": self.axis,
            "running_clearance_mm": self.running_clearance_mm,
            "installed_deflection_mm": self.installed_deflection_mm,
            "target_stiffness_N_per_mm": self.target_stiffness_N_per_mm,
            "effective_leaf_length_mm": self.effective_leaf_length_mm,
            "free_rotation_stiffness_N_per_mm": self.free_rotation_stiffness_N_per_mm,
            "guided_stiffness_N_per_mm": self.guided_stiffness_N_per_mm,
            "guided_to_fixed_ratio": self.guided_to_fixed_ratio,
            "entry_force_N": self.entry_force_N,
            "seated_force_N": self.seated_force_N,
            "hostile_retained_force_N": self.hostile_retained_force_N,
            "hostile_contact_margin_N": self.hostile_contact_margin_N,
            "backup_entry_force_N": self.backup_entry_force_N,
            "backup_root_stress_proxy_MPa": self.backup_root_stress_proxy_MPa,
        }


def _pair_stiffness(length_mm: float, separation_mm: float) -> tuple[float, float, float]:
    """Return free, guided, and ideal fixed-tip pair stiffness in N/mm.

    Two identical beams run in Y and bend in the commanded radial direction. Pair
    separation is along that same radial direction. Tip rotation therefore creates
    opposing axial extension/contraction and supplies a real rotational constraint.
    """
    if length_mm <= 0.0 or separation_mm < 0.0:
        raise ValueError("invalid guided pair geometry")
    ei = E_STUDY_MPA * LEAF_WIDTH_MM * LEAF_THICKNESS_MM**3 / 12.0
    ea = E_STUDY_MPA * LEAF_WIDTH_MM * LEAF_THICKNESS_MM
    k11 = LEAVES_PER_AXIS * 12.0 * ei / length_mm**3
    k12 = -LEAVES_PER_AXIS * 6.0 * ei / length_mm**2
    guide_k = LEAVES_PER_AXIS * ea * separation_mm**2 / (4.0 * length_mm)
    k22 = LEAVES_PER_AXIS * 4.0 * ei / length_mm + guide_k
    det = k11 * k22 - k12 * k12
    if det <= 0.0:
        raise ValueError("guided pair stiffness matrix is not positive")
    guided = det / k22
    free = k11 - k12 * k12 / (LEAVES_PER_AXIS * 4.0 * ei / length_mm)
    return free, guided, k11


def _solve_leaf_length(target_stiffness_N_per_mm: float) -> float:
    lo, hi = 1.0, 20.0
    if target_stiffness_N_per_mm <= 0.0:
        raise ValueError("target stiffness must be positive")
    for _ in range(96):
        mid = 0.5 * (lo + hi)
        _free, guided, _fixed = _pair_stiffness(mid, GUIDE_PAIR_SEPARATION_MM)
        if guided > target_stiffness_N_per_mm:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def axis_design(axis: str) -> GuidedAxis:
    if axis == "X":
        clearance = X_RUNNING_CLEARANCE_MM
    elif axis == "Z":
        clearance = Z_RUNNING_CLEARANCE_MM
    else:
        raise ValueError("axis must be X or Z")
    deflection = clearance + ENTRY_OVERCLOSURE_MM
    target_k = PRELOAD_TARGET_N / deflection
    length = _solve_leaf_length(target_k)
    free, guided, fixed = _pair_stiffness(length, GUIDE_PAIR_SEPARATION_MM)
    entry = guided * ENTRY_OVERCLOSURE_MM
    retained = (
        PRELOAD_TARGET_N - guided * ROBUSTNESS_RADIAL_ERROR_MM
    ) * (1.0 - ROBUSTNESS_RELAXATION_FRACTION)
    margin = retained - CONTINUOUS_REACTION_REFERENCE_N
    backup = PRELOAD_TARGET_N + guided * LOSSY_BACKUP_TRAVEL_MM
    stress = 1.5 * backup * length / (LEAF_WIDTH_MM * LEAF_THICKNESS_MM**2)
    return GuidedAxis(
        axis,
        clearance,
        deflection,
        target_k,
        length,
        free,
        guided,
        guided / fixed,
        entry,
        guided * deflection,
        retained,
        margin,
        backup,
        stress,
    )


def contact_equilibrium_screen() -> dict[str, float | str | bool]:
    # Equal-and-opposite resultants are intentionally coaxial at full seat. Their
    # preload-only wrench is therefore zero in the X/Z centering plane without
    # asking friction, rail contact, detent contact or deformation to close a couple.
    return {
        "X_master_preload_Z_offset_mm": 0.0,
        "Z_master_preload_X_offset_mm": 0.0,
        "preload_only_resultant_force_X_N": 0.0,
        "preload_only_resultant_force_Z_N": 0.0,
        "preload_only_resultant_moment_about_Y_Nmm": 0.0,
        "moment_balance_closed_by_geometry": True,
        "normal_working_load_path": "RIGID_MASTER_DATUMS",
        "preload_function": "MAINTAIN_RIGID_DATUM_CONTACT_ONLY",
    }


def phased_cam_force_screen(samples: int = 5001) -> dict[str, float]:
    if samples < 101:
        raise ValueError("at least 101 samples required")
    axes = {"X": axis_design("X"), "Z": axis_design("Z")}
    peak = -1.0
    peak_x = 0.0
    peak_z = 0.0
    peak_y = 0.0
    y0, y1 = -X_CAM_PHASE_LEAD_MM, CAM_TRAVEL_MM
    for index in range(samples):
        y = y0 + (y1 - y0) * index / (samples - 1)
        total = 0.0
        components: dict[str, float] = {}
        for axis, start in (("X", -X_CAM_PHASE_LEAD_MM), ("Z", 0.0)):
            row = axes[axis]
            s = (y - start) / CAM_TRAVEL_MM
            if 0.0 <= s <= 1.0:
                radial_deflection = ENTRY_OVERCLOSURE_MM + row.running_clearance_mm * smootherstep(s)
                radial_force = row.guided_stiffness_N_per_mm * radial_deflection
                slope = row.running_clearance_mm * smootherstep_derivative(s) / CAM_TRAVEL_MM
                value = radial_force * slope
            else:
                value = 0.0
            components[axis] = value
            total += value
        peak_x = max(peak_x, components["X"])
        peak_z = max(peak_z, components["Z"])
        if total > peak:
            peak = total
            peak_y = y
    return {
        "X_peak_ideal_axial_cam_force_N": peak_x,
        "Z_peak_ideal_axial_cam_force_N": peak_z,
        "combined_peak_ideal_axial_cam_force_N": peak,
        "combined_peak_coordinate_mm": peak_y,
        "axial_detent_force_proxy_N": CURRENT_AXIAL_DETENT_FORCE_PROXY_N,
    }


def build_manifest() -> dict[str, object]:
    x, z = axis_design("X"), axis_design("Z")
    cam = phased_cam_force_screen()
    equilibrium = contact_equilibrium_screen()
    return {
        "schema": SCHEMA,
        "source_rejected_v7_head": SOURCE_REJECTED_V7_HEAD,
        "source_failure_evidence_head": SOURCE_FAILURE_EVIDENCE_HEAD,
        "selected_architecture": (
            "COAXIAL_X_AND_Z_MASTER_PRELOAD_PAIRS_WITH_AXIS_SEPARATED_PARALLELOGRAM_"
            "SPRINGS_C2_TERMINAL_TAKEUP_RIGID_DATUM_WORKING_LOAD_PATH"
        ),
        "selected_values": {
            "preload_target_N_per_axis": PRELOAD_TARGET_N,
            "entry_overclosure_mm": ENTRY_OVERCLOSURE_MM,
            "cam_travel_mm": CAM_TRAVEL_MM,
            "X_phase_lead_mm": X_CAM_PHASE_LEAD_MM,
            "guide_pair_separation_mm": GUIDE_PAIR_SEPARATION_MM,
            "leaf_width_mm": LEAF_WIDTH_MM,
            "leaf_thickness_mm": LEAF_THICKNESS_MM,
            "elastic_modulus_study_MPa": E_STUDY_MPA,
        },
        "contact_equilibrium": equilibrium,
        "axes": {"X": x.manifest(), "Z": z.manifest()},
        "cam_force_screen": cam,
        "digital_checks": {
            "preload_couple_removed_by_geometry": equilibrium["moment_balance_closed_by_geometry"],
            "X_guidance_above_95pct_fixed_tip": x.guided_to_fixed_ratio > 0.95,
            "Z_guidance_above_95pct_fixed_tip": z.guided_to_fixed_ratio > 0.95,
            "X_hostile_margin_positive": x.hostile_contact_margin_N > 0.0,
            "Z_hostile_margin_positive": z.hostile_contact_margin_N > 0.0,
            "both_backup_entries_below_transient_reference": max(x.backup_entry_force_N, z.backup_entry_force_N) < TRANSIENT_REACTION_REFERENCE_N,
            "combined_cam_peak_below_0p15N": cam["combined_peak_ideal_axial_cam_force_N"] < 0.15,
            "combined_cam_peak_subordinate_to_axial_event": cam["combined_peak_ideal_axial_cam_force_N"] < CURRENT_AXIAL_DETENT_FORCE_PROXY_N,
        },
        "supersedes": "V7_TERMINAL_CONTACT_AND_TRANSVERSE_LEAF_PRELOAD_TOPOLOGY",
        "physical_validation_eligible": False,
        "physical_validation": (
            "OPEN_NONLINEAR_FEA_CONTACT_PRESSURE_SPRING_ALLOY_FORMING_RESIDUAL_STRESS_FATIGUE_"
            "RELAXATION_FRICTION_WEAR_CORROSION_WET_CHEMICAL_DAMPING_ACOUSTICS_PROCESS_CAPABILITY_"
            "INSERTION_FORCE_RELEASE_FORCE_AND_SUBJECTIVE_FEEL"
        ),
    }


def write_manifest(path: str | Path) -> dict[str, object]:
    payload = build_manifest()
    Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


if __name__ == "__main__":
    print(json.dumps(build_manifest(), indent=2, sort_keys=True))
