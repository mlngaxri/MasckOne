from __future__ import annotations

import pytest

from masck_one.anatomy import (
    BilateralLandmarkPair,
    FacialReferenceError,
    PlanarLandmark,
    build_facial_reference,
)
from masck_one.authority import load_authority
from masck_one.spatial import CanonicalDatums, Point2


def test_reference_uses_only_current_authority_landmarks():
    authority = load_authority()
    reference = build_facial_reference(authority)

    ids = {landmark.id for landmark in reference.landmarks}
    assert ids == {
        "MASCK_ONE-LMK-EYE-LEFT-CENTER",
        "MASCK_ONE-LMK-EYE-RIGHT-CENTER",
        "MASCK_ONE-LMK-NOSTRIL-LEFT-CENTER",
        "MASCK_ONE-LMK-NOSTRIL-RIGHT-CENTER",
        "MASCK_ONE-LMK-MOUTH-CENTER",
    }


def test_reference_preserves_authority_coordinates_exactly():
    authority = load_authority()
    reference = build_facial_reference(authority)

    assert reference.eye_pair.left.point_xy == Point2(-31.5, 35.0)
    assert reference.eye_pair.right.point_xy == Point2(31.5, 35.0)
    assert reference.nostril_pair.left.point_xy == Point2(-10.5, -7.5)
    assert reference.nostril_pair.right.point_xy == Point2(10.5, -7.5)
    assert reference.mouth_center.point_xy == Point2(0.0, -50.0)


def test_reference_preserves_authority_status_and_provenance():
    reference = build_facial_reference(load_authority())

    for landmark in reference.landmarks:
        assert landmark.authority_status == "CAD_BASELINE"
        assert landmark.source_path.startswith("geometry.")


def test_bilateral_pairs_are_symmetric_about_canonical_sagittal_plane():
    reference = build_facial_reference(load_authority())
    datums = CanonicalDatums.from_authority(load_authority())

    for pair in (reference.eye_pair, reference.nostril_pair):
        left = pair.left.as_projected_point3()
        mirrored = datums.mirror_sagittal(left)
        assert mirrored.x == pytest.approx(pair.right.point_xy.x)
        assert mirrored.y == pytest.approx(pair.right.point_xy.y)


def test_derived_metrics_are_exactly_derived_not_independently_stored():
    reference = build_facial_reference(load_authority())
    metrics = reference.metrics

    assert metrics.interpupillary_center_spacing_mm == pytest.approx(63.0)
    assert metrics.nostril_center_spacing_mm == pytest.approx(21.0)
    assert metrics.eye_line_y_mm == pytest.approx(35.0)
    assert metrics.nostril_line_y_mm == pytest.approx(-7.5)
    assert metrics.mouth_center_y_mm == pytest.approx(-50.0)
    assert metrics.eye_to_nostril_line_vertical_mm == pytest.approx(42.5)
    assert metrics.nostril_to_mouth_center_vertical_mm == pytest.approx(42.5)
    assert metrics.eye_to_mouth_center_vertical_mm == pytest.approx(85.0)


def test_iteration4_explicitly_does_not_claim_3d_anatomical_depth():
    reference = build_facial_reference(load_authority())

    assert reference.unresolved_3d_landmarks() == tuple(landmark.id for landmark in reference.landmarks)
    assert all(not landmark.has_resolved_depth for landmark in reference.landmarks)


def test_projected_point3_requires_explicit_reference_plane_semantics():
    landmark = build_facial_reference(load_authority()).mouth_center

    projected = landmark.as_projected_point3(z_reference_mm=12.5)
    assert projected.as_tuple() == (0.0, -50.0, 12.5)
    assert landmark.has_resolved_depth is False


def test_left_landmark_must_have_negative_x():
    with pytest.raises(FacialReferenceError):
        PlanarLandmark(
            id="BAD-LEFT",
            anatomical_name="invalid left reference",
            point_xy=Point2(1.0, 2.0),
            authority_status="CAD_BASELINE",
            source_path="test",
            bilateral_group="PAIR",
            side="left",
        )


def test_midline_landmark_must_lie_on_sagittal_plane():
    with pytest.raises(FacialReferenceError):
        PlanarLandmark(
            id="BAD-MIDLINE",
            anatomical_name="invalid midline reference",
            point_xy=Point2(0.5, 2.0),
            authority_status="CAD_BASELINE",
            source_path="test",
            side="midline",
        )


def test_asymmetric_pair_is_rejected_in_neutral_cad_baseline():
    left = PlanarLandmark(
        id="LEFT",
        anatomical_name="left",
        point_xy=Point2(-10.0, 5.0),
        authority_status="CAD_BASELINE",
        source_path="test.left",
        bilateral_group="PAIR",
        side="left",
    )
    right = PlanarLandmark(
        id="RIGHT",
        anatomical_name="right",
        point_xy=Point2(11.0, 5.0),
        authority_status="CAD_BASELINE",
        source_path="test.right",
        bilateral_group="PAIR",
        side="right",
    )

    with pytest.raises(FacialReferenceError):
        BilateralLandmarkPair("PAIR", left, right)
