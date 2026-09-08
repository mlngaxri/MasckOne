"""Non-gating diagnostic for one-feature bilateral authority eye rolls.

The production contract is the canonical sequential construction. This probe records
whether OpenCascade can also commit both disjoint 3.0 mm rolls in one feature, but a
kernel rejection is diagnostic information rather than a release failure. The actual
release regressions continue to require the canonical result to be one valid positive
solid with the protected openings preserved.
"""

import pytest

from masck_one.anatomy import build_facial_reference
from masck_one.authority import load_authority
from masck_one.exterior_eye_roll import (
    _final_crown_face,
    _posterior_eye_support_patch,
    _single_solid,
    _wearer_side_eye_edge,
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
    return authority, protected, _single_solid(cut, "simultaneous-roll source")


def test_simultaneous_bilateral_eye_roll_probe_is_non_gating(supported_protected_shell):
    authority, protected, source = supported_protected_shell
    radius = authority.number("geometry", "eye", "inner_edge_roll_radius_mm")
    edges = []
    for zone in (protected.eye_left.zone, protected.eye_right.zone):
        edges.append(
            _wearer_side_eye_edge(
                source,
                eye_width_mm=zone.envelope_width_mm,
                eye_height_mm=zone.envelope_height_mm,
                eye_x_mm=zone.center.x,
                eye_y_mm=zone.center.y,
                eye_cant_deg=zone.angle_deg,
            )
        )

    try:
        rolled = source.fillet(radius, edges).clean()
        final = _single_solid(rolled, "simultaneous bilateral eye roll")
    except Exception as exc:
        pytest.skip(
            "OpenCascade rejected optional simultaneous bilateral eye-roll probe: "
            f"{type(exc).__name__}: {exc}"
        )

    assert final.isValid()
    assert len(final.Solids()) == 1
    assert float(final.Volume()) > 0.0
