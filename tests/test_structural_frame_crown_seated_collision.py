from __future__ import annotations

import pytest

from masck_one.structural_frame_crown_support import build_structural_frame_crown_support


_TOL_MM3 = 1e-7


def _intersection_mm3(a, b) -> float:
    common = a.intersect(b).val()
    assert common.isValid(), "crown/pin intersection proof must produce valid B-rep evidence"
    volume = float(common.Volume())
    assert volume >= 0.0
    return volume


def test_seated_capture_pins_do_not_intersect_one_piece_crown_support() -> None:
    architecture = build_structural_frame_crown_support()
    for attachment in architecture.attachments:
        intersection = _intersection_mm3(attachment.capture_pin, architecture.crown_support)
        assert intersection <= _TOL_MM3, (
            f"{attachment.side} seated capture pin intersects crown support by "
            f"{intersection:.8f} mm^3"
        )
