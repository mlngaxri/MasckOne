import cadquery as cq
import pytest

from masck_one.anatomy import build_facial_reference
from masck_one.authority import load_authority
from masck_one.exterior_eye_roll import (
    EYE_ROLL_MAX_ADDED_VOLUME_MM3,
    EYE_ROLL_SUPPORT_BAND_MM,
    EYE_ROLL_SUPPORT_DEPTH_RESERVE_MM,
    SCHEMA,
    build_eye_rolled_exterior_shell,
    eye_inner_roll_manifest,
)
from masck_one.exterior_inferior_turnover import build_inferior_turnover_exterior_shell
from masck_one.exterior_rigid_clearance import build_current_protected_volumes
from masck_one.spatial import CanonicalDatums


EDGE_CENTER_TOLERANCE_MM = 2.0
BOUND_TOLERANCE_MM = 1e-5
RIGID_EDGE_TOLERANCE_MM = 1e-4


@pytest.fixture(scope="module")
def rolled_geometry():
    authority = load_authority()
    datums = CanonicalDatums.from_authority(authority)
    facial_reference = build_facial_reference(authority, datums)
    protected = build_current_protected_volumes(authority, facial_reference)
    baseline = build_inferior_turnover_exterior_shell(
        authority,
        facial_reference,
        protected,
    ).val()
    rolled = build_eye_rolled_exterior_shell(
        authority,
        facial_reference,
        protected,
    ).val()
    return authority, protected, baseline, rolled


def _eye_edges(
    shape: cq.Shape,
    *,
    center_x_mm: float,
    center_y_mm: float,
    eye_width_mm: float,
    eye_height_mm: float,
) -> list[cq.Edge]:
    result: list[cq.Edge] = []
    for edge in shape.Edges():
        if edge.geomType() not in {"ELLIPSE", "BSPLINE"}:
            continue
        bb = edge.BoundingBox()
        center_x = 0.5 * (float(bb.xmin) + float(bb.xmax))
        center_y = 0.5 * (float(bb.ymin) + float(bb.ymax))
        if abs(center_x - center_x_mm) > EDGE_CENTER_TOLERANCE_MM:
            continue
        if abs(center_y - center_y_mm) > EDGE_CENTER_TOLERANCE_MM:
            continue
        if not 0.80 * eye_width_mm <= float(bb.xlen) <= 1.30 * eye_width_mm:
            continue
        if not 0.80 * eye_height_mm <= float(bb.ylen) <= 1.35 * eye_height_mm:
            continue
        result.append(edge)
    return result


def _mean_z(edge: cq.Edge) -> float:
    bb = edge.BoundingBox()
    return 0.5 * (float(bb.zmin) + float(bb.zmax))


def _bbox_values(edge: cq.Edge) -> tuple[float, float, float, float, float, float]:
    bb = edge.BoundingBox()
    return (
        float(bb.xmin),
        float(bb.xmax),
        float(bb.ymin),
        float(bb.ymax),
        float(bb.zmin),
        float(bb.zmax),
    )


