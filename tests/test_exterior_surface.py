import math

import cadquery as cq

from masck_one.anatomy import build_facial_reference
from masck_one.authority import load_authority
from masck_one.exterior_surface import (
    ANTERIOR_CROWN_HEIGHT_MM,
    ANTERIOR_CROWN_RELIEF_MAX_MM,
    ANTERIOR_CROWN_RELIEF_MIN_MM,
    EXTERIOR_SCALE_X,
    EXTERIOR_SCALE_Y,
    EXTERIOR_Z_STATIONS_MM,
    PROFILE_RIGHT,
    anterior_crown_inner_min_z_mm,
    build_refined_exterior_shell,
    exterior_sections,
    exterior_surface_manifest,
)
from masck_one.integrated_product import build_mvp_product_candidate
from masck_one.spatial import CanonicalDatums


def _build_shell():
    authority = load_authority()
    datums = CanonicalDatums.from_authority(authority)
    facial_reference = build_facial_reference(authority, datums)
    return authority, facial_reference, build_refined_exterior_shell(authority, facial_reference)


def test_surface_stations_are_monotonic_and_gradual():
    assert len(EXTERIOR_Z_STATIONS_MM) >= 4
    assert all(b > a for a, b in zip(EXTERIOR_Z_STATIONS_MM, EXTERIOR_Z_STATIONS_MM[1:]))
    assert all(b >= a for a, b in zip(EXTERIOR_SCALE_X, EXTERIOR_SCALE_X[1:]))
    assert all(b >= a for a, b in zip(EXTERIOR_SCALE_Y, EXTERIOR_SCALE_Y[1:]))
    assert max(b - a for a, b in zip(EXTERIOR_SCALE_X, EXTERIOR_SCALE_X[1:])) <= 0.015
    assert max(b - a for a, b in zip(EXTERIOR_SCALE_Y, EXTERIOR_SCALE_Y[1:])) <= 0.010


def test_authored_sections_stay_inside_authority_envelope():
    authority = load_authority()
    outer_w, outer_h = authority.pair("geometry", "outer_xy_envelope_mm")
    sections = exterior_sections(authority)
    assert max(section[1] for section in sections) <= outer_w
    assert max(section[2] for section in sections) <= outer_h


def test_control_profile_wall_reserve_exceeds_absolute_development_minimum():
    authority = load_authority()
    nominal_wall = authority.number("geometry", "shell_nominal_wall_mm")
    absolute_min = authority.number("geometry", "shell_absolute_development_min_mm")
    # Inner side-body sections shrink width and height by two nominal walls. At every
    # authored profile control point the corresponding XY reserve is wall*hypot(x,y).
    # This is a deterministic control-net guard, not a tooling or molded-wall claim.
    minimum_control_reserve = nominal_wall * min(math.hypot(x, y) for x, y in PROFILE_RIGHT)
    assert minimum_control_reserve >= absolute_min


def test_manifest_records_curved_consumer_form_policy_without_physical_claims():
    authority = load_authority()
    manifest = exterior_surface_manifest(authority)
    assert manifest["schema"] == "MASCK_ONE_CELL2_EXTERIOR_SURFACE_V2"
    assert manifest["loft_mode"] == "smooth_non_ruled_profile_spline_with_interpolated_anterior_crown"
    assert manifest["anterior_crown"]["height_mm"] == ANTERIOR_CROWN_HEIGHT_MM
    assert manifest["anterior_crown"]["visible_relief_guard_mm"] == [
        ANTERIOR_CROWN_RELIEF_MIN_MM,
        ANTERIOR_CROWN_RELIEF_MAX_MM,
    ]
    assert manifest["anterior_crown"]["join_overlap_status"] == "NUMERICAL_BOOLEAN_CONSTRUCTION_ONLY"
    assert manifest["visible_face_policy"] == "CURVED_ANTERIOR_FACIAL_FIELD_WITH_AUTHORITY_BACKED_APERTURES"
    assert manifest["design_intent"]["side_mass"] == "laterally_blended_not_podded"
    assert manifest["evidence_status"] == "DIGITAL_CAD_MVP_EXTERIOR_NOT_CLASS_A_OR_PHYSICAL_EVIDENCE"


def test_refined_shell_is_one_valid_positive_volume_solid_inside_xy_envelope():
    authority, _, shell = _build_shell()
    assert shell.solids().size() == 1
    solid = shell.val()
    assert solid.isValid()
    assert solid.Volume() > 0.0
    outer_w, outer_h = authority.pair("geometry", "outer_xy_envelope_mm")
    bb = solid.BoundingBox()
    assert bb.xlen <= outer_w + 1e-5
    assert bb.ylen <= outer_h + 1e-5


def test_anterior_crown_removes_large_planar_prototype_face():
    _, _, shell = _build_shell()
    solid = shell.val()
    bb = solid.BoundingBox()
    visible_relief = bb.zmax - EXTERIOR_Z_STATIONS_MM[-1]
    assert ANTERIOR_CROWN_RELIEF_MIN_MM <= visible_relief <= ANTERIOR_CROWN_RELIEF_MAX_MM
    assert bb.zmax >= EXTERIOR_Z_STATIONS_MM[-1] + 0.95 * ANTERIOR_CROWN_HEIGHT_MM
    anterior_planar_faces = [
        face
        for face in solid.Faces()
        if face.geomType() == "PLANE"
        and float(face.normalAt().z) > 0.999999
        and float(face.Center().z) > EXTERIOR_Z_STATIONS_MM[-1]
        and face.Area() > 1000.0
    ]
    assert anterior_planar_faces == []


def test_protected_aperture_centerlines_remain_open_through_crown():
    _, facial_reference, shell = _build_shell()
    solid = shell.val()
    points = (
        facial_reference.eye_pair.left.point_xy,
        facial_reference.eye_pair.right.point_xy,
        facial_reference.nostril_pair.left.point_xy,
        facial_reference.nostril_pair.right.point_xy,
        facial_reference.mouth_center.point_xy,
    )
    for point in points:
        for z in (0.0, 10.0, 20.0, 23.0, 25.0):
            assert not solid.isInside(cq.Vector(point.x, point.y, z), 1e-6)


def test_crown_starts_anterior_of_current_package_envelopes():
    model = build_mvp_product_candidate()
    crown_inner_z = anterior_crown_inner_min_z_mm(model.authority)
    packages = (
        *model.actuator_envelopes,
        model.water_reservoir_envelope,
        model.waste_cartridge_envelope,
        model.battery_reference_envelope,
    )
    for component in packages:
        assert component.solid.val().BoundingBox().zmax < crown_inner_z
