import cadquery as cq

from masck_one.anatomy import build_facial_reference
from masck_one.authority import load_authority
from masck_one.exterior_construction import build_constructed_exterior_shell
from masck_one.exterior_inferior_turnover import build_inferior_turnover_exterior_shell
from masck_one.spatial import CanonicalDatums


PROBE_HALF_WIDTH_MM = 0.70
BOUND_TOLERANCE_MM = 1e-5
CENTER_FIELD_CHANGE_MAX_MM = 0.05
MINIMUM_LATERAL_SETBACK_MM = {
    24.0: 0.15,
    36.0: 0.35,
    48.0: 0.55,
}
MIRROR_TOLERANCE_MM = 0.01


def _models():
    authority = load_authority()
    datums = CanonicalDatums.from_authority(authority)
    facial_reference = build_facial_reference(authority, datums)
    previous = build_constructed_exterior_shell(authority, facial_reference).val()
    candidate = build_inferior_turnover_exterior_shell(authority, facial_reference).val()
    return previous, candidate


def _front_z_at_xy(solid: cq.Shape, x_mm: float, y_mm: float) -> float:
    probe = (
        cq.Workplane("XY")
        .box(
            2.0 * PROBE_HALF_WIDTH_MM,
            2.0 * PROBE_HALF_WIDTH_MM,
            60.0,
            centered=(True, True, True),
        )
        .translate((x_mm, y_mm, 15.0))
        .val()
    )
    intersection = solid.intersect(probe)
    assert float(intersection.Volume()) > 0.0
    return float(intersection.BoundingBox().zmax)


def test_final_brep_side_mass_feathers_progressively_without_moving_package_footprint():
    previous, candidate = _models()
    previous_bb = previous.BoundingBox()
    candidate_bb = candidate.BoundingBox()
    assert abs(candidate_bb.xlen - previous_bb.xlen) <= BOUND_TOLERANCE_MM
    assert abs(candidate_bb.ylen - previous_bb.ylen) <= BOUND_TOLERANCE_MM
    assert abs(candidate_bb.zmin - previous_bb.zmin) <= BOUND_TOLERANCE_MM

    center_change = abs(
        _front_z_at_xy(candidate, 0.0, 0.0)
        - _front_z_at_xy(previous, 0.0, 0.0)
    )
    assert center_change <= CENTER_FIELD_CHANGE_MAX_MM

    setbacks: list[float] = []
    for x_mm, minimum_setback in MINIMUM_LATERAL_SETBACK_MM.items():
        positive = _front_z_at_xy(previous, x_mm, 0.0) - _front_z_at_xy(candidate, x_mm, 0.0)
        negative = _front_z_at_xy(previous, -x_mm, 0.0) - _front_z_at_xy(candidate, -x_mm, 0.0)
        assert positive >= minimum_setback
        assert negative >= minimum_setback
        assert abs(positive - negative) <= MIRROR_TOLERANCE_MM
        setbacks.append(0.5 * (positive + negative))

    assert setbacks[0] < setbacks[1] < setbacks[2]
