from masck_one.anatomy import build_facial_reference
from masck_one.authority import load_authority
from masck_one.exterior_surface import (
    ANTERIOR_CROWN_SAMPLE_Y_NORM,
    _anterior_crown_constraints,
    anterior_crown_boundary_z_mm,
    exterior_sections,
)
from masck_one.spatial import CanonicalDatums


BROW_RIDGE_BUMP_MAX_MM = 0.45
SUPERIOR_CENTERLINE_DROP_MAX_MM = 2.30
SUPERIOR_CONTROL_REACH_MIN_NORM = 0.44


def _centerline_constraint_z_by_normalized_y() -> dict[float, float]:
    authority = load_authority()
    datums = CanonicalDatums.from_authority(authority)
    facial_reference = build_facial_reference(authority, datums)
    _, width, height = exterior_sections(authority)[-1]
    constraints = _anterior_crown_constraints(
        width,
        height,
        anterior_crown_boundary_z_mm(authority),
        facial_reference,
    )

    rows: dict[float, list[tuple[float, float, float]]] = {}
    for point in constraints:
        rows.setdefault(round(point[1] / height, 6), []).append(point)
    return {
        y_norm: min(row, key=lambda point: abs(point[0]))[2]
        for y_norm, row in rows.items()
    }


def test_superior_constraint_field_has_no_separate_brow_ridge():
    centerline = _centerline_constraint_z_by_normalized_y()
    z0 = centerline[0.0]
    z12 = centerline[0.12]
    z24 = centerline[0.24]
    z36 = centerline[0.36]

    local_brow_bump = z12 - 0.5 * (z0 + z24)
    assert local_brow_bump <= BROW_RIDGE_BUMP_MAX_MM
    assert z12 - z36 <= SUPERIOR_CENTERLINE_DROP_MAX_MM


def test_superior_crown_control_reaches_forehead_transition_zone():
    assert max(ANTERIOR_CROWN_SAMPLE_Y_NORM) >= SUPERIOR_CONTROL_REACH_MIN_NORM
