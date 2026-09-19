from __future__ import annotations

import cadquery as cq
import pytest

import masck_one.treatment_collision_kernel_v2 as kernel
import masck_one.treatment_reference_geometry as reference_geometry
from masck_one.treatment_reference_geometry import TreatmentReferenceGeometryError


def _box(center_x: float) -> cq.Shape:
    return (
        cq.Workplane("XY")
        .box(1.0, 1.0, 1.0)
        .translate((center_x, 0.0, 0.0))
        .val()
    )


def test_v2_preserves_gap_contact_and_penetration_semantics():
    base = _box(0.0)
    assert kernel.intersection_volume_mm3(base, _box(1.01)) == 0.0
    assert kernel.intersection_volume_mm3(base, _box(1.0)) == 0.0
    assert kernel.intersection_volume_mm3(base, _box(0.75)) == pytest.approx(0.25, abs=1e-9)


def test_v2_completed_but_unusable_common_uses_exact_cut_without_hiding_overlap(monkeypatch):
    left = _box(0.0)
    right = _box(0.75)

    def unusable_common(_common: cq.Shape, _left: cq.Shape, _right: cq.Shape) -> float:
        raise TreatmentReferenceGeometryError("forced unusable positive Common topology")

    monkeypatch.setattr(reference_geometry, "_common_positive_volume_mm3", unusable_common)
    assert kernel.intersection_volume_mm3(left, right) == pytest.approx(0.25, abs=1e-9)


def test_v2_unusable_common_does_not_convert_exact_contact_to_penetration(monkeypatch):
    left = _box(0.0)
    touching = _box(1.0)

    def unusable_common(_common: cq.Shape, _left: cq.Shape, _right: cq.Shape) -> float:
        raise TreatmentReferenceGeometryError("forced unusable positive Common topology")

    monkeypatch.setattr(reference_geometry, "_common_positive_volume_mm3", unusable_common)
    assert kernel.intersection_volume_mm3(left, touching) == 0.0


def test_v2_keeps_partition_side_locked_when_common_and_cut_are_unusable(monkeypatch):
    left = cq.Workplane("XY").box(4.0, 1.0, 1.0).val()
    right = cq.Workplane("XY").box(8.0, 1.0, 1.0).val()
    original_common = reference_geometry._direct_common
    original_partition = reference_geometry._partition_solid_once
    partition_sources: list[tuple[float, float]] = []

    def fail_common_until_right_piece_is_small(a: cq.Shape, b: cq.Shape) -> cq.Shape:
        bounds = b.BoundingBox()
        if bounds.xmax - bounds.xmin > 1.05:
            raise TreatmentReferenceGeometryError("forced Common failure")
        return original_common(a, b)

    def failed_cut(_left: cq.Shape, _right: cq.Shape) -> float:
        raise TreatmentReferenceGeometryError("forced Cut failure")

    def recorded_partition(source: cq.Shape) -> list[cq.Shape]:
        bounds = source.BoundingBox()
        partition_sources.append(
            (bounds.xmax - bounds.xmin, (bounds.xmin + bounds.xmax) / 2.0)
        )
        return original_partition(source)

    monkeypatch.setattr(reference_geometry, "_direct_common", fail_common_until_right_piece_is_small)
    monkeypatch.setattr(reference_geometry, "_exact_cut_removed_volume_mm3", failed_cut)
    monkeypatch.setattr(reference_geometry, "_partition_solid_once", recorded_partition)

    assert kernel.intersection_volume_mm3(left, right) == pytest.approx(4.0, abs=1e-8)
    assert partition_sources[0][0] == pytest.approx(8.0, abs=1e-9)
    assert not any(
        span == pytest.approx(4.0, abs=1e-9)
        and center == pytest.approx(0.0, abs=1e-9)
        for span, center in partition_sources[1:]
    )
