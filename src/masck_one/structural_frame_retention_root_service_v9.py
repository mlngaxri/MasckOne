from __future__ import annotations

"""V9 service-corridor reach gate.

V8 proves the two local service gestures remain separated. V9 additionally proves that
each realized corridor still provides the full authored withdrawal/install travel. This
catches a future CAD edit that leaves a collision-free but truncated service gesture.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
import math

from . import structural_frame_retention_root_service as v1
from . import structural_frame_retention_root_service_v8 as v8
from .structural_frame_retention_roots import build_structural_frame_retention_roots

SCHEMA = "MASCK_ONE_STRUCTURAL_FRAME_RETENTION_ROOT_SERVICE_V9"
SUPERSEDES_SCHEMA = v8.SCHEMA
GEOMETRY_TOLERANCE_MM = 1e-6


class StructuralFrameRetentionRootServiceV9Error(ValueError):
    pass


def _axis_span(shape, axis: str) -> float:
    bb = shape.val().BoundingBox()
    span = {"x": bb.xlen, "y": bb.ylen, "z": bb.zlen}[axis]
    if not math.isfinite(span) or span <= 0.0:
        raise StructuralFrameRetentionRootServiceV9Error("service-corridor span must be finite and positive")
    return float(span)


def _reach_evidence() -> tuple[tuple[tuple[str, float, float], ...], str]:
    roots = build_structural_frame_retention_roots()
    service = v1.build_structural_frame_retention_root_service(roots=roots)
    if len(service.paths) != 2:
        raise StructuralFrameRetentionRootServiceV9Error("exactly two bilateral service paths are required")

    records = []
    for path in service.paths:
        pin_reach = _axis_span(path.pin_withdraw_sweep, "y")
        retainer_reach = _axis_span(path.clip_install_sweep, "z")
        if pin_reach + GEOMETRY_TOLERANCE_MM < v1.PIN_WITHDRAW_EXTENSION_MM:
            raise StructuralFrameRetentionRootServiceV9Error(f"{path.root_id} pin service corridor is truncated")
        if retainer_reach + GEOMETRY_TOLERANCE_MM < v1.CLIP_RADIAL_EXTENSION_MM:
            raise StructuralFrameRetentionRootServiceV9Error(f"{path.root_id} retainer service corridor is truncated")
        records.append((path.root_id, round(pin_reach, 12), round(retainer_reach, 12)))

    if abs(records[0][1] - records[1][1]) > GEOMETRY_TOLERANCE_MM or abs(records[0][2] - records[1][2]) > GEOMETRY_TOLERANCE_MM:
        raise StructuralFrameRetentionRootServiceV9Error("bilateral service reach is not mirror-equivalent")

    source = v8.build_structural_frame_retention_root_service_v8()
    payload = {
        "source_v8_evidence_sha256": source.local_access_evidence_sha256,
        "records": records,
        "required_pin_withdraw_extension_mm": v1.PIN_WITHDRAW_EXTENSION_MM,
        "required_retainer_install_extension_mm": v1.CLIP_RADIAL_EXTENSION_MM,
        "geometry_tolerance_mm": GEOMETRY_TOLERANCE_MM,
    }
    digest = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    return tuple(records), digest


@dataclass(frozen=True, slots=True)
class StructuralFrameRetentionRootServiceV9:
    source_v8_evidence_sha256: str
    service_reach_mm: tuple[tuple[str, float, float], ...]
    reach_evidence_sha256: str
    physical_validation_eligible: bool = False

    def validate(self) -> "StructuralFrameRetentionRootServiceV9":
        source = v8.build_structural_frame_retention_root_service_v8()
        records, digest = _reach_evidence()
        if self.source_v8_evidence_sha256 != source.local_access_evidence_sha256:
            raise StructuralFrameRetentionRootServiceV9Error("source V8 service evidence is stale")
        if self.service_reach_mm != records:
            raise StructuralFrameRetentionRootServiceV9Error("service reach evidence is stale")
        if self.reach_evidence_sha256 != digest or len(digest) != 64:
            raise StructuralFrameRetentionRootServiceV9Error("service reach digest is stale")
        if self.physical_validation_eligible is not False:
            raise StructuralFrameRetentionRootServiceV9Error("digital service geometry is not physical evidence")
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        payload = {
            "schema": SCHEMA,
            "supersedes_schema": SUPERSEDES_SCHEMA,
            "source_v8_evidence_sha256": self.source_v8_evidence_sha256,
            "service_reach_mm": [list(record) for record in self.service_reach_mm],
            "required_pin_withdraw_extension_mm": v1.PIN_WITHDRAW_EXTENSION_MM,
            "required_retainer_install_extension_mm": v1.CLIP_RADIAL_EXTENSION_MM,
            "reach_evidence_sha256": self.reach_evidence_sha256,
            "criterion": "SERVICE_CORRIDORS_PRESERVE_AUTHORED_TRAVEL_AND_BILATERAL_EQUIVALENCE",
            "whole_head_removal_status": "OPEN",
            "physical_validation_eligible": self.physical_validation_eligible,
        }
        payload["manifest_sha256"] = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        return payload


def build_structural_frame_retention_root_service_v9() -> StructuralFrameRetentionRootServiceV9:
    source = v8.build_structural_frame_retention_root_service_v8()
    records, digest = _reach_evidence()
    return StructuralFrameRetentionRootServiceV9(source.local_access_evidence_sha256, records, digest, False).validate()
