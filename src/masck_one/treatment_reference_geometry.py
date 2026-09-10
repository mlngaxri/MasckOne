from __future__ import annotations

"""Robust reference-geometry helpers for treatment motion verification.

Manufactured treatment parts remain strict positive B-rep solids elsewhere. Motion
and service sweeps are reference geometry: they are allowed to be compounds of
independent positive-volume pieces and must never be Boolean-fused merely to make a
single review body.

A rigid translation sweep is represented by the two endpoint solids plus positive
face-prism contributions. Faces whose translation is analytically tangent to their
surface do not generate 3-D swept volume and are excluded before OpenCascade prism
construction. This prevents mathematically zero-volume planar/cylindrical side sweeps
from being misreported as tiny invalid positive solids by the kernel. Positive swept
material is never discarded based on its volume.

Trimmed faces are prism-swept with OpenCascade canonicalization disabled. OCP 7.9.3.1
can otherwise replace a valid trimmed cylindrical sweep with an invalid canonicalized
solid even though the non-canonical prism is valid and has the same positive volume.
Disabling that representation rewrite preserves the exact source face and translation;
it does not heal, approximate, omit, or enlarge swept geometry.

Collision common is evaluated with OpenCascade's exact BRepAlgoAPI Common operator.
If the compact two-shape constructor does not complete, the same solid pair is retried
through explicit argument/tool lists with parallel execution enabled. No fuzzy value,
geometric tolerance expansion, sampling approximation, or collision threshold change
is introduced. Any finite positive common that cannot be healed remains a hard failure.
"""

import math

import cadquery as cq
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism
from OCP.ShapeFix import ShapeFix_Shape
from OCP.TopTools import TopTools_ListOfShape
from OCP.gp import gp_Vec


_GEOMETRIC_DIRECTION_TOL = 1e-12


class TreatmentReferenceGeometryError(ValueError):
    pass


def _heal(shape: cq.Shape) -> cq.Shape:
    if shape.isValid():
        return shape
    fixer = ShapeFix_Shape(shape.wrapped)
    fixer.Perform()
    return cq.Shape.cast(fixer.Shape())


def _positive_valid_solids(shape: cq.Shape) -> list[cq.Shape]:
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


def _unit_alignment(first: cq.Vector, second: cq.Vector) -> float:
    first_length = float(first.Length)
    second_length = float(second.Length)
    if first_length <= 0.0 or second_length <= 0.0:
        raise TreatmentReferenceGeometryError("direction vectors must be positive length")
    return abs(float(first.dot(second))) / (first_length * second_length)


def _face_translation_is_tangent(
    face: cq.Face,
    travel_vector: cq.Vector,
) -> bool:
    """Return True only for analytically zero-volume planar/cylindrical sweeps.

    For a planar face, translation in its plane has zero swept volume. For a
    cylindrical face, translation parallel to the cylinder axis is tangent everywhere
    and likewise contributes no 3-D prism. The test samples the face center and edge
    centers and requires every available normal to be orthogonal to travel. Other
    surface classes are never discarded by this classifier.
    """
    if face.geomType() not in {"PLANE", "CYLINDER"}:
        return False

    sample_points = [face.Center(), *(edge.Center() for edge in face.Edges())]
    alignments: list[float] = []
    for point in sample_points:
        try:
            normal = face.normalAt(point)
        except Exception:
            continue
        alignments.append(_unit_alignment(normal, travel_vector))

    return bool(alignments) and max(alignments) <= _GEOMETRIC_DIRECTION_TOL


