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


def test_surface_stations_are_monotonic_and_gradual():
    assert len(EXTERIOR_Z_STATIONS_MM) >= 4
    assert all(b > a for a, b in zip(EXTERIOR_Z_STATIONS_MM, EXTERIOR_Z_STATIONS_MM[1:]))
    assert all(b >= a for a, b in zip(EXTERIOR_SCALE_X, EXTERIOR_SCALE_X[1:]))
    assert all(b >= a for a, b in zip(EXTERIOR_SCALE_Y, EXTERIOR_SCALE_Y[1:]))
    assert max(b - a for a, b in zip(EXTERIOR_SCALE_X, EXTERIOR_SCALE_X[1:])) <= 0.015
    assert max(b - a for a, b in zip(EXTERIOR_SCALE_Y, EXTERIOR_SCALE_Y[1:])) <= 0.010


def test_manifest_stays_inside_authoritative_xy_envelope():
    authority = load_authority()
    outer_w, outer_h = authority.pair("geometry", "outer_xy_envelope_mm")
    manifest = exterior_surface_manifest(authority)
    assert max(manifest["width_mm"]) <= outer_w
    assert max(manifest["height_mm"]) <= outer_h
    assert manifest["loft_mode"] == "smooth_non_ruled"
    assert manifest["design_intent"]["side_mass"] == "laterally_blended_not_podded"


def test_refined_shell_builds_as_valid_positive_volume_solid():
    authority = load_authority()
    datums = CanonicalDatums.from_authority(authority)
    facial_reference = build_facial_reference(authority, datums)
    shell = build_refined_exterior_shell(authority, facial_reference)
    solid = shell.val()
    assert solid.isValid()
    assert solid.Volume() > 0.0
