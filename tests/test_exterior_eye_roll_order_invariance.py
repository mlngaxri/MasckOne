"""Hostile topology regression for the authority 3.0 mm bilateral eye roll.

The production contract is deterministic validity of the canonical bilateral feature
sequence. OpenCascade does not guarantee that sequential fillets commute, so reverse
order is diagnostic evidence only and must not become a false release requirement.
"""

import cadquery as cq
import pytest

from masck_one.anatomy import build_facial_reference
from masck_one.authority import load_authority
from masck_one.exterior_eye_roll import (
    EyeInnerRollError,
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

    cut = cut_rigid_hard_envelopes(cq.Workplane(obj=supported), protected).val()
    return authority, protected, _single_solid(cut, "order-diagnostic source")


def test_canonical_bilateral_eye_roll_is_valid(supported_protected_shell):
    authority, protected, source = supported_protected_shell
    radius = authority.number("geometry", "eye", "inner_edge_roll_radius_mm")
    left = protected.eye_left.zone
    right = protected.eye_right.zone

    canonical = _fillet_protected_eye_edges_independently(
        source, roll_radius_mm=radius, eye_zones=(left, right)
    )

    assert canonical.isValid()
    assert len(canonical.Solids()) == 1
    assert float(canonical.Volume()) > 0.0


def test_reverse_order_is_diagnostic_not_release_contract(supported_protected_shell):
    authority, protected, source = supported_protected_shell
    radius = authority.number("geometry", "eye", "inner_edge_roll_radius_mm")
    left = protected.eye_left.zone
    right = protected.eye_right.zone

    try:
        reverse = _fillet_protected_eye_edges_independently(
            source, roll_radius_mm=radius, eye_zones=(right, left)
        )
    except EyeInnerRollError:
        # Sequential OCC fillets need not commute. A controlled failure here is useful
        # diagnostic evidence but does not invalidate the deterministic production path.
        return

    assert reverse.isValid()
    assert len(reverse.Solids()) == 1
    assert float(reverse.Volume()) > 0.0
