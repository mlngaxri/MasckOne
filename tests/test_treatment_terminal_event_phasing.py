from __future__ import annotations

import math

from studies.treatment_terminal_event_phasing import (
    CURRENT_AXIAL_DETENT_FORCE_PROXY_N,
    build_manifest,
)


def test_radial_play_is_removed_before_final_axial_capture_event():
    manifest = build_manifest()
    geometry = manifest["geometry_seeds_mm"]
    assert geometry["radial_full_preload_lead_before_axial_event"] > 0.0
    assert math.isclose(
        geometry["radial_full_preload_lead_before_axial_event"],
        0.04,
        abs_tol=1e-12,
    )
    assert manifest["digital_phasing_checks"]["radial_preload_has_flat_land_before_axial_event"] is True


def test_radial_cam_takeup_is_subordinate_to_one_final_capture_event():
    manifest = build_manifest()
    forces = manifest["ideal_frictionless_cam_force_proxies_N"]
    assert forces["X_peak"] > forces["Z_peak"] > 0.0
    assert forces["two_axis_noncoincident_sum_upper_bound"] < CURRENT_AXIAL_DETENT_FORCE_PROXY_N
    assert manifest["digital_phasing_checks"]["cam_takeup_is_smaller_than_current_detent_proxy"] is True


def test_hard_stop_remains_outside_normal_compliant_seating_hierarchy():
    manifest = build_manifest()
    geometry = manifest["geometry_seeds_mm"]
    assert geometry["rigid_end_stop_probe"] > geometry["soft_landing_probe"]
    assert manifest["digital_phasing_checks"]["rigid_stop_is_not_the_first_compliant_event_in_probe_hierarchy"] is True


def test_event_phasing_is_design_intent_not_physical_feel_claim():
    manifest = build_manifest()
    assert manifest["sequence"] == [
        "LOW_DRAG_PARALLEL_RAIL_APPROACH",
        "X_Z_ZERO_SLOPE_CAM_ACQUISITION",
        "X_Z_FULL_PRELOAD_ON_FLAT_LAND",
        "MUTED_AXIAL_LANDING_AND_DETENT_EVENT",
        "RIGID_END_STOP_RESERVED_FOR_OVERTRAVEL",
    ]
    assert manifest["physical_validation_eligible"] is False
    assert manifest["physical_validation"].startswith("OPEN_")
