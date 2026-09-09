from __future__ import annotations

"""C2 terminal seating profile and robustness update for the treatment carrier.

The previous V6 preload cassette was directionally strong but still carried three
fragile seeds: 0.30 N seated preload, 0.005 mm entry overclosure and a 0.65 mm cubic
smoothstep cam. A later robustness DOE showed that dimensional error plus preload
relaxation can consume nearly all of the no-gap margin at those settings.

This successor keeps the same mechanical separation of functions:

- long rail = low-drag acquisition only;
- terminal cams = progressively remove X/Z play;
- spring cassettes = maintain contact only;
- rigid master datums = normal 40 Hz working reaction;
- lossy backup then rigid stop = abnormal reverse travel;
- axial landing/detent = one muted final seating event.

The current digital candidate intentionally trades a little more radial spring preload
for materially better robustness and a longer, C2-smooth terminal take-up:

- 0.40 N seated preload per X/Z axis;
- 0.030 mm entry overclosure;
- 0.95 mm quintic smootherstep cam travel;
- X cam starts/finishes 0.16 mm before Z, reducing coincident cam-force peaking;
- two 0.80 x 0.15 mm spring leaves per axis, length tuned separately for X/Z.

All values are architecture-study seeds. They are not production tolerances, measured
forces, selected spring grade, acoustic evidence or human-perception claims.
"""

from dataclasses import dataclass
import json
import math
from pathlib import Path

SCHEMA = "MASCK_ONE_TREATMENT_BUTTERY_TERMINAL_PROFILE_V2"
SOURCE_PRELOAD_ROBUSTNESS_PARENT_SHA = "d63fe0f53d69ea7fd359b28589ba270e9276df3d"

CONTINUOUS_REACTION_REFERENCE_N = 0.20
TRANSIENT_REACTION_REFERENCE_N = 0.60
CURRENT_AXIAL_DETENT_FORCE_PROXY_N = 0.26

PRELOAD_TARGET_N = 0.40
ENTRY_OVERCLOSURE_MM = 0.030
CAM_TRAVEL_MM = 0.95
X_CAM_PHASE_LEAD_MM = 0.16
FULL_SEAT_LAND_MM = 0.16
AXIAL_EVENT_GAP_MM = 0.12
LOSSY_BACKUP_TRAVEL_MM = 0.04

X_CLEARANCE_MM = 0.16
Z_CLEARANCE_MM = 0.12
ROBUSTNESS_RADIAL_ERROR_MM = 0.05
ROBUSTNESS_RELAXATION_FRACTION = 0.20

E_STUDY_MPA = 190000.0
LEAF_WIDTH_MM = 0.80
LEAF_THICKNESS_MM = 0.15
LEAVES_PER_AXIS = 2
LEAF_PAIR_GAP_MM = 0.20

# Comparison point selected by the preceding coarse DOE before the stronger no-gap
# robustness / smoothness trade below was evaluated.
PREVIOUS_PRELOAD_N = 0.40
PREVIOUS_OVERCLOSURE_MM = 0.015
PREVIOUS_CAM_TRAVEL_MM = 0.80


@dataclass(frozen=True, slots=True)
class AxisDesign:
    axis: str
    running_clearance_mm: float
    target_deflection_mm: float
    stiffness_N_per_mm: float
    effective_leaf_length_mm: float
    entry_force_N: float
    seated_preload_N: float
    robustness_corner_retained_preload_N: float
    robustness_corner_contact_margin_N: float
    backup_entry_force_N: float
    backup_root_stress_proxy_MPa: float

    def manifest(self) -> dict[str, float | str]:
        return {
            "axis": self.axis,
            "running_clearance_mm": self.running_clearance_mm,
            "target_deflection_mm": self.target_deflection_mm,
            "stiffness_N_per_mm": self.stiffness_N_per_mm,
            "effective_leaf_length_mm": self.effective_leaf_length_mm,
            "entry_force_N": self.entry_force_N,
            "seated_preload_N": self.seated_preload_N,
            "robustness_corner_retained_preload_N": self.robustness_corner_retained_preload_N,
            "robustness_corner_contact_margin_N": self.robustness_corner_contact_margin_N,
            "backup_entry_force_N": self.backup_entry_force_N,
            "backup_root_stress_proxy_MPa": self.backup_root_stress_proxy_MPa,
        }


