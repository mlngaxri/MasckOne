import cadquery as cq

from masck_one.anatomy import build_facial_reference
from masck_one.authority import load_authority
from masck_one.exterior_construction import build_constructed_exterior_shell
from masck_one.exterior_inferior_turnover import (
    INFERIOR_TURNOVER_CENTER_Y_OFFSET_FROM_MOUTH_NORM,
    INFERIOR_TURNOVER_EXTRA_RECESS_MM,
    INFERIOR_TURNOVER_SPREAD_X_NORM,
    INFERIOR_TURNOVER_SPREAD_Y_NORM,
    SIDE_MASS_FEATHER_CENTER_Y_NORM,
    SIDE_MASS_FEATHER_FULL_X_NORM,
    SIDE_MASS_FEATHER_RECESS_MM,
    SIDE_MASS_FEATHER_SPREAD_Y_NORM,
    SIDE_MASS_FEATHER_START_X_NORM,
    build_inferior_turnover_exterior_shell,
    inferior_turnover_manifest,
)
from masck_one.spatial import CanonicalDatums


SLICE_BAND_MM = 0.40
BOUND_TOLERANCE_MM = 1e-5
MINIMUM_BUILT_SETBACK_MM = {
    -70.0: 0.30,
    -80.0: 0.30,
    -85.0: 0.25,
}


def _facial_reference():
    authority = load_authority()
    datums = CanonicalDatums.from_authority(authority)
    return authority, build_facial_reference(authority, datums)


def _front_z_in_y_band(solid: cq.Shape, y_mm: float) -> float:
    slab = (
        cq.Workplane("XY")
        .box(220.0, SLICE_BAND_MM, 60.0, centered=(True, True, True))
        .translate((0.0, y_mm, 15.0))
        .val()
    )
    intersection = solid.intersect(slab)
    assert float(intersection.Volume()) > 0.0
    return float(intersection.BoundingBox().zmax)


def test_final_brep_inferior_turnover_reduces_chin_projection_without_moving_footprint():
    authority, facial_reference = _facial_reference()
    previous = build_constructed_exterior_shell(authority, facial_reference).val()
    candidate = build_inferior_turnover_exterior_shell(authority, facial_reference).val()

    previous_bb = previous.BoundingBox()
    candidate_bb = candidate.BoundingBox()
    assert abs(candidate_bb.xlen - previous_bb.xlen) <= BOUND_TOLERANCE_MM
    assert abs(candidate_bb.ylen - previous_bb.ylen) <= BOUND_TOLERANCE_MM
    assert abs(candidate_bb.zmin - previous_bb.zmin) <= BOUND_TOLERANCE_MM

    candidate_front_z: list[float] = []
    for y_mm, minimum_setback_mm in MINIMUM_BUILT_SETBACK_MM.items():
        previous_z = _front_z_in_y_band(previous, y_mm)
        candidate_z = _front_z_in_y_band(candidate, y_mm)
        assert previous_z - candidate_z >= minimum_setback_mm
        candidate_front_z.append(candidate_z)

    assert candidate_front_z[0] > candidate_front_z[1] > candidate_front_z[2]


def test_inferior_turnover_manifest_keeps_soft_interface_and_package_footprint_uninvented():
    authority = load_authority()
    manifest = inferior_turnover_manifest(authority)
    assert manifest["schema"] == "MASCK_ONE_CELL2_INFERIOR_TURNOVER_V3"
    assert manifest["extra_anterior_recess_mm"] == INFERIOR_TURNOVER_EXTRA_RECESS_MM
    assert manifest["center_y_offset_from_mouth_norm"] == (
        INFERIOR_TURNOVER_CENTER_Y_OFFSET_FROM_MOUTH_NORM
    )
    assert manifest["spread_x_norm"] == INFERIOR_TURNOVER_SPREAD_X_NORM
    assert manifest["spread_y_norm"] == INFERIOR_TURNOVER_SPREAD_Y_NORM
    assert manifest["side_mass_feather_recess_mm"] == SIDE_MASS_FEATHER_RECESS_MM
    assert manifest["side_mass_feather_start_x_norm"] == SIDE_MASS_FEATHER_START_X_NORM
    assert manifest["side_mass_feather_full_x_norm"] == SIDE_MASS_FEATHER_FULL_X_NORM
    assert manifest["side_mass_feather_center_y_norm"] == SIDE_MASS_FEATHER_CENTER_Y_NORM
    assert manifest["side_mass_feather_spread_y_norm"] == SIDE_MASS_FEATHER_SPREAD_Y_NORM
    assert manifest["side_body_station_policy"] == "UNCHANGED_FROM_PROMPT08"
    assert manifest["rear_cavity_policy"] == "UNCHANGED_FROM_PROMPT08"
    assert manifest["perimeter_footprint_policy"] == "UNCHANGED_FROM_PROMPT08"
    assert manifest["rigid_protected_face_policy"] == (
        "CONSUME_RELEASED_PLANAR_HARD_ENVELOPES_AS_THROUGH_CUTS"
    )
    assert manifest["soft_interface_geometry_status"] == "UNRESOLVED_NOT_INVENTED"
