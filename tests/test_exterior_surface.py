import math

from masck_one.anatomy import build_facial_reference
from masck_one.authority import load_authority
from masck_one.exterior_surface import (
    EXTERIOR_SCALE_X,
    EXTERIOR_SCALE_Y,
    EXTERIOR_Z_STATIONS_MM,
    PROFILE_RIGHT,
    build_refined_exterior_shell,
    exterior_sections,
    exterior_surface_manifest,
)
from masck_one.spatial import CanonicalDatums


def _build_shell():
    authority = load_authority()
    datums = CanonicalDatums.from_authority(authority)
    facial_reference = build_facial_reference(authority, datums)
    return authority, build_refined_exterior_shell(authority, facial_reference)


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
    # Inner sections shrink width and height by two nominal walls. At every authored
    # profile control point the corresponding XY separation is wall * hypot(x, y).
    # This is a deterministic control-net guard, not a tooling or molded-wall claim.
    minimum_control_reserve = nominal_wall * min(math.hypot(x, y) for x, y in PROFILE_RIGHT)
    assert minimum_control_reserve >= absolute_min


def test_manifest_records_non_ruled_consumer_form_policy_without_physical_claims():
    authority = load_authority()
    manifest = exterior_surface_manifest(authority)
    assert manifest["schema"] == "MASCK_ONE_CELL2_EXTERIOR_SURFACE_V1"
    assert manifest["loft_mode"] == "smooth_non_ruled_profile_spline"
    assert manifest["visible_face_policy"] == "ANTERIOR_FACIAL_FIELD_RETAINED_AT_NOMINAL_WALL_THICKNESS"
    assert manifest["design_intent"]["side_mass"] == "laterally_blended_not_podded"
    assert manifest["evidence_status"] == "DIGITAL_CAD_MVP_EXTERIOR_NOT_CLASS_A_OR_PHYSICAL_EVIDENCE"


def test_refined_shell_builds_as_valid_positive_volume_solid_inside_authority_envelope():
    authority, shell = _build_shell()
    solid = shell.val()
    assert solid.isValid()
    assert solid.Volume() > 0.0
    outer_w, outer_h = authority.pair("geometry", "outer_xy_envelope_mm")
    bb = solid.BoundingBox()
    assert bb.xlen <= outer_w + 1e-6
    assert bb.ylen <= outer_h + 1e-6
    assert bb.zlen <= max(EXTERIOR_Z_STATIONS_MM) - min(EXTERIOR_Z_STATIONS_MM) + 1e-6


def test_anterior_facial_field_retains_five_real_protected_apertures():
    _, shell = _build_shell()
    solid = shell.val()
    anterior_z = max(float(face.Center().z) for face in solid.Faces())
    anterior_faces = [
        face
        for face in solid.Faces()
        if face.geomType() == "PLANE"
        and abs(float(face.Center().z) - anterior_z) < 1e-6
        and float(face.normalAt().z) > 0.999999
    ]
    assert len(anterior_faces) == 1
    facial_field = anterior_faces[0]
    assert facial_field.Area() > 10000.0
    # One outer perimeter wire plus two eyes, two nostrils and one mouth.
    assert len(facial_field.Wires()) == 6
