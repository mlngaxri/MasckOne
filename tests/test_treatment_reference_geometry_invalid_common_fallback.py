from __future__ import annotations

import cadquery as cq
import pytest

import masck_one.treatment_reference_geometry as reference_geometry
from masck_one.treatment_reference_geometry import (
    TreatmentReferenceGeometryError,
    intersection_volume_mm3,
)


def _box(center_x: float) -> cq.Shape:
    return (
        cq.Workplane("XY")
        .box(1.0, 1.0, 1.0)
        .translate((center_x, 0.0, 0.0))
        .val()
    )


def test_invalid_positive_common_uses_exact_cut_identity_without_hiding_overlap(monkeypatch):
    """A completed Common with unusable positive topology must not end verification.

    The terminal service sweep can produce a tiny positive Common that OCC cannot heal.
    That is a Boolean representation failure, not permission to discard material. The
    collision kernel already has an exact Cut-volume identity for Common execution
    failures; this regression requires the same fail-closed path when Common executes
    but its positive result is unusable.
    """
    left = _box(0.0)
    right = _box(0.75)
    original_positive_volume = reference_geometry._common_positive_volume_mm3
    calls = 0

    def reject_first_common_result(common: cq.Shape, a: cq.Shape, b: cq.Shape) -> float:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise TreatmentReferenceGeometryError(
                "forced unusable positive Common topology"
            )
        return original_positive_volume(common, a, b)

    monkeypatch.setattr(
        reference_geometry,
        "_common_positive_volume_mm3",
        reject_first_common_result,
    )

    assert intersection_volume_mm3(left, right) == pytest.approx(0.25, abs=1e-9)


def test_invalid_positive_common_fallback_must_not_convert_contact_to_penetration(monkeypatch):
    left = _box(0.0)
    touching = _box(1.0)

    def reject_common_result(_common: cq.Shape, _a: cq.Shape, _b: cq.Shape) -> float:
        raise TreatmentReferenceGeometryError("forced unusable Common topology")

    monkeypatch.setattr(
        reference_geometry,
        "_common_positive_volume_mm3",
        reject_common_result,
    )

    assert intersection_volume_mm3(left, touching) == 0.0
