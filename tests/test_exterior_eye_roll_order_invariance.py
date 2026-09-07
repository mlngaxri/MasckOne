"""Hostile topology regression for the authority 3.0 mm bilateral eye roll.

This test deliberately exercises both disjoint feature orders on the same normalized,
protected-clearance shell. It exists to distinguish an order-sensitive OpenCascade
fillet failure from an invalid protected-opening selector or invalid support body.
"""

import pytest

from masck_one.anatomy import build_facial_reference
from masck_one.authority import load_authority
from masck_one.exterior_eye_roll import (
    _fillet_protected_eye_edges_independently,
    _final_crown_face,
    _posterior_eye_support_patch,
    _single_solid,
)
from masck_one.exterior_inferior_turnover import build_inferior_turnover_exterior_shell
from masck_one.exterior_rigid_clearance import (
    build_current_protected_volumes,
    cut_rigid_hard_envelopes,
)
from masck_one.spatial import CanonicalDatums


@pytest.fixture(scope="module")
def supported_protected_shell():
    authority = load_authority()
    datums = CanonicalDatums.from_authority(authority)
    facial_reference = build_facial_reference(authority, datums)
    protected = build_current_protected_volumes(authority, facial_reference)
    base = build_inferior_turnover_exterior_shell(
        authority, facial_reference, protected
    ).val()
    wall = authority.number("geometry", "shell_nominal_wall_mm")
    radius = authority.number("geometry", "eye", "inner_edge_roll_radius_mm")
    face = _final_crown_face(authority, facial_reference)

    supported = base
    for zone in (protected.eye_left.zone, protected.eye_right.zone):
        patch = _posterior_eye_support_patch(
            face,
            wall_mm=wall,
            roll_radius_mm=radius,
            eye_width_mm=zone.envelope_width_mm,
            eye_height_mm=zone.envelope_height_mm,
            eye_x_mm=zone.center.x,
            eye_y_mm=zone.center.y,
            eye_cant_deg=zone.angle_deg,
        )
        supported = supported.fuse(patch).clean()

    cut = cut_rigid_hard_envelopes(supported, protected).val()
    return authority, protected, _single_solid(cut, "order-invariance source")


def test_bilateral_eye_roll_is_not_feature_order_dependent(supported_protected_shell):
    authority, protected, source = supported_protected_shell
    radius = authority.number("geometry", "eye", "inner_edge_roll_radius_mm")
    left = protected.eye_left.zone
    right = protected.eye_right.zone

    left_first = _fillet_protected_eye_edges_independently(
        source, roll_radius_mm=radius, eye_zones=(left, right)
    )
    right_first = _fillet_protected_eye_edges_independently(
        source, roll_radius_mm=radius, eye_zones=(right, left)
    )

    assert left_first.isValid() and right_first.isValid()
    assert len(left_first.Solids()) == len(right_first.Solids()) == 1
    assert float(left_first.Volume()) == pytest.approx(
        float(right_first.Volume()), rel=0.0, abs=1e-5
    )
    for a, b in zip(left_first.BoundingBox().toTuple(), right_first.BoundingBox().toTuple()):
        assert float(a) == pytest.approx(float(b), rel=0.0, abs=1e-5)