def smootherstep(s: float) -> float:
    """Quintic C2 smootherstep: q, q' and q'' are zero/flat at endpoints."""
    s = min(1.0, max(0.0, float(s)))
    return 10.0 * s**3 - 15.0 * s**4 + 6.0 * s**5


def smootherstep_derivative(s: float) -> float:
    s = min(1.0, max(0.0, float(s)))
    return 30.0 * s**2 * (1.0 - s) ** 2


def smootherstep_second_derivative(s: float) -> float:
    s = min(1.0, max(0.0, float(s)))
    return 60.0 * s - 180.0 * s**2 + 120.0 * s**3


def _clearance(axis: str) -> float:
    if axis == "X":
        return X_CLEARANCE_MM
    if axis == "Z":
        return Z_CLEARANCE_MM
    raise ValueError("axis must be X or Z")


def axis_design(axis: str) -> AxisDesign:
    clearance = _clearance(axis)
    target_deflection = clearance + ENTRY_OVERCLOSURE_MM
    stiffness = PRELOAD_TARGET_N / target_deflection
    numerator = (
        2.0
        * E_STUDY_MPA
        * LEAF_WIDTH_MM
        * LEAF_THICKNESS_MM**3
    )
    length = (numerator / stiffness) ** (1.0 / 3.0)
    entry_force = stiffness * ENTRY_OVERCLOSURE_MM
    retained_before_relaxation = PRELOAD_TARGET_N - stiffness * ROBUSTNESS_RADIAL_ERROR_MM
    retained = retained_before_relaxation * (1.0 - ROBUSTNESS_RELAXATION_FRACTION)
    margin = retained - CONTINUOUS_REACTION_REFERENCE_N
    backup_force = PRELOAD_TARGET_N + stiffness * LOSSY_BACKUP_TRAVEL_MM
    # Two fixed-guided leaves, F/2 per leaf and end moment ~F*L/4.
    stress = (
        1.5
        * backup_force
        * length
        / (LEAF_WIDTH_MM * LEAF_THICKNESS_MM**2)
    )
    return AxisDesign(
        axis,
        clearance,
        target_deflection,
        stiffness,
        length,
        entry_force,
        PRELOAD_TARGET_N,
        retained,
        margin,
        backup_force,
        stress,
    )


def previous_corner_margin_N(axis: str) -> float:
    clearance = _clearance(axis)
    stiffness = PREVIOUS_PRELOAD_N / (clearance + PREVIOUS_OVERCLOSURE_MM)
    retained = (
        PREVIOUS_PRELOAD_N - stiffness * ROBUSTNESS_RADIAL_ERROR_MM
    ) * (1.0 - ROBUSTNESS_RELAXATION_FRACTION)
    return retained - CONTINUOUS_REACTION_REFERENCE_N


def _axis_axial_cam_force_N(*, axis: str, y_mm: float, start_y_mm: float) -> float:
    row = axis_design(axis)
    s = (y_mm - start_y_mm) / CAM_TRAVEL_MM
    if s < 0.0 or s > 1.0:
        return 0.0
    radial_deflection = ENTRY_OVERCLOSURE_MM + row.running_clearance_mm * smootherstep(s)
    preload_force = row.stiffness_N_per_mm * radial_deflection
    radial_slope = (
        row.running_clearance_mm
        * smootherstep_derivative(s)
        / CAM_TRAVEL_MM
    )
    return preload_force * radial_slope


