from __future__ import annotations

"""Terminal event phasing study for the treatment carrier.

The user/service feel target is not achieved by stacking every compliant feature at
the same coordinate. The terminal mechanism should sequence its jobs:

FREE RAIL
-> progressive X/Z play take-up
-> X/Z preload reaches a flat full-seat land
-> one muted axial landing/detent event
-> positive rigid stop remains outside normal seating.

This study uses the current nominal geometry seeds only. It does not predict physical
insertion force or sound because friction, real spring force, damping and material
behavior remain unmeasured.
"""

import json
from pathlib import Path

from masck_one.structural_frame_carrier_detent import NOMINAL_COUNTERFACE_GAP_MM
from masck_one.structural_frame_carrier_landing import NOMINAL_LANDING_GAP_MM
from masck_one.treatment_carrier_counterpart import (
    RIGID_END_STOP_GAP_MM,
    RIGID_END_STOP_PROBE_MM,
    SOFT_LANDING_PROBE_MM,
)
from masck_one.treatment_terminal_datum_preload import (
    CAM_TRANSITION_TRAVEL_MM,
    FULL_SEAT_LAND_MM,
)
from studies.treatment_parallel_preload_flexure import (
    CAM_TRAVEL_MM,
    build_axis,
    force_profile,
)

SCHEMA = "MASCK_ONE_TREATMENT_TERMINAL_EVENT_PHASING_V1"
SOURCE_V6_PARENT_SHA = "eaaf2d6bef26ab643e3a892dd4699f68dce3412f"
CURRENT_AXIAL_DETENT_FORCE_PROXY_N = 0.26


def peak_ideal_cam_axial_force_N(axis: str) -> float:
    row = build_axis(axis)
    clearance = row.running_clearance_mm
    peak = 0.0
    profile = force_profile(axis, 401)
    for item in profile:
        s = item["normalized_travel"]
        # derivative of 3s^2-2s^3
        qprime = 6.0 * s * (1.0 - s)
        ddelta_dy = clearance * qprime / CAM_TRAVEL_MM
        peak = max(peak, item["preload_force_N"] * ddelta_dy)
    return peak


def build_manifest() -> dict[str, object]:
    axial_event_gap = max(NOMINAL_LANDING_GAP_MM, NOMINAL_COUNTERFACE_GAP_MM)
    radial_flat_lead = FULL_SEAT_LAND_MM - axial_event_gap
    x_cam = peak_ideal_cam_axial_force_N("X")
    z_cam = peak_ideal_cam_axial_force_N("Z")
    combined = x_cam + z_cam
    return {
        "schema": SCHEMA,
        "source_v6_parent_sha": SOURCE_V6_PARENT_SHA,
        "sequence": [
            "LOW_DRAG_PARALLEL_RAIL_APPROACH",
            "X_Z_ZERO_SLOPE_CAM_ACQUISITION",
            "X_Z_FULL_PRELOAD_ON_FLAT_LAND",
            "MUTED_AXIAL_LANDING_AND_DETENT_EVENT",
            "RIGID_END_STOP_RESERVED_FOR_OVERTRAVEL",
        ],
        "geometry_seeds_mm": {
            "cam_transition_travel": CAM_TRANSITION_TRAVEL_MM,
            "cam_full_seat_land": FULL_SEAT_LAND_MM,
            "landing_nominal_gap": NOMINAL_LANDING_GAP_MM,
            "detent_nominal_counterface_gap": NOMINAL_COUNTERFACE_GAP_MM,
            "radial_full_preload_lead_before_axial_event": radial_flat_lead,
            "rigid_end_stop_gap": RIGID_END_STOP_GAP_MM,
            "soft_landing_probe": SOFT_LANDING_PROBE_MM,
            "rigid_end_stop_probe": RIGID_END_STOP_PROBE_MM,
        },
        "ideal_frictionless_cam_force_proxies_N": {
            "X_peak": x_cam,
            "Z_peak": z_cam,
            "two_axis_noncoincident_sum_upper_bound": combined,
            "current_axial_detent_force_proxy": CURRENT_AXIAL_DETENT_FORCE_PROXY_N,
        },
        "digital_phasing_checks": {
            "radial_preload_has_flat_land_before_axial_event": radial_flat_lead > 0.0,
            "cam_takeup_is_smaller_than_current_detent_proxy": combined < CURRENT_AXIAL_DETENT_FORCE_PROXY_N,
            "rigid_stop_is_not_the_first_compliant_event_in_probe_hierarchy": RIGID_END_STOP_PROBE_MM > SOFT_LANDING_PROBE_MM,
        },
        "buttery_intent": (
            "REMOVE_RADIAL_PLAY_BEFORE_THE_FINAL_CAPTURE_EVENT_SO_THE_USER_OR_SERVICE_TECH_DOES_NOT_"
            "FEEL_TWO_COUPLED_SNAPS; KEEP_THE_HARD_STOP_OUT_OF_NORMAL_SEATING"
        ),
        "physical_validation_eligible": False,
        "physical_validation": (
            "OPEN_REAL_FORCE_TRAVEL_FRICTION_DETENT_FORCE_LANDING_STIFFNESS_DAMPING_ACOUSTICS_"
            "TOLERANCE_WEAR_WET_CONTAMINATION_AND_SUBJECTIVE_FEEL"
        ),
    }


def write_manifest(path: str | Path) -> dict[str, object]:
    payload = build_manifest()
    Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


if __name__ == "__main__":
    print(json.dumps(build_manifest(), indent=2, sort_keys=True))
