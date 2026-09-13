from __future__ import annotations

"""Tolerance/retention closure study for the treatment terminal seat.

This study intentionally attacks two hidden failure modes in the V3 four-face rigid
terminal taper:

1. independent radial manufacturing errors map into much larger axial contact-position
   errors through a shallow taper, so four perfectly rigid faces are over-constrained;
2. the same taper angle controls both self-release friction margin and axial back-drive,
   leaving a very narrow feasible window if the current Cell 6 detent is asked to do
   both precision seating and overload retention.

The result is an architecture decision, not a production tolerance claim: V1 should
use independently equalizing radial datum shoes for acquisition/preload and a separate
positive axial capture path for overload retention. Working massage reaction must
bottom into rigid compressive datums rather than remain on compliant flexures.
"""

import json
import math
from pathlib import Path

from masck_one.treatment_terminal_kinematic_seat import (
    RUNNING_X_CLEARANCE_MM,
    RUNNING_Z_CLEARANCE_MM,
    TAPER_OVERTRAVEL_EXTENSION_MM,
    TRANSIENT_REACTION_REFERENCE_N,
    X_TAPER_SPAN_MM,
    Z_TAPER_SPAN_MM,
    detent_linear_proxy,
)

SCHEMA = "MASCK_ONE_TREATMENT_TERMINAL_SEAT_TOLERANCE_V1"
SOURCE_CELL6_HEAD_SHA = "fcccde02b31cc1c4e01136630d92e550e4e09a11"
SOURCE_TREATMENT_V3_HEAD_SHA = "16d62d744dc8e7a4090f9a2d788bea016542d959"

# DOE seeds only. They are deliberately not called production tolerances.
RADIAL_ERROR_STUDY_MM = (0.02, 0.03, 0.05)
FRICTION_COEFFICIENT_STUDY = (0.20, 0.25, 0.30, 0.35)

# A separate positive axial capture may allow a tiny transient withdrawal before a
# rigid keeper takes load. This is only a kinematic sensitivity seed, not a selected
# production gap or audible-rattle claim.
AXIAL_CAPTURE_DEADBAND_STUDY_MM = (0.02, 0.04, 0.06)


def _slope_x() -> float:
    return RUNNING_X_CLEARANCE_MM / X_TAPER_SPAN_MM


def _slope_z() -> float:
    return RUNNING_Z_CLEARANCE_MM / Z_TAPER_SPAN_MM


def axial_contact_shift_mm(radial_error_mm: float, taper_slope: float) -> float:
    if taper_slope <= 0.0:
        raise ValueError("taper slope must be positive")
    return radial_error_mm / taper_slope


def rigid_four_face_tolerance_screen() -> dict[str, object]:
    sx, sz = _slope_x(), _slope_z()
    rows: list[dict[str, float | bool]] = []
    for error in RADIAL_ERROR_STUDY_MM:
        # Independent +/- radial error can put one face early and another late by
        # twice the one-sided contact shift. The smallest taper slope is worst.
        worst_spread = 2.0 * error / min(sx, sz)
        rows.append(
            {
                "radial_error_seed_mm": error,
                "x_one_sided_axial_contact_shift_mm": axial_contact_shift_mm(error, sx),
                "z_one_sided_axial_contact_shift_mm": axial_contact_shift_mm(error, sz),
                "worst_independent_four_face_contact_spread_mm": worst_spread,
                "current_overtravel_wedge_mm": TAPER_OVERTRAVEL_EXTENSION_MM,
                "current_overtravel_wedge_covers_spread": worst_spread <= TAPER_OVERTRAVEL_EXTENSION_MM,
            }
        )
    return {
        "x_taper_slope": sx,
        "z_taper_slope": sz,
        "rows": rows,
        "decision": (
            "REJECT_FULLY_RIGID_FOUR_FACE_MATCHED_CONTACT_AS_PRODUCTION_BASELINE; "
            "INDEPENDENT_RADIAL_EQUALIZATION_REQUIRED"
        ),
    }


