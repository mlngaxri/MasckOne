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


ACTUAL_SECTION_TAPER_MIN_MM = 4.0


def _build_shell():
    authority = load_authority()
    datums = CanonicalDatums.from_authority(authority)
    facial_reference = build_facial_reference(authority, datums)
    return authority, facial_reference, build_refined_exterior_shell(authority, facial_reference)


def _section_xy_span_mm(solid: cq.Shape, z_mm: float) -> tuple[float, float]:
    section = cq.Workplane("XY").workplane(offset=z_mm).newObject([solid]).section()
    if section.size() == 0:
        raise AssertionError(f"Exterior section at Z={z_mm} mm is empty")
    bb = section.val().BoundingBox()
    return float(bb.xlen), float(bb.ylen)


def test_surface_stations_are_controlled_and_taper_before_crown():
    assert len(EXTERIOR_Z_STATIONS_MM) >= 4
    assert all(b > a for a, b in zip(EXTERIOR_Z_STATIONS_MM, EXTERIOR_Z_STATIONS_MM[1:]))
    assert all(scale > 0.0 for scale in EXTERIOR_SCALE_X)
    assert all(scale > 0.0 for scale in EXTERIOR_SCALE_Y)

    # Peak side mass must occur before the anterior perimeter. This is the authored
    # construction guard; a separate B-rep regression below verifies the built result.
    peak_x = max(range(len(EXTERIOR_SCALE_X)), key=EXTERIOR_SCALE_X.__getitem__)
    peak_y = max(range(len(EXTERIOR_SCALE_Y)), key=EXTERIOR_SCALE_Y.__getitem__)
    assert 0 < peak_x < len(EXTERIOR_SCALE_X) - 1
    assert 0 < peak_y < len(EXTERIOR_SCALE_Y) - 1
    assert EXTERIOR_SCALE_X[-1] < EXTERIOR_SCALE_X[peak_x]
    assert EXTERIOR_SCALE_Y[-1] < EXTERIOR_SCALE_Y[peak_y]

    # Keep station-to-station change broad and loft-friendly rather than faceted.
    assert max(abs(b - a) for a, b in zip(EXTERIOR_SCALE_X, EXTERIOR_SCALE_X[1:])) <= 0.040
    assert max(abs(b - a) for a, b in zip(EXTERIOR_SCALE_Y, EXTERIOR_SCALE_Y[1:])) <= 0.030


def test_authored_sections_stay_inside_authority_envelope():
    authority = load_authority()
    outer_w, outer_h = authority.pair("geometry", "outer_xy_envelope_mm")
    sections = exterior_sections(authority)
    assert max(section[1] for section in sections) <= outer_w
    assert max(section[2] for section in sections) <= outer_h


def test_anterior_perimeter_tapers_materially_from_peak_side_mass():
    authority = load_authority()
    sections = exterior_sections(authority)
    _, peak_width, peak_height = sections[-2]
    _, anterior_width, anterior_height = sections[-1]
    assert peak_width - anterior_width >= 4.0
    assert peak_height - anterior_height >= 4.0


def test_built_shell_carries_actual_midbody_depth_into_anterior_taper():
    _, _, shell = _build_shell()
    solid = shell.val()
    peak_width, peak_height = _section_xy_span_mm(solid, 16.0)
    anterior_width, anterior_height = _section_xy_span_mm(solid, 21.5)

    # This protects the visible B-rep result rather than only the authored control net.
    # The exact current candidate measures roughly 4.59 mm X taper and 4.16 mm Y taper.
    assert peak_width - anterior_width >= ACTUAL_SECTION_TAPER_MIN_MM
    assert peak_height - anterior_height >= ACTUAL_SECTION_TAPER_MIN_MM


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
    assert manifest["design_intent"]["side_mass"] == "midbody_fullness_with_anterior_perimeter_taper_not_podded"
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
    # ANTERIOR_CROWN_HEIGHT_MM is the unshaped radial construction amplitude, not a
    # lower bound on the final compound B-rep after superior, nasal and lower-face
    # shaping terms are applied. The explicit final relief guard above owns that truth.
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


def test_shell_has_no_material_intersection_with_released_waste_cartridge_envelope():
    model = build_mvp_product_candidate()
    intersection = model.shell.solid.val().intersect(model.waste_cartridge_envelope.solid.val())
    # OpenCascade can report signed numerical noise around zero volume; reject any
    # material overlap larger than the kernel-level construction scale.
    assert abs(float(intersection.Volume())) <= 1e-5


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