def translation_reference_compound(
    shape: cq.Shape,
    travel: tuple[float, float, float],
) -> cq.Compound:
    """Return a Boolean-free continuous envelope for one rigid translation."""
    if not shape.isValid() or not shape.Solids():
        raise TreatmentReferenceGeometryError(
            "reference sweep source must be valid positive geometry"
        )
    if not all(math.isfinite(float(value)) for value in travel):
        raise TreatmentReferenceGeometryError("reference sweep travel must be finite")

    travel_vector = cq.Vector(*travel)
    if float(travel_vector.Length) <= 0.0:
        raise TreatmentReferenceGeometryError("reference sweep travel must be nonzero")

    pieces: list[cq.Shape] = []
    for endpoint in (shape, shape.translate(travel)):
        pieces.extend(_positive_valid_solids(endpoint))

    swept_face_count = 0
    tangent_face_count = 0
    for face in shape.Faces():
        if _face_translation_is_tangent(face, travel_vector):
            tangent_face_count += 1
            continue
        # Canonize=False is intentional. On OCP 7.9.3.1, canonicalization of some
        # valid trimmed cylindrical faces in the fused moving-output linkage creates
        # invalid positive solids. The non-canonical prism preserves the exact face
        # trim and translation and remains valid; no geometric gate is relaxed.
        prism = cq.Shape.cast(
            BRepPrimAPI_MakePrism(
                face.wrapped,
                gp_Vec(*travel),
                False,
                False,
            ).Shape()
        )
        positive = _positive_valid_solids(prism)
        if positive:
            swept_face_count += 1
            pieces.extend(positive)

    if not pieces:
        raise TreatmentReferenceGeometryError("reference translation envelope is empty")
    if swept_face_count == 0 and tangent_face_count == 0:
        raise TreatmentReferenceGeometryError(
            "reference translation produced no positive face sweep"
        )

    compound = cq.Compound.makeCompound(pieces)
    if not compound.Solids():
        raise TreatmentReferenceGeometryError(
            "reference translation envelope has no positive solids"
        )
    for solid in compound.Solids():
        volume = float(solid.Volume())
        if not solid.isValid() or not math.isfinite(volume) or volume <= 0.0:
            raise TreatmentReferenceGeometryError(
                "reference translation envelope contains invalid material"
            )
    return compound


def _explicit_list_common(left: cq.Shape, right: cq.Shape) -> cq.Shape:
    """Run the same exact Common through explicit OCC argument/tool lists.

    This is an execution-path fallback only. It intentionally does not set a fuzzy
    value or alter either operand. Parallel mode changes scheduling, not geometry.
    """
    arguments = TopTools_ListOfShape()
    arguments.Append(left.wrapped)
    tools = TopTools_ListOfShape()
    tools.Append(right.wrapped)

    operation = BRepAlgoAPI_Common()
    operation.SetArguments(arguments)
    operation.SetTools(tools)
    operation.SetRunParallel(True)
    operation.Build()
    if not operation.IsDone():
        raise TreatmentReferenceGeometryError(
            "explicit-list OCC common did not complete: "
            f"left_bbox={_bbox_tuple(left)}, right_bbox={_bbox_tuple(right)}"
        )
    return cq.Shape.cast(operation.Shape())


def _direct_common(left: cq.Shape, right: cq.Shape) -> cq.Shape:
    try:
        operation = BRepAlgoAPI_Common(left.wrapped, right.wrapped)
        operation.Build()
    except Exception:
        return _explicit_list_common(left, right)
    if not operation.IsDone():
        return _explicit_list_common(left, right)
    return cq.Shape.cast(operation.Shape())


def _bbox_tuple(shape: cq.Shape) -> tuple[float, float, float, float, float, float]:
    bb = shape.BoundingBox()
    return (bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax)


def intersection_volume_mm3(a: cq.Shape, b: cq.Shape) -> float:
    """Return positive common volume using exact OCC solid-to-solid operands.

    Boundary-only or topologically empty commons contribute zero. Any common with
    finite positive volume must heal to valid B-rep topology or the check fails.
    The explicit-list retry is the same Boolean operation on the same operands and
    does not relax collision criteria.
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

            common = _direct_common(left, right)
            raw_solids = common.Solids()
            if not raw_solids:
                continue
            for raw in raw_solids:
                raw_volume = max(0.0, float(raw.Volume()))
                if not math.isfinite(raw_volume):
                    raise TreatmentReferenceGeometryError(
                        "intersection volume is nonfinite"
                    )
                if raw_volume <= 0.0:
                    continue
                solid = _heal(raw)
                volume = max(0.0, float(solid.Volume()))
                if not math.isfinite(volume):
                    raise TreatmentReferenceGeometryError(
                        "healed intersection volume is nonfinite"
                    )
                if volume <= 0.0:
                    continue
                if not solid.isValid():
                    raise TreatmentReferenceGeometryError(
                        "positive common cannot be healed to valid solid: "
                        f"raw_volume_mm3={raw_volume:.12g}, "
                        f"left_bbox={_bbox_tuple(left)}, right_bbox={_bbox_tuple(right)}"
                    )
                total += volume

    if not math.isfinite(total):
        raise TreatmentReferenceGeometryError(
            "aggregate intersection volume is nonfinite"
        )
    return total