def single_detent_wedge_window() -> dict[str, object]:
    retained = detent_linear_proxy()["retained_force_proxy_N"]
    # For equal X/Z taper slopes s, worst resultant transient axial back-drive is
    # F*sqrt(2)*s. This gives the largest equal slope the current linear detent proxy
    # can retain without any analytical margin.
    max_equal_slope = retained / (TRANSIENT_REACTION_REFERENCE_N * math.sqrt(2.0))
    max_equal_angle_deg = math.degrees(math.atan(max_equal_slope))
    friction_rows = []
    for mu in FRICTION_COEFFICIENT_STUDY:
        min_release_angle_deg = math.degrees(math.atan(mu))
        friction_rows.append(
            {
                "friction_coefficient_seed": mu,
                "minimum_equal_taper_slope_for_ideal_self_release": mu,
                "minimum_equal_taper_angle_deg_for_ideal_self_release": min_release_angle_deg,
                "retention_limited_max_equal_taper_slope": max_equal_slope,
                "retention_limited_max_equal_taper_angle_deg": max_equal_angle_deg,
                "feasible_slope_window": mu < max_equal_slope,
                "angle_window_deg": max(0.0, max_equal_angle_deg - min_release_angle_deg),
            }
        )
    return {
        "detent_retained_force_linear_proxy_N": retained,
        "transient_reaction_reference_N": TRANSIENT_REACTION_REFERENCE_N,
        "retention_limited_max_equal_taper_slope": max_equal_slope,
        "retention_limited_max_equal_taper_angle_deg": max_equal_angle_deg,
        "friction_rows": friction_rows,
        "decision": (
            "DO_NOT_REQUIRE_ONE_DETENT_TO_SATISFY_BOTH_SELF_RELEASE_AND_TRANSIENT_RETENTION; "
            "SEPARATE_GENTLE_SEATING_BIAS_FROM_POSITIVE_AXIAL_OVERLOAD_CAPTURE"
        ),
    }


def axial_capture_deadband_screen() -> dict[str, object]:
    sx, sz = _slope_x(), _slope_z()
    rows = []
    for deadband in AXIAL_CAPTURE_DEADBAND_STUDY_MM:
        rows.append(
            {
                "axial_capture_deadband_seed_mm": deadband,
                "x_clearance_reopened_before_hard_capture_mm": deadband * sx,
                "z_clearance_reopened_before_hard_capture_mm": deadband * sz,
            }
        )
    return {
        "rows": rows,
        "interpretation": (
            "A_HARD_CAPTURE_IS_AN_OVERLOAD_BACKSTOP_NOT_THE_NORMAL_40HZ_REACTION_PATH; "
            "NORMAL_SEATING_BIAS_MUST_KEEP_THE_TAPER/EQUALIZER_ENGAGED_WITHOUT_CYCLIC_IMPACT"
        ),
    }


def build_manifest() -> dict[str, object]:
    return {
        "schema": SCHEMA,
        "source_cell6_head_sha": SOURCE_CELL6_HEAD_SHA,
        "source_treatment_v3_head_sha": SOURCE_TREATMENT_V3_HEAD_SHA,
        "rigid_four_face_tolerance_screen": rigid_four_face_tolerance_screen(),
        "single_detent_wedge_window": single_detent_wedge_window(),
        "axial_capture_deadband_screen": axial_capture_deadband_screen(),
        "selected_architecture_direction": (
            "LOW_DRAG_PARALLEL_APPROACH -> INDEPENDENT_RADIAL_EQUALIZATION_SHOES -> "
            "PROGRESSIVE_TERMINAL_WEDGE_SEATING -> RIGID_COMPRESSIVE_DATUM_BOTTOMING -> "
            "GENTLE_AXIAL_SEATING_BIAS -> SEPARATE_POSITIVE_AXIAL_OVERLOAD_CAPTURE"
        ),
        "working_reaction_rule": (
            "40HZ_WORKING_REACTION_MUST_NOT_CYCLE_A_LOOSE_GAP_OR_DEPEND_ON_DETENT_BEAM_BENDING; "
            "COMPLIANT_ELEMENTS_ACQUIRE/PRELOAD/DAMP_AND_RIGID_DATUMS_CARRY_WORKING_LOAD"
        ),
        "physical_validation_eligible": False,
        "physical_validation": (
            "OPEN_TOLERANCE_STACK_FRICTION_INSERTION_RELEASE_FORCE_CONTACT_PRESSURE_WEAR_CREEP_"
            "FATIGUE_ACOUSTICS_WET_CONTAMINATION_AND_ASSEMBLY_PROCESS_CAPABILITY"
        ),
    }


def write_manifest(path: str | Path) -> dict[str, object]:
    payload = build_manifest()
    Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


if __name__ == "__main__":
    print(json.dumps(build_manifest(), indent=2, sort_keys=True))
