from masck_one.anatomy import build_facial_reference
from masck_one.authority import load_authority
from masck_one.exterior_surface import (
    EXTERIOR_SCALE_X,
    EXTERIOR_SCALE_Y,
    EXTERIOR_Z_STATIONS_MM,
    build_refined_exterior_shell,
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


def test_manifest_nominal_sections_stay_inside_authoritative_xy_envelope():
    authority = load_authority()
    outer_w, outer_h = authority.pair("geometry", "outer_xy_envelope_mm")
    manifest = exterior_surface_manifest(authority)
    assert max(manifest["nominal_width_mm"]) <= outer_w
    assert max(manifest["nominal_height_mm"]) <= outer_h
    assert manifest["loft_mode"] == "smooth_non_ruled_profile_spline"
    assert manifest["visible_face_policy"] == "ANTERIOR_FACIAL_FIELD_RETAINED_AT_NOMINAL_WALL_THICKNESS"
    assert manifest["design_intent"]["side_mass"] == "laterally_blended_not_podded"


def test_refined_shell_builds_as_valid_positive_volume_solid_inside_authority_envelope():
    authority, shell = _build_shell()
    solid = shell.val()
    assert solid.isValid()
    assert solid.Volume() > 0.0
    outer_w, outer_h = authority.pair("geometry", "outer_xy_envelope_mm")
    bb = solid.BoundingBox()
    assert bb.xlen <= outer_w + 1e-6
    assert bb.ylen <= outer_h + 1e-6


def test_anterior_facial_field_exists_and_contains_five_real_protected_apertures():
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
