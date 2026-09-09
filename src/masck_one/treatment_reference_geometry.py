from __future__ import annotations

"""Robust reference-geometry helpers for treatment motion verification.

Manufactured treatment parts remain strict positive B-rep solids elsewhere. Motion
and service sweeps are reference geometry: they are allowed to be compounds of
independent positive-volume pieces and must never be Boolean-fused merely to make a
single review body.

The collision helper deliberately evaluates solid pairs. OpenCascade can represent a
boundary-only common as an invalid/empty aggregate even though there is no positive
intersection volume. Such a result is zero-volume contact, not a manufactured-solid
failure. Any positive-volume returned solid is still required to be valid and finite.
"""

import math

import cadquery as cq
from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism
from OCP.gp import gp_Vec


class TreatmentReferenceGeometryError(ValueError):
    pass


def translation_reference_compound(
    shape: cq.Shape,
    travel: tuple[float, float, float],
) -> cq.Compound:
    """Return a conservative Boolean-free envelope for one rigid translation."""
    if not shape.isValid() or not shape.Solids():
        raise TreatmentReferenceGeometryError("reference sweep source must be valid positive geometry")
    if not all(math.isfinite(float(value)) for value in travel):
        raise TreatmentReferenceGeometryError("reference sweep travel must be finite")

    pieces: list[cq.Shape] = [shape, shape.translate(travel)]
    for face in shape.Faces():
        prism = cq.Shape.cast(
            BRepPrimAPI_MakePrism(face.wrapped, gp_Vec(*travel)).Shape()
        )
        pieces.extend(prism.Solids())

    positive = [piece for piece in pieces if piece.Solids() and float(piece.Volume()) > 0.0]
    compound = cq.Compound.makeCompound(positive)
    if not compound.Solids():
        raise TreatmentReferenceGeometryError("reference translation envelope is empty")
    for solid in compound.Solids():
        if not solid.isValid() or not math.isfinite(float(solid.Volume())) or float(solid.Volume()) <= 0.0:
            raise TreatmentReferenceGeometryError("reference translation envelope contains invalid material")
    return compound


def intersection_volume_mm3(a: cq.Shape, b: cq.Shape) -> float:
    """Return positive common volume using only solid-to-solid Boolean operands.

    Boundary-only or topologically empty commons contribute zero. Positive returned
    solids remain fail-closed: every one must be valid, finite and non-negative.
    """
    total = 0.0
    left_solids = a.Solids()
    right_solids = b.Solids()
    if not left_solids or not right_solids:
        return 0.0

    for left in left_solids:
        lb = left.BoundingBox()
        for right in right_solids:
            rb = right.BoundingBox()
            if (
                lb.xmax < rb.xmin
                or rb.xmax < lb.xmin
                or lb.ymax < rb.ymin
                or rb.ymax < lb.ymin
                or lb.zmax < rb.zmin
                or rb.zmax < lb.zmin
            ):
                continue
            try:
                common = left.intersect(right)
                solids = common.Solids()
            except Exception as exc:
                raise TreatmentReferenceGeometryError("solid-pair intersection kernel failure") from exc

            # OpenCascade may return an invalid aggregate for an empty/tangent common.
            # With no positive-volume solids there is no volumetric collision to count.
            if not solids:
                continue
            for solid in solids:
                if not solid.isValid():
                    raise TreatmentReferenceGeometryError("positive common contains invalid solid")
                volume = max(0.0, float(solid.Volume()))
                if not math.isfinite(volume):
                    raise TreatmentReferenceGeometryError("intersection volume is nonfinite")
                total += volume

    if not math.isfinite(total):
        raise TreatmentReferenceGeometryError("aggregate intersection volume is nonfinite")
    return total
