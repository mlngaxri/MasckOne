from __future__ import annotations

"""Robust reference-geometry helpers for treatment motion verification.

Manufactured treatment parts remain strict positive B-rep solids elsewhere. Motion
and service sweeps are reference geometry: they are allowed to be compounds of
independent positive-volume pieces and must never be Boolean-fused merely to make a
single review body.

OpenCascade can emit locally invalid solids when a curved face is linearly swept, and
can also return an invalid common at tangential contact. Reference pieces are therefore
shape-healed before use. Collision remains fail-closed for any finite positive common
that cannot be healed to valid B-rep topology.
"""

import math

import cadquery as cq
from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism
from OCP.ShapeFix import ShapeFix_Shape
from OCP.gp import gp_Vec


class TreatmentReferenceGeometryError(ValueError):
    pass


def _heal(shape: cq.Shape) -> cq.Shape:
    """Apply OpenCascade's topology repair without changing nominal design intent."""
    if shape.isValid():
        return shape
    fixer = ShapeFix_Shape(shape.wrapped)
    fixer.Perform()
    healed = cq.Shape.cast(fixer.Shape())
    return healed


def _positive_valid_solids(shape: cq.Shape) -> list[cq.Shape]:
    """Return valid positive solids, healing the aggregate once when required."""
    candidate = _heal(shape)
    solids = candidate.Solids()
    out: list[cq.Shape] = []
    for solid in solids:
        healed = _heal(solid)
        volume = float(healed.Volume()) if healed.Solids() else 0.0
        if not math.isfinite(volume):
            raise TreatmentReferenceGeometryError("reference solid volume is nonfinite")
        if volume <= 0.0:
            continue
        if not healed.isValid():
            raise TreatmentReferenceGeometryError("positive reference solid cannot be healed")
        out.extend(healed.Solids())
    return out


def translation_reference_compound(
    shape: cq.Shape,
    travel: tuple[float, float, float],
) -> cq.Compound:
    """Return a conservative Boolean-free envelope for one rigid translation."""
    if not shape.isValid() or not shape.Solids():
        raise TreatmentReferenceGeometryError("reference sweep source must be valid positive geometry")
    if not all(math.isfinite(float(value)) for value in travel):
        raise TreatmentReferenceGeometryError("reference sweep travel must be finite")

    pieces: list[cq.Shape] = []
    for endpoint in (shape, shape.translate(travel)):
        pieces.extend(_positive_valid_solids(endpoint))

    for face in shape.Faces():
        prism = cq.Shape.cast(
            BRepPrimAPI_MakePrism(face.wrapped, gp_Vec(*travel)).Shape()
        )
        # Faces parallel to travel legitimately generate no positive swept volume.
        pieces.extend(_positive_valid_solids(prism))

    if not pieces:
        raise TreatmentReferenceGeometryError("reference translation envelope is empty")
    compound = cq.Compound.makeCompound(pieces)
    if not compound.Solids():
        raise TreatmentReferenceGeometryError("reference translation envelope has no positive solids")
    for solid in compound.Solids():
        volume = float(solid.Volume())
        if not solid.isValid() or not math.isfinite(volume) or volume <= 0.0:
            raise TreatmentReferenceGeometryError("reference translation envelope contains invalid material")
    return compound


def intersection_volume_mm3(a: cq.Shape, b: cq.Shape) -> float:
    """Return positive common volume using only solid-to-solid Boolean operands.

    Boundary-only or topologically empty commons contribute zero. Any common with
    finite positive volume must heal to valid B-rep topology or the check fails.
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
            except Exception as exc:
                raise TreatmentReferenceGeometryError("solid-pair intersection kernel failure") from exc

            raw_solids = common.Solids()
            if not raw_solids:
                continue
            for raw in raw_solids:
                raw_volume = max(0.0, float(raw.Volume()))
                if not math.isfinite(raw_volume):
                    raise TreatmentReferenceGeometryError("intersection volume is nonfinite")
                if raw_volume <= 0.0:
                    continue
                solid = _heal(raw)
                volume = max(0.0, float(solid.Volume()))
                if not math.isfinite(volume):
                    raise TreatmentReferenceGeometryError("healed intersection volume is nonfinite")
                if volume <= 0.0:
                    continue
                if not solid.isValid():
                    raise TreatmentReferenceGeometryError("positive common cannot be healed to valid solid")
                total += volume

    if not math.isfinite(total):
        raise TreatmentReferenceGeometryError("aggregate intersection volume is nonfinite")
    return total
