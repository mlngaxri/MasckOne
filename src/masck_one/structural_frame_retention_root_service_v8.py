from __future__ import annotations

"""V8 same-root service-access separation gate.

V3 proves each operation clears the opposite seated hardware, while V4-V7 prove
bilateral operation corridors do not conflict. V8 closes the remaining local access gap:
the pin-withdrawal and retainer-installation corridors at each root must themselves
remain spatially separated. This reduces accidental simultaneous access and catches a
future packaging edit that makes the two service gestures occupy the same local space.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
import math

from . import structural_frame_retention_root_service as v1
from . import structural_frame_retention_root_service_v6 as v6
from . import structural_frame_retention_root_service_v7 as v7
from .structural_frame_retention_roots import build_structural_frame_retention_roots

SCHEMA = "MASCK_ONE_STRUCTURAL_FRAME_RETENTION_ROOT_SERVICE_V8"
SUPERSEDES_SCHEMA = v7.SCHEMA
MIN_LOCAL_OPERATION_SEPARATION_MM = v1.ACCESS_CLEARANCE_MM
SYMMETRY_TOLERANCE_MM = v7.SYMMETRY_TOLERANCE_MM


class StructuralFrameRetentionRootServiceV8Error(ValueError):
    pass


def _local_access_evidence() -> tuple[tuple[tuple[str, float], ...], str]:
    roots = build_structural_frame_retention_roots()
    service = v1.build_structural_frame_retention_root_service(roots=roots)
    if len(service.paths) != 2:
        raise StructuralFrameRetentionRootServiceV8Error("exactly two bilateral service paths are required")

    records: list[tuple[str, float]] = []
    for path in service.paths:
        distance = v6._brep_distance(path.pin_withdraw_sweep, path.clip_install_sweep)
        if not math.isfinite(distance) or distance < MIN_LOCAL_OPERATION_SEPARATION_MM:
            raise StructuralFrameRetentionRootServiceV8Error(
                f"{path.root_id} pin and retainer service corridors are insufficiently separated"
            )
        records.append((path.root_id, round(distance, 12)))

    if abs(records[0][1] - records[1][1]) > SYMMETRY_TOLERANCE_MM:
        raise StructuralFrameRetentionRootServiceV8Error(
            "same-root service-access separation is not mirror-equivalent"
        )

    source = v7.build_structural_frame_retention_root_service_v7()
    payload = {
        "source_v7_evidence_sha256": source.pairwise_evidence_sha256,
        "records": [(root_id, format(distance, ".12f")) for root_id, distance in records],
        "minimum_local_operation_separation_mm": format(MIN_LOCAL_OPERATION_SEPARATION_MM, ".12f"),
        "symmetry_tolerance_mm": format(SYMMETRY_TOLERANCE_MM, ".12f"),
    }
    digest = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return tuple(records), digest


@dataclass(frozen=True, slots=True)
class StructuralFrameRetentionRootServiceV8:
    source_v7_evidence_sha256: str
    local_operation_separations_mm: tuple[tuple[str, float], ...]
    local_access_evidence_sha256: str
    physical_validation_eligible: bool = False

    def validate(self) -> "StructuralFrameRetentionRootServiceV8":
        source = v7.build_structural_frame_retention_root_service_v7()
        records, digest = _local_access_evidence()
        if self.source_v7_evidence_sha256 != source.pairwise_evidence_sha256:
            raise StructuralFrameRetentionRootServiceV8Error("source V7 service evidence is stale")
        if self.local_operation_separations_mm != records:
            raise StructuralFrameRetentionRootServiceV8Error("local service-access evidence is stale")
        if self.local_access_evidence_sha256 != digest or len(digest) != 64:
            raise StructuralFrameRetentionRootServiceV8Error("local service-access digest is stale")
        if self.physical_validation_eligible is not False:
            raise StructuralFrameRetentionRootServiceV8Error("digital service geometry is not physical evidence")
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        payload = {
            "schema": SCHEMA,
            "supersedes_schema": SUPERSEDES_SCHEMA,
            "source_v7_evidence_sha256": self.source_v7_evidence_sha256,
            "local_operation_separations_mm": [list(record) for record in self.local_operation_separations_mm],
            "minimum_local_operation_separation_mm": MIN_LOCAL_OPERATION_SEPARATION_MM,
            "symmetry_tolerance_mm": SYMMETRY_TOLERANCE_MM,
            "local_access_evidence_sha256": self.local_access_evidence_sha256,
            "criterion": "PIN_AND_RETAINER_SERVICE_GESTURES_REMAIN_LOCALLY_SEPARATED_AND_MIRROR_EQUIVALENT",
            "whole_head_removal_status": "OPEN",
            "physical_validation_eligible": self.physical_validation_eligible,
        }
        payload["manifest_sha256"] = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        return payload


def build_structural_frame_retention_root_service_v8() -> StructuralFrameRetentionRootServiceV8:
    source = v7.build_structural_frame_retention_root_service_v7()
    records, digest = _local_access_evidence()
    return StructuralFrameRetentionRootServiceV8(source.pairwise_evidence_sha256, records, digest, False).validate()
