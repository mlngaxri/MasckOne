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
AABB overlap is followed by exact shape-to-shape distance: pairs with strictly positive
distance are provably disjoint and never need a Boolean common. Touching/overlapping
pairs have zero distance and still run the strict Common path. If both Common execution
paths fail on a zero-distance pair, exact BRepAlgoAPI Cut volume identities are tried
in both subtraction directions. If both subtraction directions also fail, the larger
operand is selected once, exactly clipped into non-overlapping AABB partitions whose
summed positive volume must reproduce that operand, and that same operand side remains
locked throughout recursive subdivision. This prevents recursion from switching onto
a smaller but topologically more complex swept operand after the original large source
has already been conditioned. No fuzzy value, geometric tolerance expansion, sampling
approximation, collision threshold change, or material omission is introduced; failure
after bounded exact partitioning remains a hard verification error.
"""

import math

import cadquery as cq
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common, BRepAlgoAPI_Cut
from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism
from OCP.ShapeFix import ShapeFix_Shape
from OCP.TopTools import TopTools_ListOfShape
from OCP.gp import gp_Vec


_GEOMETRIC_DIRECTION_TOL = 1e-12
_PARTITION_MAX_DEPTH = 6
_PARTITION_MARGIN_MM = 1.0
_PARTITION_VOLUME_ABS_TOL_MM3 = 1e-6
_PARTITION_VOLUME_REL_TOL = 1e-10


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
    """Run the same exact Common through explicit OCC argument/tool lists."""
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


def _explicit_list_cut(left: cq.Shape, right: cq.Shape) -> cq.Shape:
    """Run exact left-minus-right Cut through explicit OCC argument/tool lists."""
    arguments = TopTools_ListOfShape()
    arguments.Append(left.wrapped)
    tools = TopTools_ListOfShape()
    tools.Append(right.wrapped)

    operation = BRepAlgoAPI_Cut()
    operation.SetArguments(arguments)
    operation.SetTools(tools)
    operation.SetRunParallel(True)
    operation.Build()
    if not operation.IsDone():
        raise TreatmentReferenceGeometryError(
            "exact cut-volume fallback did not complete: "
            f"left_bbox={_bbox_tuple(left)}, right_bbox={_bbox_tuple(right)}"
        )
    return cq.Shape.cast(operation.Shape())


def _direct_cut(left: cq.Shape, right: cq.Shape) -> cq.Shape:
    try:
        operation = BRepAlgoAPI_Cut(left.wrapped, right.wrapped)
        operation.Build()
    except Exception:
        return _explicit_list_cut(left, right)
    if not operation.IsDone():
        return _explicit_list_cut(left, right)
    return cq.Shape.cast(operation.Shape())


def _exact_cut_removed_volume_one_way_mm3(left: cq.Shape, right: cq.Shape) -> float:
    """Return exact common volume from the one-way identity A - (A minus B)."""
    cut = _direct_cut(left, right)
    if not cut.isValid():
        cut = _heal(cut)
    if not cut.isValid():
        raise TreatmentReferenceGeometryError(
            "exact cut-volume fallback produced invalid topology: "
            f"left_bbox={_bbox_tuple(left)}, right_bbox={_bbox_tuple(right)}"
        )

    left_volume = float(left.Volume())
    remaining_volume = sum(max(0.0, float(solid.Volume())) for solid in cut.Solids())
    removed_volume = left_volume - remaining_volume
    if not all(math.isfinite(value) for value in (left_volume, remaining_volume, removed_volume)):
        raise TreatmentReferenceGeometryError("exact cut-volume fallback is nonfinite")
    if removed_volume < 0.0:
        raise TreatmentReferenceGeometryError(
            "exact cut-volume identity returned negative removed volume: "
            f"removed_mm3={removed_volume:.12g}, left_bbox={_bbox_tuple(left)}, "
            f"right_bbox={_bbox_tuple(right)}"
        )
    return removed_volume


def _exact_cut_removed_volume_mm3(left: cq.Shape, right: cq.Shape) -> float:
    """Try both exact subtraction directions for the symmetric common volume."""
    try:
        return _exact_cut_removed_volume_one_way_mm3(left, right)
    except TreatmentReferenceGeometryError as first_error:
        try:
            return _exact_cut_removed_volume_one_way_mm3(right, left)
        except TreatmentReferenceGeometryError as second_error:
            raise TreatmentReferenceGeometryError(
                "both exact cut-volume directions failed: "
                f"left_bbox={_bbox_tuple(left)}, right_bbox={_bbox_tuple(right)}; "
                f"first={first_error}; second={second_error}"
            ) from second_error


def _exact_shape_distance(left: cq.Shape, right: cq.Shape) -> float:
    """Return exact OCC minimum distance for a valid solid pair.

    A strictly positive result proves separation and can safely bypass Boolean Common.
    Zero means touching or overlap and therefore remains on the strict Common path.
    No epsilon or fuzzy tolerance is applied here.
    """
    try:
        distance = float(left.distance(right))
    except Exception as exc:
        raise TreatmentReferenceGeometryError(
            "exact OCC distance prefilter failed: "
            f"left_bbox={_bbox_tuple(left)}, right_bbox={_bbox_tuple(right)}"
        ) from exc
    if not math.isfinite(distance) or distance < 0.0:
        raise TreatmentReferenceGeometryError(
            "exact OCC distance prefilter returned invalid distance: "
            f"distance_mm={distance}, left_bbox={_bbox_tuple(left)}, "
            f"right_bbox={_bbox_tuple(right)}"
        )
    return distance


def _bbox_tuple(shape: cq.Shape) -> tuple[float, float, float, float, float, float]:
    bb = shape.BoundingBox()
    return (bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax)


def _bbox_volume(shape: cq.Shape) -> float:
    bb = shape.BoundingBox()
    spans = (bb.xmax - bb.xmin, bb.ymax - bb.ymin, bb.zmax - bb.zmin)
    if not all(math.isfinite(value) and value >= 0.0 for value in spans):
        raise TreatmentReferenceGeometryError("partition operand has invalid bounding box")
    return spans[0] * spans[1] * spans[2]


def _partition_box(
    *,
    xmin: float,
    xmax: float,
    ymin: float,
    ymax: float,
    zmin: float,
    zmax: float,
) -> cq.Shape:
    dimensions = (xmax - xmin, ymax - ymin, zmax - zmin)
    if not all(math.isfinite(value) and value > 0.0 for value in dimensions):
        raise TreatmentReferenceGeometryError("partition box dimensions must be positive finite")
    return (
        cq.Workplane("XY")
        .box(*dimensions, centered=(True, True, True))
        .translate(
            (
                (xmin + xmax) / 2.0,
                (ymin + ymax) / 2.0,
                (zmin + zmax) / 2.0,
            )
        )
        .val()
    )


def _exact_clip_to_box(source: cq.Shape, box: cq.Shape) -> list[cq.Shape]:
    """Clip one solid with a simple exact box without using monkey-patchable fallbacks."""
    try:
        operation = BRepAlgoAPI_Common(source.wrapped, box.wrapped)
        operation.Build()
    except Exception as exc:
        raise TreatmentReferenceGeometryError(
            "exact partition clip raised: "
            f"source_bbox={_bbox_tuple(source)}, box_bbox={_bbox_tuple(box)}"
        ) from exc
    if not operation.IsDone():
        raise TreatmentReferenceGeometryError(
            "exact partition clip did not complete: "
            f"source_bbox={_bbox_tuple(source)}, box_bbox={_bbox_tuple(box)}"
        )
    return _positive_valid_solids(cq.Shape.cast(operation.Shape()))


def _partition_solid_once(source: cq.Shape) -> list[cq.Shape]:
    """Split a positive solid into exact, non-overlapping AABB-clipped pieces."""
    bb = source.BoundingBox()
    spans = {
        "x": bb.xmax - bb.xmin,
        "y": bb.ymax - bb.ymin,
        "z": bb.zmax - bb.zmin,
    }
    axis = max(spans, key=spans.get)
    span = spans[axis]
    if not math.isfinite(span) or span <= 0.0:
        raise TreatmentReferenceGeometryError("cannot partition degenerate positive solid")

    margin = max(_PARTITION_MARGIN_MM, 0.05 * max(spans.values()))
    split = (
        (bb.xmin + bb.xmax) / 2.0
        if axis == "x"
        else (bb.ymin + bb.ymax) / 2.0
        if axis == "y"
        else (bb.zmin + bb.zmax) / 2.0
    )

    common = {
        "xmin": bb.xmin - margin,
        "xmax": bb.xmax + margin,
        "ymin": bb.ymin - margin,
        "ymax": bb.ymax + margin,
        "zmin": bb.zmin - margin,
        "zmax": bb.zmax + margin,
    }
    first = dict(common)
    second = dict(common)
    first[f"{axis}max"] = split
    second[f"{axis}min"] = split

    pieces = [
        piece
        for bounds in (first, second)
        for piece in _exact_clip_to_box(source, _partition_box(**bounds))
    ]
    if len(pieces) < 2:
        raise TreatmentReferenceGeometryError(
            "exact partitioning did not produce two positive operand pieces: "
            f"source_bbox={_bbox_tuple(source)}"
        )

    source_volume = float(source.Volume())
    piece_volume = sum(float(piece.Volume()) for piece in pieces)
    if not all(math.isfinite(value) and value > 0.0 for value in (source_volume, piece_volume)):
        raise TreatmentReferenceGeometryError("exact partition volume identity is nonfinite")
    allowed_delta = max(
        _PARTITION_VOLUME_ABS_TOL_MM3,
        _PARTITION_VOLUME_REL_TOL * source_volume,
    )
    if abs(piece_volume - source_volume) > allowed_delta:
        raise TreatmentReferenceGeometryError(
            "exact partition pieces do not conserve operand volume: "
            f"source_mm3={source_volume:.12g}, pieces_mm3={piece_volume:.12g}, "
            f"delta_mm3={piece_volume - source_volume:.12g}, allowed_mm3={allowed_delta:.12g}"
        )
    return pieces


def _common_positive_volume_mm3(common: cq.Shape, left: cq.Shape, right: cq.Shape) -> float:
    total = 0.0
    raw_solids = common.Solids()
    if not raw_solids:
        return 0.0
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
            raise TreatmentReferenceGeometryError(
                "positive common cannot be healed to valid solid: "
                f"raw_volume_mm3={raw_volume:.12g}, "
                f"left_bbox={_bbox_tuple(left)}, right_bbox={_bbox_tuple(right)}"
            )
        total += volume
    return total


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

    if _exact_shape_distance(left, right) > 0.0:
        return 0.0

    try:
        common = _direct_common(left, right)
    except TreatmentReferenceGeometryError as common_error:
        try:
            return _exact_cut_removed_volume_mm3(left, right)
        except TreatmentReferenceGeometryError as cut_error:
            if partition_depth >= _PARTITION_MAX_DEPTH:
                raise TreatmentReferenceGeometryError(
                    "exact collision verification exhausted bounded partitioning: "
                    f"depth={partition_depth}, partition_side={partition_side}, "
                    f"left_bbox={_bbox_tuple(left)}, right_bbox={_bbox_tuple(right)}; "
                    f"common={common_error}; cut={cut_error}"
                ) from cut_error

            locked_partition_side = partition_side
            if locked_partition_side is None:
                locked_partition_side = (
                    "right" if _bbox_volume(right) >= _bbox_volume(left) else "left"
                )

            source = right if locked_partition_side == "right" else left
            pieces = _partition_solid_once(source)
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

    return _common_positive_volume_mm3(common, left, right)


def intersection_volume_mm3(a: cq.Shape, b: cq.Shape) -> float:
    """Return positive common volume using exact OCC solid-to-solid operands.

    Boundary-only or topologically empty commons contribute zero. After cheap AABB
    rejection, an exact OCC minimum-distance check skips only pairs with strictly
    positive separation. Touching/overlapping pairs still execute exact Common. If
    Common and both exact Cut identities cannot execute, bounded exact partitioning of
    the initially larger operand conditions the same geometry into smaller
    non-overlapping pieces whose volume identity is proved before recursion. The
    selected partition side remains fixed throughout that recursion so a complex
    opposite operand is never selected merely because a conditioned piece became
    smaller. Collision criteria are unchanged.
    """
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
        raise TreatmentReferenceGeometryError(
            "aggregate intersection volume is nonfinite"
        )
    return total