def phased_cam_force_screen(samples: int = 4001) -> dict[str, object]:
    if samples < 101:
        raise ValueError("at least 101 samples required")
    y0 = -X_CAM_PHASE_LEAD_MM
    y1 = CAM_TRAVEL_MM
    peak = -1.0
    peak_y = 0.0
    peak_x = 0.0
    peak_z = 0.0
    rows: list[dict[str, float]] = []
    for i in range(samples):
        y = y0 + (y1 - y0) * i / (samples - 1)
        x_force = _axis_axial_cam_force_N(axis="X", y_mm=y, start_y_mm=-X_CAM_PHASE_LEAD_MM)
        z_force = _axis_axial_cam_force_N(axis="Z", y_mm=y, start_y_mm=0.0)
        total = x_force + z_force
        if x_force > peak_x:
            peak_x = x_force
        if z_force > peak_z:
            peak_z = z_force
        if total > peak:
            peak = total
            peak_y = y
        if i % max(1, samples // 40) == 0 or i == samples - 1:
            rows.append(
                {
                    "axial_coordinate_mm": y,
                    "X_ideal_axial_cam_force_N": x_force,
                    "Z_ideal_axial_cam_force_N": z_force,
                    "combined_ideal_axial_cam_force_N": total,
                }
            )
    return {
        "X_phase_lead_mm": X_CAM_PHASE_LEAD_MM,
        "X_peak_ideal_axial_cam_force_N": peak_x,
        "Z_peak_ideal_axial_cam_force_N": peak_z,
        "combined_peak_ideal_axial_cam_force_N": peak,
        "combined_peak_coordinate_mm": peak_y,
        "current_axial_detent_force_proxy_N": CURRENT_AXIAL_DETENT_FORCE_PROXY_N,
        "sampled_profile": rows,
    }


def event_phasing_screen() -> dict[str, float | bool]:
    z_full_preload_lead = FULL_SEAT_LAND_MM - AXIAL_EVENT_GAP_MM
    x_full_preload_lead = z_full_preload_lead + X_CAM_PHASE_LEAD_MM
    return {
        "Z_full_preload_lead_before_axial_event_mm": z_full_preload_lead,
        "X_full_preload_lead_before_axial_event_mm": x_full_preload_lead,
        "both_radial_axes_fully_preloaded_before_axial_event": (
            min(x_full_preload_lead, z_full_preload_lead) > 0.0
        ),
        "X_finishes_before_Z": X_CAM_PHASE_LEAD_MM > 0.0,
    }


def build_manifest() -> dict[str, object]:
    x = axis_design("X")
    z = axis_design("Z")
    cam = phased_cam_force_screen()
    phasing = event_phasing_screen()
    return {
        "schema": SCHEMA,
        "source_preload_robustness_parent_sha": SOURCE_PRELOAD_ROBUSTNESS_PARENT_SHA,
        "selected_profile": {
            "preload_target_N_per_axis": PRELOAD_TARGET_N,
            "entry_overclosure_mm": ENTRY_OVERCLOSURE_MM,
            "cam_travel_mm": CAM_TRAVEL_MM,
            "cam_profile": "QUINTIC_C2_SMOOTHERSTEP",
            "X_phase_lead_mm": X_CAM_PHASE_LEAD_MM,
            "full_seat_land_mm": FULL_SEAT_LAND_MM,
            "axial_event_gap_mm": AXIAL_EVENT_GAP_MM,
        },
        "spring_study": {
            "elastic_modulus_study_MPa": E_STUDY_MPA,
            "leaf_width_mm": LEAF_WIDTH_MM,
            "leaf_thickness_mm": LEAF_THICKNESS_MM,
            "leaves_per_axis": LEAVES_PER_AXIS,
            "leaf_pair_gap_mm": LEAF_PAIR_GAP_MM,
            "status": "ANALYTICAL_GEOMETRY_SEED_ONLY_ALLOY_AND_FATIGUE_OPEN",
        },
        "axes": {"X": x.manifest(), "Z": z.manifest()},
        "robustness_comparison": {
            "corner_radial_error_mm": ROBUSTNESS_RADIAL_ERROR_MM,
            "corner_relaxation_fraction": ROBUSTNESS_RELAXATION_FRACTION,
            "previous_0p40N_0p015mm_X_margin_N": previous_corner_margin_N("X"),
            "previous_0p40N_0p015mm_Z_margin_N": previous_corner_margin_N("Z"),
            "selected_X_margin_N": x.robustness_corner_contact_margin_N,
            "selected_Z_margin_N": z.robustness_corner_contact_margin_N,
        },
        "C2_endpoint_checks": {
            "qprime_0": smootherstep_derivative(0.0),
            "qprime_1": smootherstep_derivative(1.0),
            "qsecond_0": smootherstep_second_derivative(0.0),
            "qsecond_1": smootherstep_second_derivative(1.0),
        },
        "phased_cam_force_screen": cam,
        "event_phasing": phasing,
        "digital_checks": {
            "X_robustness_corner_margin_above_0p03N": x.robustness_corner_contact_margin_N > 0.03,
            "Z_robustness_corner_margin_above_0p01N": z.robustness_corner_contact_margin_N > 0.01,
            "both_backup_entries_below_transient_reference": max(
                x.backup_entry_force_N, z.backup_entry_force_N
            ) < TRANSIENT_REACTION_REFERENCE_N,
            "combined_cam_peak_below_0p15N": cam["combined_peak_ideal_axial_cam_force_N"] < 0.15,
            "combined_cam_peak_subordinate_to_axial_event": cam["combined_peak_ideal_axial_cam_force_N"] < CURRENT_AXIAL_DETENT_FORCE_PROXY_N,
            "C2_zero_slope_and_curvature_at_both_ends": all(
                abs(v) < 1e-12
                for v in (
                    smootherstep_derivative(0.0),
                    smootherstep_derivative(1.0),
                    smootherstep_second_derivative(0.0),
                    smootherstep_second_derivative(1.0),
                )
            ),
            "both_radial_axes_preloaded_before_final_axial_event": phasing[
                "both_radial_axes_fully_preloaded_before_axial_event"
            ],
        },
        "selected_buttery_sequence": (
            "LOW_DRAG_RAIL -> X_C2_CAM_STARTS_EARLY -> Z_C2_CAM_JOINS -> "
            "BOTH_AXES_SETTLE_ON_FLAT_PRELOAD_LANDS -> ONE_MUTED_AXIAL_EVENT -> "
            "POSITIVE_Y_SEAT; NORMAL_40HZ_REACTION_STAYS_ON_RIGID_DATUMS"
        ),
        "reason_for_change": (
            "THE COARSER 0P40N_0P015MM_0P80MM SEED LEFT ONLY ABOUT 0P0015N Z-AXIS "
            "CONTACT MARGIN AT THE DELIBERATELY HOSTILE 0P05MM_PLUS_20PCT CORNER. "
            "THE 0P030MM OVERCLOSURE REDUCES SPRING STIFFNESS SENSITIVITY, THE 0P95MM C2 CAM "
            "SPREADS TAKEUP OVER MORE TRAVEL, AND X/Z PHASING REDUCES COINCIDENT AXIAL PEAK."
        ),
        "physical_validation_eligible": False,
        "physical_validation": (
            "OPEN_REAL_TOLERANCE_DISTRIBUTION_SPRING_RELAXATION_ALLOY_FORMING_RESIDUAL_STRESS_"
            "NONLINEAR_FEA_FATIGUE_CAM_FRICTION_CONTACT_PRESSURE_WEAR_DAMPING_ACOUSTICS_"
            "WET_CHEMICAL_CORROSION_ASSEMBLY_FORCE_TRAVEL_AND_SUBJECTIVE_FEEL"
        ),
    }


def write_manifest(path: str | Path) -> dict[str, object]:
    payload = build_manifest()
    Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


if __name__ == "__main__":
    print(json.dumps(build_manifest(), indent=2, sort_keys=True))
