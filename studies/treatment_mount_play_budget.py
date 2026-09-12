"""Geometric free-play audit for the current treatment mount candidate.

This is deliberately a geometry/architecture screen, not a tactile-quality claim.
It distinguishes collision-free clearance from an actually preloaded low-rattle mount.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from masck_one.structural_frame_carrier_detent import NOMINAL_COUNTERFACE_GAP_MM
from masck_one.structural_frame_carrier_landing import NOMINAL_LANDING_GAP_MM
from masck_one.structural_frame_carrier_preload import NOMINAL_LATERAL_GAP_MM
from masck_one.structural_frame_carrier_interfaces import RAIL_LENGTH_MM
from masck_one.treatment_carrier_counterpart import (
    CROWN_SIDE_CLEARANCE_MM,
    CROWN_TOP_CLEARANCE_MM,
    CROWN_UNDERSIDE_CLEARANCE_MM,
    RIGID_END_STOP_GAP_MM,
    ROOT_SIDE_CLEARANCE_MM,
)
from masck_one.treatment_mounted_four_zone import (
    SHOULDER_HEIGHT_MM,
    YOKE_X_CLEARANCE_MM,
    YOKE_Z_CLEARANCE_MM,
)

SCHEMA = "MASCK_ONE_TREATMENT_MOUNT_FREE_PLAY_AUDIT_V1"


def _angle_deg(total_clearance_mm: float, guide_span_mm: float) -> float:
    if total_clearance_mm < 0.0 or guide_span_mm <= 0.0:
        raise ValueError("free-play audit requires nonnegative clearance and positive guide span")
    return math.degrees(math.atan2(total_clearance_mm, guide_span_mm))


def build_report() -> dict[str, object]:
    yoke_total_x = 2.0 * YOKE_X_CLEARANCE_MM
    yoke_total_z = 2.0 * YOKE_Z_CLEARANCE_MM
    rail_root_total_x = 2.0 * ROOT_SIDE_CLEARANCE_MM
    rail_crown_total_x = 2.0 * CROWN_SIDE_CLEARANCE_MM
    rail_crown_total_z = CROWN_UNDERSIDE_CLEARANCE_MM + CROWN_TOP_CLEARANCE_MM

    # These angular values are uncoupled geometric upper-bound indicators only.
    # The complete carrier has multiple contacts, so they are not predictions of
    # actual assembled rock. They exist to expose how much free travel is present
    # before nominal elastic preload is demonstrated.
    return {
        "schema": SCHEMA,
        "clearance_seeds_mm": {
            "shoulder_yoke_total_x": yoke_total_x,
            "shoulder_yoke_total_z": yoke_total_z,
            "rail_shoe_root_total_x": rail_root_total_x,
            "rail_shoe_crown_total_x": rail_crown_total_x,
            "rail_shoe_crown_total_z": rail_crown_total_z,
            "cell6_preload_leaf_nominal_gap": NOMINAL_LATERAL_GAP_MM,
            "cell6_landing_nominal_gap": NOMINAL_LANDING_GAP_MM,
            "cell6_detent_nominal_gap": NOMINAL_COUNTERFACE_GAP_MM,
            "treatment_rigid_end_stop_gap": RIGID_END_STOP_GAP_MM,
        },
        "uncoupled_geometric_rock_indicators_deg": {
            "shoulder_yoke_x_clearance_over_shoulder_y_span": _angle_deg(
                yoke_total_x, SHOULDER_HEIGHT_MM
            ),
            "rail_root_x_clearance_over_rail_length": _angle_deg(
                rail_root_total_x, RAIL_LENGTH_MM
            ),
            "rail_crown_x_clearance_over_rail_length": _angle_deg(
                rail_crown_total_x, RAIL_LENGTH_MM
            ),
        },
        "nominal_elastic_preload_demonstrated": False,
        "reason": (
            "CELL6_PRELOAD_LANDING_AND_DETENT_FEATURES_ARE_AUTHORED_WITH_POSITIVE_NOMINAL_GAPS; "
            "THE_TREATMENT_YOKE_IS_BILATERALLY_CLEARANCED. COLLISION_FREE NOMINAL CAD THEREFORE "
            "DOES_NOT YET DEMONSTRATE A ZERO-DEAD-ZONE LOW-RATTLE WORKING REACTION PATH."
        ),
        "required_next_architecture": (
            "ONE_SIDED_RIGID_KINEMATIC_DATUM_PLUS_OPPOSING_COMPLIANT_BIAS_OR_EQUIVALENT "
            "THAT REMOVES WORKING_REACTION_BACKLASH WITHOUT ZERO_CLEARANCE_BINDING"
        ),
        "evidence_firewall": (
            "GEOMETRIC_CLEARANCE_AUDIT_ONLY; INSERTION_FORCE_FRICTION_PRELOAD_STIFFNESS_WEAR_"
            "ACOUSTICS_AND_PERCEIVED_BUTTERY_FEEL_REQUIRE_PHYSICAL_VALIDATION"
        ),
    }


def write_report(path: Path = Path("studies/treatment_mount_play_budget_results.json")) -> dict[str, object]:
    report = build_report()
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    print(json.dumps(write_report(), indent=2, sort_keys=True))
