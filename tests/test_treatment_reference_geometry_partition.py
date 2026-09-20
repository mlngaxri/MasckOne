from __future__ import annotations

import cadquery as cq
import pytest

import masck_one.treatment_reference_geometry as reference_geometry
from masck_one.treatment_reference_geometry import (
    TreatmentReferenceGeometryError,
    _bbox_volume,
    _partition_solid_once,
    intersection_volume_mm3,
)


def _box(x: float, y: float, z: float, center_x: float = 0.0) -> cq.Shape:
    return (
        cq.Workplane("XY")
        .box(x, y, z, centered=(True, True, True))
        .translate((center_x, 0.0, 0.0))
        .val()
    )


def test_exact_partition_conserves_positive_operand_volume():
    source = _box(10.0, 8.0, 2.0)
    pieces = _partition_solid_once(source)

    assert len(pieces) >= 2
    assert all(piece.isValid() and piece.Solids() and piece.Volume() > 0.0 for piece in pieces)
    assert sum(float(piece.Volume()) for piece in pieces) == pytest.approx(
        float(source.Volume()), abs=1e-9
    )


def test_partition_fallback_preserves_contact_and_positive_overlap_when_large_booleans_fail(monkeypatch):
    large = _box(10.0, 10.0, 1.0)
    touching = _box(1.0, 1.0, 1.0, center_x=5.5)
    penetrating = _box(1.0, 1.0, 1.0, center_x=4.75)

    original_common = reference_geometry._direct_common
    original_cut = reference_geometry._direct_cut

    def fail_large_common(left: cq.Shape, right: cq.Shape) -> cq.Shape:
        if max(_bbox_volume(left), _bbox_volume(right)) > 20.0:
            raise TreatmentReferenceGeometryError("forced pathological large Common")
        return original_common(left, right)

    def fail_large_cut(left: cq.Shape, right: cq.Shape) -> cq.Shape:
        if max(_bbox_volume(left), _bbox_volume(right)) > 20.0:
            raise TreatmentReferenceGeometryError("forced pathological large Cut")
        return original_cut(left, right)

    monkeypatch.setattr(reference_geometry, "_direct_common", fail_large_common)
    monkeypatch.setattr(reference_geometry, "_direct_cut", fail_large_cut)

    assert intersection_volume_mm3(large, touching) == 0.0
    assert intersection_volume_mm3(large, penetrating) == pytest.approx(0.75, abs=1e-9)
