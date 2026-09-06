from masck_one.anatomy import build_facial_reference
from masck_one.authority import load_authority
from masck_one.exterior_surface import (
    ANTERIOR_CHIN_CENTER_Y_OFFSET_NORM,
    ANTERIOR_LOWER_FACE_LATERAL_BIAS,
    ANTERIOR_MOUTH_NEUTRAL_SPREAD_X_NORM,
    ANTERIOR_MOUTH_NEUTRAL_SPREAD_Y_NORM,
    _anterior_crown_constraints,
    anterior_crown_boundary_z_mm,
    exterior_sections,
)
from masck_one.spatial import CanonicalDatums


MOUTH_CENTER_LEAD_MAX_MM = 0.40
CHIN_CENTER_LEAD_MAX_MM = 0.45
MIRROR_Z_TOLERANCE_MM = 1e-9


def _constraint_rows():
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
        rows.setdefault(point[1], []).append(point)
    return authority, facial_reference, width, height, rows


def _center_and_first_lateral_pair(row):
    center = min(row, key=lambda point: abs(point[0]))
    positive = min((point for point in row if point[0] > 0.0), key=lambda point: point[0])
    negative = max((point for point in row if point[0] < 0.0), key=lambda point: point[0])
    return center, negative, positive


def test_lower_face_constraint_field_avoids_mouth_muzzle_and_robotic_chin():
    _, facial_reference, _, height, rows = _constraint_rows()
    mouth_y = facial_reference.mouth_center.point_xy.y

    mouth_row_y = min(rows, key=lambda y: abs(y - mouth_y))
    mouth_center, mouth_left, mouth_right = _center_and_first_lateral_pair(rows[mouth_row_y])
    assert abs(mouth_left[2] - mouth_right[2]) <= MIRROR_Z_TOLERANCE_MM
    mouth_lateral_z = 0.5 * (mouth_left[2] + mouth_right[2])
    assert mouth_center[2] - mouth_lateral_z <= MOUTH_CENTER_LEAD_MAX_MM

    chin_target_y = mouth_y + ANTERIOR_CHIN_CENTER_Y_OFFSET_NORM * height
    chin_row_y = min(rows, key=lambda y: abs(y - chin_target_y))
    chin_center, chin_left, chin_right = _center_and_first_lateral_pair(rows[chin_row_y])
    assert abs(chin_left[2] - chin_right[2]) <= MIRROR_Z_TOLERANCE_MM
    chin_lateral_z = 0.5 * (chin_left[2] + chin_right[2])
    assert chin_center[2] - chin_lateral_z <= CHIN_CENTER_LEAD_MAX_MM


def test_mouth_neutrality_recess_is_broad_not_an_aperture_bezel():
    authority, _, width, height, _ = _constraint_rows()
    mouth_w, mouth_h = authority.pair("geometry", "mouth", "visual_aperture_wh_mm")
    assert 0.0 <= ANTERIOR_LOWER_FACE_LATERAL_BIAS <= 1.0
    assert width * ANTERIOR_MOUTH_NEUTRAL_SPREAD_X_NORM > mouth_w / 2.0 + 5.0
    assert height * ANTERIOR_MOUTH_NEUTRAL_SPREAD_Y_NORM > mouth_h / 2.0 + 10.0
