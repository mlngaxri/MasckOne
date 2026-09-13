from __future__ import annotations

from masck_one import retention_quick_release_tactile as v1
from masck_one.retention_quick_release_tactile_v2 import (
    CAM_PROFILE_ID,
    SCHEMA,
    SUPERSEDES_SCHEMA,
    _cam_control_points,
    _exact_smooth_cam_tooth,
    build_retention_quick_release_tactile_v2,
)


def test_v2_exact_bezier_supersedes_faceted_v1_without_parallel_owner_truth():
    candidate = build_retention_quick_release_tactile_v2()
    manifest = candidate.manifest()

    assert manifest["schema"] == SCHEMA
    assert manifest["supersedes_schema"] == SUPERSEDES_SCHEMA == v1.SCHEMA
    assert manifest["owner_branch"] == v1.OWNER_BRANCH
    assert manifest["detent"]["cam_profile"] == CAM_PROFILE_ID
    assert manifest["detent"]["faceted_contact_profile"] is False
    assert manifest["physical_validation_eligible"] is False


def test_exact_bezier_is_one_valid_manufactured_tooth_and_keeps_package_endpoints():
    tooth = _exact_smooth_cam_tooth(False).val()
    controls = _cam_control_points(False)

    assert tooth.isValid()
    assert len(tooth.Solids()) == 1
    assert tooth.Volume() > 0.0
    assert sum(edge.geomType() == "BEZIER" for edge in tooth.Edges()) >= 2
    assert controls[0] == (v1.DETENT_TOOTH_X_MIN_MM, v1.DETENT_TOOTH_BOTTOM_LEFT_Z_MM)
    assert controls[-1] == (v1.DETENT_TOOTH_X_MAX_MM, v1.DETENT_TOOTH_BOTTOM_RIGHT_Z_MM)


def test_bezier_control_multiplicity_proves_zero_entry_exit_slope_and_curvature():
    controls = _cam_control_points(False)
    z = [point[1] for point in controls]

    # Degree-5 Bezier endpoint first and second derivatives depend only on the first
    # three / last three controls. Repeated ordinates therefore give dz/dt=d2z/dt2=0
    # while X advances monotonically, i.e. zero cam slope and curvature at both ends.
    assert z[0] == z[1] == z[2]
    assert z[3] == z[4] == z[5]
    assert all(controls[index + 1][0] > controls[index][0] for index in range(5))


def test_v2_preserves_low_play_guidance_damping_and_independent_hard_stops():
    mechanism = build_retention_quick_release_tactile_v2().mechanism

    assert 0.0 < mechanism.rail_radial_clearance_mm <= v1.MAX_SPOOL_RAIL_RADIAL_CLEARANCE_MM
    assert 0.0 < mechanism.anti_rotation_side_clearance_mm <= v1.MAX_ANTI_ROTATION_SIDE_CLEARANCE_MM
    assert mechanism.flexure_free_slider_interference_mm3 > 0.0
    assert mechanism.flexure_installed_slider_interference_mm3 == 0.0
    assert mechanism.inboard_bumper_free_interference_mm3 > 0.0
    assert mechanism.outboard_bumper_free_interference_mm3 > 0.0
    assert mechanism.inboard_bumper_installed_interference_mm3 == 0.0
    assert mechanism.outboard_bumper_installed_interference_mm3 == 0.0
    assert mechanism.rigid_inboard_overtravel_intersection_mm3 > 0.0
    assert mechanism.rigid_outboard_overtravel_intersection_mm3 > 0.0