def test_eye_roll_manifest_consumes_authority_radius_at_rigid_hard_edge():
    authority = load_authority()
    manifest = eye_inner_roll_manifest(authority)
    radius = authority.number("geometry", "eye", "inner_edge_roll_radius_mm")
    wall = authority.number("geometry", "shell_nominal_wall_mm")
    eye_width, eye_height = authority.pair("geometry", "eye", "visual_aperture_wh_mm")
    clearance = authority.number("geometry", "eye", "rigid_dynamic_keepout_clearance_mm")
    assert manifest["schema"] == SCHEMA
    assert manifest["radius_mm"] == radius
    assert manifest["visual_aperture_wh_mm"] == [eye_width, eye_height]
    assert manifest["rigid_hard_envelope_wh_mm"] == [
        eye_width + 2.0 * clearance,
        eye_height + 2.0 * clearance,
    ]
    assert manifest["rigid_dynamic_keepout_clearance_mm"] == clearance
    assert manifest["support_band_mm"] == EYE_ROLL_SUPPORT_BAND_MM
    assert manifest["support_depth_reserve_mm"] == EYE_ROLL_SUPPORT_DEPTH_RESERVE_MM
    assert manifest["supported_local_depth_mm"] == pytest.approx(
        max(wall, radius + EYE_ROLL_SUPPORT_DEPTH_RESERVE_MM)
    )
    assert manifest["hidden_added_depth_mm"] == pytest.approx(
        manifest["supported_local_depth_mm"] - wall
    )
    assert manifest["max_added_volume_mm3"] == EYE_ROLL_MAX_ADDED_VOLUME_MM3
    assert manifest["support_location"] == "WEARER_SIDE_ONLY_BEHIND_EXISTING_A_SURFACE"
    assert manifest["rigid_edge_policy"] == (
        "AUTHORITY_ROLL_APPLIED_TO_RELEASED_RIGID_HARD_ENVELOPE_EDGE"
    )
    assert "FUTURE_NONRIGID_VISIBLE_INTERFACE" in manifest["visual_aperture_policy"]
    assert manifest["visible_bezel_added"] is False
    assert manifest["external_a_surface_modified_by_support"] is False


def test_final_brep_eye_roll_preserves_outer_bounds_and_exact_rigid_opening_edge(rolled_geometry):
    _, protected, baseline, rolled = rolled_geometry
    assert rolled.isValid()
    assert len(rolled.Solids()) == 1
    added_volume = float(rolled.Volume()) - float(baseline.Volume())
    assert added_volume > 0.0
    assert added_volume <= EYE_ROLL_MAX_ADDED_VOLUME_MM3

    baseline_bb = baseline.BoundingBox()
    rolled_bb = rolled.BoundingBox()
    for previous, current in (
        (baseline_bb.xmin, rolled_bb.xmin),
        (baseline_bb.xmax, rolled_bb.xmax),
        (baseline_bb.ymin, rolled_bb.ymin),
        (baseline_bb.ymax, rolled_bb.ymax),
        (baseline_bb.zmin, rolled_bb.zmin),
        (baseline_bb.zmax, rolled_bb.zmax),
    ):
        assert float(current) == pytest.approx(float(previous), abs=BOUND_TOLERANCE_MM)

    for zone in (protected.eye_left.zone, protected.eye_right.zone):
        baseline_edges = _eye_edges(
            baseline,
            center_x_mm=zone.center.x,
            center_y_mm=zone.center.y,
            eye_width_mm=zone.envelope_width_mm,
            eye_height_mm=zone.envelope_height_mm,
        )
        rolled_edges = _eye_edges(
            rolled,
            center_x_mm=zone.center.x,
            center_y_mm=zone.center.y,
            eye_width_mm=zone.envelope_width_mm,
            eye_height_mm=zone.envelope_height_mm,
        )
        assert len(baseline_edges) >= 2
        assert len(rolled_edges) >= 3

        baseline_anterior = max(baseline_edges, key=_mean_z)
        rolled_anterior = max(rolled_edges, key=_mean_z)
        for previous, current in zip(
            _bbox_values(baseline_anterior),
            _bbox_values(rolled_anterior),
        ):
            assert current == pytest.approx(previous, abs=RIGID_EDGE_TOLERANCE_MM)

        rolled_wearer = min(rolled_edges, key=_mean_z)
        assert _mean_z(rolled_wearer) < _mean_z(rolled_anterior)
        assert float(rolled_wearer.Length()) > float(rolled_anterior.Length())


def test_eye_centerlines_remain_open_through_rolled_shell(rolled_geometry):
    _, protected, _, rolled = rolled_geometry
    for zone in (protected.eye_left.zone, protected.eye_right.zone):
        probe = (
            cq.Workplane("XY")
            .workplane(offset=-8.0)
            .center(zone.center.x, zone.center.y)
            .circle(0.25)
            .extrude(48.0)
            .val()
        )
        assert float(rolled.intersect(probe).Volume()) == pytest.approx(0.0, abs=1e-8)
