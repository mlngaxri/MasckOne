from __future__ import annotations

import math

import pytest

from masck_one.anatomy import build_facial_reference
from masck_one.authority import load_authority
from masck_one.facial_surface import build_planar_development_surface
from masck_one.protected_volumes import build_protected_volumes
from masck_one.spatial import Point3
from masck_one.worn_pose import (
    WornPose,
    WornPoseError,
    WornPoseLimits,
    generate_hard_envelope_regression_set,
    posed_zone_bounds,
    protected_zone_boundary_points,
)


def test_limits_come_directly_from_authority_and_z_is_not_invented():
    authority = load_authority()
    limits = WornPoseLimits.from_authority(authority)

    assert limits.translation_radial_max_mm == 5.0
    assert limits.rotation_max_deg == 4.0
    assert limits.z_translation_status == "NOT_DEFINED_BY_CURRENT_AUTHORITY_FIXED_ZERO"


def test_default_regression_set_has_expected_deterministic_459_states():
    regression = generate_hard_envelope_regression_set(load_authority())

    # 1 center + 16 radial boundary translations, times 3^3 rotation states.
    assert regression.pose_count == 17 * 27 == 459
    assert regression.radial_direction_count == 16
    assert regression.maximum_sampled_radial_translation_mm == pytest.approx(5.0, abs=1e-12)
    assert regression.maximum_sampled_absolute_rotation_deg == pytest.approx(4.0)
    assert regression.poses[regression.identity_pose_index] == WornPose(0.0, 0.0, 0.0, 0.0, 0.0)


def test_regression_generation_is_bitwise_order_deterministic_at_signature_level():
    a = generate_hard_envelope_regression_set(load_authority())
    b = generate_hard_envelope_regression_set(load_authority())

    assert a.sha256 == b.sha256
    assert [pose.signature_payload() for pose in a.poses] == [pose.signature_payload() for pose in b.poses]


def test_every_pose_respects_radial_and_rotation_limits():
    regression = generate_hard_envelope_regression_set(load_authority())
    for pose in regression.poses:
        pose.validate_against(regression.limits)
        assert pose.translation_radial_mm <= 5.0 + 1e-10
        assert pose.translation_z_mm == 0.0
        assert max(abs(pose.roll_x_deg), abs(pose.pitch_y_deg), abs(pose.yaw_z_deg)) <= 4.0


def test_translation_beyond_radial_limit_is_rejected_even_if_each_axis_is_under_limit():
    limits = WornPoseLimits(5.0, 4.0)
    pose = WornPose(4.0, 4.0, 0.0, 0.0, 0.0)
    assert pose.translation_x_mm < 5.0 and pose.translation_y_mm < 5.0
    with pytest.raises(WornPoseError, match="exceeds radial limit"):
        pose.validate_against(limits)


def test_rotation_beyond_limit_is_rejected_per_axis():
    limits = WornPoseLimits(5.0, 4.0)
    with pytest.raises(WornPoseError, match="pitch_y_deg"):
        WornPose(0.0, 0.0, 0.0, 4.001, 0.0).validate_against(limits)


def test_identity_pose_is_exact_for_points():
    point = Point3(31.5, 35.0, 12.0)
    assert WornPose(0, 0, 0, 0, 0).apply_point(point) == point


def test_positive_xy_translation_has_explicit_reference_to_device_semantics():
    point = Point3(10.0, 20.0, 3.0)
    posed = WornPose(2.0, -1.5, 0.0, 0.0, 0.0).apply_point(point)
    assert posed == Point3(12.0, 18.5, 3.0)


def test_rotation_can_create_z_change_without_any_z_translation_parameter():
    point = Point3(0.0, 30.0, 0.0)
    posed = WornPose(0.0, 0.0, 4.0, 0.0, 0.0).apply_point(point)
    assert posed.z != pytest.approx(0.0)
    assert WornPose(0.0, 0.0, 4.0, 0.0, 0.0).translation_z_mm == 0.0


def test_radial_boundary_contains_cardinal_and_diagonal_directions():
    regression = generate_hard_envelope_regression_set(load_authority(), radial_direction_count=16)
    translations = {
        (round(p.translation_x_mm, 9), round(p.translation_y_mm, 9))
        for p in regression.poses
        if p.roll_x_deg == p.pitch_y_deg == p.yaw_z_deg == 0.0
    }
    assert (5.0, 0.0) in translations
    assert (0.0, 5.0) in translations
    expected_diag = round(5.0 / math.sqrt(2.0), 9)
    assert (expected_diag, expected_diag) in translations


def test_protected_zone_boundary_sampling_is_closed_shape_without_duplicate_endpoint():
    authority = load_authority()
    reference = build_facial_reference(authority)
    protected = build_protected_volumes(authority, reference, build_planar_development_surface(authority))
    points = protected_zone_boundary_points(protected.mouth.zone, samples=32)

    assert len(points) == 32
    assert len({tuple(round(v, 9) for v in point.as_tuple()) for point in points}) == 32
    assert all(point.z == 0.0 for point in points)


def test_posed_zone_bounds_change_under_nonzero_pose_and_are_finite():
    authority = load_authority()
    reference = build_facial_reference(authority)
    protected = build_protected_volumes(authority, reference, build_planar_development_surface(authority))
    zone = protected.eye_left.zone
    identity = posed_zone_bounds(zone, WornPose(0, 0, 0, 0, 0))
    moved = posed_zone_bounds(zone, WornPose(5, 0, 4, -4, 4))

    assert moved != identity
    for value in (
        moved.min_x_mm, moved.max_x_mm, moved.min_y_mm, moved.max_y_mm, moved.min_z_mm, moved.max_z_mm
    ):
        assert math.isfinite(value)
    assert moved.max_x_mm > moved.min_x_mm
    assert moved.max_y_mm > moved.min_y_mm


def test_manifest_states_discrete_screen_not_measured_distribution():
    regression = generate_hard_envelope_regression_set(load_authority())
    manifest = regression.manifest()

    assert manifest["pose_count"] == 459
    assert manifest["translation_z_mm"] == 0.0
    assert manifest["evidence_status"] == "DETERMINISTIC_DISCRETE_SCREEN_NOT_MEASURED_DONNING_DISTRIBUTION"
    assert len(manifest["sha256"]) == 64


def test_nonfinite_pose_values_are_rejected():
    with pytest.raises(WornPoseError):
        WornPose(math.nan, 0, 0, 0, 0)


def test_regression_direction_count_too_low_is_rejected():
    with pytest.raises(WornPoseError, match="at least 4"):
        generate_hard_envelope_regression_set(load_authority(), radial_direction_count=3)
