from __future__ import annotations

"""Fail-closed treatment collision kernel successor.

This module preserves the exact collision semantics of treatment_reference_geometry
while extending the existing fallback chain to the case where OCC Common completes
but returns positive topology that cannot be healed. No collision tolerance, fuzzy
value, sampling approximation, or material omission is introduced.
"""

import math

import cadquery as cq

from . import treatment_reference_geometry as _v1


TreatmentReferenceGeometryError = _v1.TreatmentReferenceGeometryError


def _fallback_after_unusable_common_mm3(
    left: cq.Shape,
    right: cq.Shape,
    *,
    partition_depth: int,
    partition_side: str | None,
    common_error: TreatmentReferenceGeometryError,
) -> float:
    """Recover a representation failure using the existing exact Cut/partition chain."""
    try:
        return _v1._exact_cut_removed_volume_mm3(left, right)
    except TreatmentReferenceGeometryError as cut_error:
        if partition_depth >= _v1._PARTITION_MAX_DEPTH:
            raise TreatmentReferenceGeometryError(
                "exact collision verification exhausted bounded partitioning after "
                "unusable Common topology: "
                f"depth={partition_depth}, partition_side={partition_side}, "
                f"left_bbox={_v1._bbox_tuple(left)}, right_bbox={_v1._bbox_tuple(right)}; "
                f"common={common_error}; cut={cut_error}"
            ) from cut_error

        locked_partition_side = partition_side
        if locked_partition_side is None:
            locked_partition_side = (
                "right"
                if _v1._bbox_volume(right) >= _v1._bbox_volume(left)
                else "left"
            )

        source = right if locked_partition_side == "right" else left
        pieces = _v1._partition_solid_once(source)
        if locked_partition_side == "right":
            return sum(
                _pair_intersection_volume_mm3(
                    left,
                    piece,
                    partition_depth=partition_depth + 1,
                    partition_side=locked_partition_side,
                )
                for piece in pieces
            )
        return sum(
            _pair_intersection_volume_mm3(
                piece,
                right,
                partition_depth=partition_depth + 1,
                partition_side=locked_partition_side,
            )
            for piece in pieces
        )


def _pair_intersection_volume_mm3(
    left: cq.Shape,
    right: cq.Shape,
    *,
    partition_depth: int,
    partition_side: str | None,
) -> float:
    if partition_side not in {None, "left", "right"}:
        raise TreatmentReferenceGeometryError("partition side must be left, right, or None")

    lb = left.BoundingBox()
    rb = right.BoundingBox()
    if (
        lb.xmax < rb.xmin
        or rb.xmax < lb.xmin
        or lb.ymax < rb.ymin
        or rb.ymax < lb.ymin
        or lb.zmax < rb.zmin
        or rb.zmax < lb.zmin
    ):
        return 0.0

    if _v1._exact_shape_distance(left, right) > 0.0:
        return 0.0

    try:
        common = _v1._direct_common(left, right)
    except TreatmentReferenceGeometryError as common_error:
        return _fallback_after_unusable_common_mm3(
            left,
            right,
            partition_depth=partition_depth,
            partition_side=partition_side,
            common_error=common_error,
        )

    try:
        return _v1._common_positive_volume_mm3(common, left, right)
    except TreatmentReferenceGeometryError as common_error:
        return _fallback_after_unusable_common_mm3(
            left,
            right,
            partition_depth=partition_depth,
            partition_side=partition_side,
            common_error=common_error,
        )


def intersection_volume_mm3(a: cq.Shape, b: cq.Shape) -> float:
    """Return exact positive common volume, including unusable-Common recovery."""
    total = 0.0
    left_solids = a.Solids()
    right_solids = b.Solids()
    if not left_solids or not right_solids:
        return 0.0

    for left in left_solids:
        for right in right_solids:
            total += _pair_intersection_volume_mm3(
                left,
                right,
                partition_depth=0,
                partition_side=None,
            )

    if not math.isfinite(total):
        raise TreatmentReferenceGeometryError("aggregate intersection volume is nonfinite")
    return total
