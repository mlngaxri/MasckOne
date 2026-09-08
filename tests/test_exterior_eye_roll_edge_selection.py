import pytest

from masck_one.authority import load_authority
from masck_one.exterior_eye_roll import (
    EYE_EDGE_SPAN_TOLERANCE_MM,
    EYE_ROLL_SUPPORT_BAND_MM,
    _rotated_ellipse_bbox_spans_mm,
    eye_inner_roll_manifest,
)


def test_hidden_support_perimeter_cannot_match_exact_rigid_eye_selector():
    authority = load_authority()
    visual_width, visual_height = authority.pair(
        "geometry", "eye", "visual_aperture_wh_mm"
    )
    clearance = authority.number(
        "geometry", "eye", "rigid_dynamic_keepout_clearance_mm"
    )
    cant = authority.number("geometry", "eye", "lateral_cant_deg")

    hard_width = visual_width + 2.0 * clearance
    hard_height = visual_height + 2.0 * clearance
    hard_x_span, hard_y_span = _rotated_ellipse_bbox_spans_mm(
        hard_width,
        hard_height,
        cant,
    )
    support_x_span, support_y_span = _rotated_ellipse_bbox_spans_mm(
        hard_width + 2.0 * EYE_ROLL_SUPPORT_BAND_MM,
        hard_height + 2.0 * EYE_ROLL_SUPPORT_BAND_MM,
        cant,
    )

    assert support_x_span - hard_x_span > EYE_EDGE_SPAN_TOLERANCE_MM
    assert support_y_span - hard_y_span > EYE_EDGE_SPAN_TOLERANCE_MM
    assert hard_x_span == pytest.approx(62.9319942517, abs=1e-9)
    assert hard_y_span == pytest.approx(47.0910193084, abs=1e-9)
    assert support_x_span == pytest.approx(73.9305287455, abs=1e-9)
    assert support_y_span == pytest.approx(58.0885265729, abs=1e-9)

    manifest = eye_inner_roll_manifest(authority)
    assert manifest["edge_selection_span_tolerance_mm"] == EYE_EDGE_SPAN_TOLERANCE_MM
    assert manifest["edge_selection_policy"] == (
        "CANT_AWARE_RELEASED_RIGID_HARD_ENVELOPE_BBOX_THEN_POSTERIOR_Z"
    )
    assert manifest["visible_bezel_added"] is False
