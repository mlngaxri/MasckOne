from __future__ import annotations

"""V6 exact B-rep clearance gate for bilateral retention-root service corridors.

V5 proves a conservative AABB separation reserve. V6 independently queries OCC for the
minimum distance between each pair of realized bilateral service solids and binds that
result to V5. This catches future geometry for which bounding-box separation no longer
represents the closest physical approach.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
import math

from . import structural_frame_retention_root_service as v1
from . import structural_frame_retention_root_service_v5 as v5
from .structural_frame_retention_roots import build_structural_frame_retention_roots

SCHEMA = "MASCK_ONE_STRUCTURAL_FRAME_RETENTION_ROOT_SERVICE_V6"
SUPERSEDES_SCHEMA = v5.SCHEMA
MIN_BREP_SERVICE_CLEARANCE_MM = v1.ACCESS_CLEARANCE_MM


class StructuralFrameRetentionRootServiceV6Error(ValueError):
    pass


def _brep_distance(first, second) -> float:
    try:
        distance = float(first.val().distance(second.val()))
    except Exception as exc:
        raise StructuralFrameRetentionRootServiceV6Error(
            "B-rep service-clearance query failed; clearance evidence is unavailable"
        ) from exc
    if not math.isfinite(distance) or distance < 0.0:
        raise StructuralFrameRetentionRootServiceV6Error(
            "B-rep service clearance must be finite and non-negative"
        )
    return distance


def _clearance_evidence() -> tuple[float, str]:
    roots = build_structural_frame_retention_roots()
    service = v1.build_structural_frame_retention_root_service(roots=roots)
    if len(service.paths) != 2:
        raise StructuralFrameRetentionRootServiceV6Error("exactly two bilateral service paths are required")
    left, right = service.paths
    checks = (
        ("pin_withdraw_vs_pin_withdraw", left.pin_withdraw_sweep, right.pin_withdraw_sweep),
        ("clip_install_vs_clip_install", left.clip_install_sweep, right.clip_install_sweep),
        ("left_pin_withdraw_vs_right_clip_install", left.pin_withdraw_sweep, right.clip_install_sweep),
        ("left_clip_install_vs_right_pin_withdraw", left.clip_install_sweep, right.pin_withdraw_sweep),
    )
    records = []
    minimum = math.inf
    for operation_pair, first, second in checks:
        distance = _brep_distance(first, second)
        if distance < MIN_BREP_SERVICE_CLEARANCE_MM:
            raise StructuralFrameRetentionRootServiceV6Error(
                f"B-rep bilateral service clearance is insufficient for {operation_pair}"
            )
        minimum = min(minimum, distance)
        records.append((operation_pair, format(distance, ".12f")))

    source = v5.build_structural_frame_retention_root_service_v5()
    # V5's axis-aligned reserve is a conservative lower bound. Exact B-rep distance
    # must never be smaller than that already accepted reserve.
    if minimum + 1e-9 < source.minimum_bilateral_service_separation_mm:
        raise StructuralFrameRetentionRootServiceV6Error(
            "B-rep clearance contradicts V5 conservative separation authority"
        )
    payload = {
        "source_v5_evidence_sha256": source.separation_evidence_sha256,
        "required_clearance_mm": format(MIN_BREP_SERVICE_CLEARANCE_MM, ".12f"),
        "records": records,
    }
    digest = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return round(minimum, 12), digest


@dataclass(frozen=True, slots=True)
class StructuralFrameRetentionRootServiceV6:
    source_v5_evidence_sha256: str
    minimum_brep_service_clearance_mm: float
    clearance_evidence_sha256: str
    physical_validation_eligible: bool = False

    def validate(self) -> "StructuralFrameRetentionRootServiceV6":
        source = v5.build_structural_frame_retention_root_service_v5()
        minimum, digest = _clearance_evidence()
        if self.source_v5_evidence_sha256 != source.separation_evidence_sha256:
            raise StructuralFrameRetentionRootServiceV6Error("source V5 service evidence is stale")
        if not math.isfinite(self.minimum_brep_service_clearance_mm):
            raise StructuralFrameRetentionRootServiceV6Error("minimum B-rep service clearance must be finite")
        if self.minimum_brep_service_clearance_mm != minimum or minimum < MIN_BREP_SERVICE_CLEARANCE_MM:
            raise StructuralFrameRetentionRootServiceV6Error("B-rep service clearance evidence is stale or insufficient")
        if self.clearance_evidence_sha256 != digest or len(digest) != 64:
            raise StructuralFrameRetentionRootServiceV6Error("B-rep clearance evidence digest is stale")
        if self.physical_validation_eligible is not False:
            raise StructuralFrameRetentionRootServiceV6Error("digital service geometry is not physical evidence")
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        payload = {
            "schema": SCHEMA,
            "supersedes_schema": SUPERSEDES_SCHEMA,
            "source_v5_evidence_sha256": self.source_v5_evidence_sha256,
            "minimum_brep_service_clearance_mm": self.minimum_brep_service_clearance_mm,
            "required_brep_service_clearance_mm": MIN_BREP_SERVICE_CLEARANCE_MM,
            "clearance_evidence_sha256": self.clearance_evidence_sha256,
            "criterion": "BILATERAL_SERVICE_CORRIDORS_RETAIN_POSITIVE_EXACT_BREP_CLEARANCE",
            "whole_head_removal_status": "OPEN",
            "physical_validation_eligible": self.physical_validation_eligible,
        }
        payload["manifest_sha256"] = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        return payload


def build_structural_frame_retention_root_service_v6() -> StructuralFrameRetentionRootServiceV6:
    source = v5.build_structural_frame_retention_root_service_v5()
    minimum, digest = _clearance_evidence()
    return StructuralFrameRetentionRootServiceV6(
        source.separation_evidence_sha256, minimum, digest, False
    ).validate()
