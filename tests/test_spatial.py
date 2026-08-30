from __future__ import annotations

import math

import pytest

from masck_one.authority import load_authority
from masck_one.spatial import (
    CanonicalDatums,
    DatumFrame,
    Matrix3,
    Point2,
    Point3,
    RigidTransform,
    SpatialContractError,
    Vector3,
    authority_point2,
)


def test_canonical_datums_match_frozen_authority_axes_and_origin():
    authority = load_authority()
    datums = CanonicalDatums.from_authority(authority)

    assert datums.global_frame.origin == Point3(0.0, 0.0, 0.0)
    assert datums.global_frame.x_axis == Vector3(1.0, 0.0, 0.0)
    assert datums.global_frame.y_axis == Vector3(0.0, 1.0, 0.0)
    assert datums.global_frame.z_axis == Vector3(0.0, 0.0, 1.0)
    assert datums.global_frame.x_axis.cross(datums.global_frame.y_axis) == datums.global_frame.z_axis


def test_canonical_planes_have_expected_sign_convention():
    datums = CanonicalDatums.from_authority(load_authority())

    wearer_right = Point3(12.0, 0.0, 0.0)
    superior = Point3(0.0, 15.0, 0.0)
    anterior = Point3(0.0, 0.0, 9.0)

    assert datums.sagittal_plane.signed_distance(wearer_right) == pytest.approx(12.0)
    assert datums.transverse_plane.signed_distance(superior) == pytest.approx(15.0)
    assert datums.coronal_plane.signed_distance(anterior) == pytest.approx(9.0)


def test_sagittal_mirror_is_exact_and_involutive():
    datums = CanonicalDatums.from_authority(load_authority())
    point = Point3(31.5, 35.0, 7.25)

    mirrored = datums.mirror_sagittal(point)
    assert mirrored == Point3(-31.5, 35.0, 7.25)
    assert datums.mirror_sagittal(mirrored) == point


def test_authority_point_adapter_preserves_existing_eye_coordinates():
    authority = load_authority()
    left = authority_point2(authority, "geometry", "eye", "centers_mm", "left")
    right = authority_point2(authority, "geometry", "eye", "centers_mm", "right")

    assert left == Point2(-31.5, 35.0)
    assert right == Point2(31.5, 35.0)
    assert left.mirrored_across_sagittal() == right


def test_positive_z_rotation_obeys_right_hand_rule():
    rotation = Matrix3.rotation_z(90.0)
    rotated = rotation.apply_vector(Vector3(1.0, 0.0, 0.0))

    assert rotated.is_close(Vector3(0.0, 1.0, 0.0), abs_tol=1e-12)
    assert rotation.is_rotation()
    assert rotation.determinant() == pytest.approx(1.0)


def test_positive_y_rotation_maps_anterior_axis_toward_wearer_right():
    rotation = Matrix3.rotation_y(90.0)
    rotated = rotation.apply_vector(Vector3(0.0, 0.0, 1.0))

    assert rotated.is_close(Vector3(1.0, 0.0, 0.0), abs_tol=1e-12)


def test_rigid_transform_inverse_round_trip_is_numerically_stable():
    transform = RigidTransform.from_extrinsic_xyz(
        Vector3(8.0, -4.0, 12.0),
        roll_x_deg=7.0,
        pitch_y_deg=-11.0,
        yaw_z_deg=4.0,
    )
    point = Point3(42.0, -17.0, 3.5)
    vector = Vector3(2.0, -1.0, 0.5)

    point_round_trip = transform.inverse().apply_point(transform.apply_point(point))
    vector_round_trip = transform.inverse().apply_vector(transform.apply_vector(vector))

    assert point_round_trip.is_close(point, abs_tol=1e-10)
    assert vector_round_trip.is_close(vector, abs_tol=1e-10)


def test_followed_by_has_explicit_application_order():
    translate = RigidTransform.from_translation(Vector3(10.0, 0.0, 0.0))
    rotate = RigidTransform(Matrix3.rotation_z(90.0), Vector3(0.0, 0.0, 0.0))
    point = Point3(1.0, 0.0, 0.0)

    combined = translate.followed_by(rotate)
    expected = rotate.apply_point(translate.apply_point(point))

    assert combined.apply_point(point).is_close(expected, abs_tol=1e-12)
    assert combined.apply_point(point).is_close(Point3(0.0, 11.0, 0.0), abs_tol=1e-12)


def test_datum_frame_local_global_round_trip():
    frame = DatumFrame(
        "TEST_ROTATED",
        Point3(5.0, 6.0, 7.0),
        Vector3(0.0, 1.0, 0.0),
        Vector3(-1.0, 0.0, 0.0),
        Vector3(0.0, 0.0, 1.0),
    )
    local = Point3(4.0, -3.0, 2.0)

    global_point = frame.local_to_global(local)
    recovered = frame.global_to_local(global_point)

    assert recovered.is_close(local, abs_tol=1e-12)


def test_plane_projection_removes_only_normal_component():
    datums = CanonicalDatums.from_authority(load_authority())
    point = Point3(7.0, 12.0, 5.0)

    projected = datums.sagittal_plane.project(point)
    assert projected == Point3(0.0, 12.0, 5.0)


def test_invalid_zero_vector_normalization_is_rejected():
    with pytest.raises(SpatialContractError):
        Vector3(0.0, 0.0, 0.0).normalized()


def test_invalid_left_handed_datum_frame_is_rejected():
    with pytest.raises(SpatialContractError):
        DatumFrame(
            "LEFT_HANDED",
            Point3(0.0, 0.0, 0.0),
            Vector3(1.0, 0.0, 0.0),
            Vector3(0.0, 1.0, 0.0),
            Vector3(0.0, 0.0, -1.0),
        )


def test_invalid_non_orthonormal_transform_is_rejected():
    bad_rotation = Matrix3(((1.0, 0.1, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)))
    with pytest.raises(SpatialContractError):
        RigidTransform(bad_rotation, Vector3(0.0, 0.0, 0.0))


def test_all_spatial_primitives_reject_non_finite_values():
    with pytest.raises(SpatialContractError):
        Point3(math.inf, 0.0, 0.0)
    with pytest.raises(SpatialContractError):
        Vector3(0.0, math.nan, 0.0)
