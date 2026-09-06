from __future__ import annotations

"""Traversal-order-independent OpenCascade geometry identity for collision evidence.

Equivalent regenerated B-reps can serialize to different byte streams. Collision release
provenance therefore fingerprints realized topology and quantized geometric metrics,
not raw exportBrep() bytes. This is digital identity only, never a manufacturing or
physical tolerance.
"""

from hashlib import sha256
import json
import math

import cadquery as cq

SCHEMA = "MASCK_ONE_OCC_GEOMETRY_FINGERPRINT_V1"
GEOMETRY_DECIMALS = 8


class CollisionGeometryFingerprintError(ValueError):
    pass


def _quantized(value: object) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise CollisionGeometryFingerprintError("geometry fingerprint requires finite numeric metrics") from exc
    if not math.isfinite(number):
        raise CollisionGeometryFingerprintError("geometry fingerprint encountered a nonfinite metric")
    result = round(number, GEOMETRY_DECIMALS)
    return 0.0 if result == 0.0 else result


def _point_payload(point: object) -> list[float]:
    try:
        return [_quantized(point.x), _quantized(point.y), _quantized(point.z)]
    except AttributeError as exc:
        raise CollisionGeometryFingerprintError("geometry fingerprint requires 3D point coordinates") from exc


def _bbox_payload(shape: object) -> list[float]:
    try:
        box = shape.BoundingBox()
    except (AttributeError, TypeError, ValueError) as exc:
        raise CollisionGeometryFingerprintError("geometry fingerprint requires a valid bounding box") from exc
    return [
        _quantized(box.xmin),
        _quantized(box.ymin),
        _quantized(box.zmin),
        _quantized(box.xmax),
        _quantized(box.ymax),
        _quantized(box.zmax),
    ]


def _record_key(record: object) -> str:
    return json.dumps(record, sort_keys=True, separators=(",", ":"), allow_nan=False)


def geometry_fingerprint_payload(workplane: cq.Workplane) -> dict[str, object]:
    if type(workplane) is not cq.Workplane:
        raise CollisionGeometryFingerprintError("geometry fingerprint requires exact CadQuery Workplane geometry")
    shape = workplane.val()
    solids = shape.Solids()
    if not shape.isValid() or not solids:
        raise CollisionGeometryFingerprintError("geometry fingerprint requires valid solid geometry")

    solid_records: list[dict[str, object]] = []
    for body in solids:
        face_records: list[dict[str, object]] = []
        for face in body.Faces():
            face_records.append(
                {
                    "geom_type": str(face.geomType()),
                    "area_mm2": _quantized(face.Area()),
                    "center_mm": _point_payload(face.Center()),
                    "bbox_mm": _bbox_payload(face),
                    "edge_count": len(face.Edges()),
                    "vertex_count": len(face.Vertices()),
                }
            )
        face_records.sort(key=_record_key)

        edge_records: list[dict[str, object]] = []
        for edge in body.Edges():
            edge_records.append(
                {
                    "geom_type": str(edge.geomType()),
                    "length_mm": _quantized(edge.Length()),
                    "center_mm": _point_payload(edge.Center()),
                    "bbox_mm": _bbox_payload(edge),
                    "vertex_count": len(edge.Vertices()),
                }
            )
        edge_records.sort(key=_record_key)

        vertex_records = sorted(
            (_point_payload(vertex.Center()) for vertex in body.Vertices()),
            key=lambda point: tuple(point),
        )
        solid_records.append(
            {
                "volume_mm3": _quantized(body.Volume()),
                "center_mm": _point_payload(body.Center()),
                "bbox_mm": _bbox_payload(body),
                "shell_count": len(body.Shells()),
                "face_count": len(body.Faces()),
                "edge_count": len(body.Edges()),
                "vertex_count": len(body.Vertices()),
                "faces": face_records,
                "edges": edge_records,
                "vertices_mm": vertex_records,
            }
        )
    solid_records.sort(key=_record_key)
    return {
        "schema": SCHEMA,
        "quantization_decimals": GEOMETRY_DECIMALS,
        "solid_count": len(solid_records),
        "solids": solid_records,
    }


def geometry_fingerprint_sha256(workplane: cq.Workplane) -> str:
    payload = geometry_fingerprint_payload(workplane)
    return sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()
