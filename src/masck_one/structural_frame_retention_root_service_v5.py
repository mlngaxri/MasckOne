from __future__ import annotations

"""V5 minimum-separation gate for bilateral retention-root service corridors.

V4 proves the left/right service sweeps do not intersect. V5 strengthens that result by
requiring a positive axis-aligned separation reserve between every bilateral operation
pair. This prevents a numerically non-intersecting but effectively touching service
layout from being accepted as accessible packaging evidence.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
import math

from . import structural_frame_retention_root_service as v1
from . import structural_frame_retention_root_service_v4 as v4
from .structural_frame_retention_roots import build_structural_frame_retention_roots

SCHEMA = "MASCK_ONE_STRUCTURAL_FRAME_RETENTION_ROOT_SERVICE_V5"
SUPERSEDES_SCHEMA = v4.SCHEMA
MIN_BILATERAL_SERVICE_SEPARATION_MM = v1.ACCESS_CLEARANCE_MM


class StructuralFrameRetentionRootServiceV5Error(ValueError):
    pass


def _axis_separation(first, second) -> tuple[float, float, float]:
    a = first.val().BoundingBox()
    b = second.val().BoundingBox()
    gaps = (
        max(0.0, b.xmin - a.xmax, a.xmin - b.xmax),
        max(0.0, b.ymin - a.ymax, a.ymin - b.ymax),
        max(0.0, b.zmin - a.zmax, a.zmin - b.zmax),
    )
    if not all(math.isfinite(value) and value >= 0.0 for value in gaps):
        raise StructuralFrameRetentionRootServiceV5Error("service separation must be finite and non-negative")
    return gaps


def _separation_evidence() -> tuple[float, str]:
    roots = build_structural_frame_retention_roots()
    service = v1.build_structural_frame_retention_root_service(roots=roots)
    if len(service.paths) != 2:
        raise StructuralFrameRetentionRootServiceV5Error("exactly two bilateral service paths are required")
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
        gaps = _axis_separation(first, second)
        # Separation on any world axis proves the AABBs, and therefore the contained
        # service solids, have at least this conservative clearance.
        reserve = max(gaps)
        if reserve < MIN_BILATERAL_SERVICE_SEPARATION_MM:
            raise StructuralFrameRetentionRootServiceV5Error(
                f"bilateral service separation reserve is insufficient for {operation_pair}"
            )
        minimum = min(minimum, reserve)
        records.append((operation_pair, *(format(value, ".12f") for value in gaps), format(reserve, ".12f")))

    v4_audit = v4.build_structural_frame_retention_root_service_v4()
    payload = {
        "source_v4_evidence_sha256": v4_audit.bilateral_corridor_evidence_sha256,
        "required_separation_mm": format(MIN_BILATERAL_SERVICE_SEPARATION_MM, ".12f"),
        "records": records,
    }
    digest = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return round(minimum, 12), digest


@dataclass(frozen=True, slots=True)
class StructuralFrameRetentionRootServiceV5:
    source_v4_evidence_sha256: str
    minimum_bilateral_service_separation_mm: float
    separation_evidence_sha256: str
    physical_validation_eligible: bool = False

    def validate(self) -> "StructuralFrameRetentionRootServiceV5":
        source = v4.build_structural_frame_retention_root_service_v4()
        minimum, digest = _separation_evidence()
        if self.source_v4_evidence_sha256 != source.bilateral_corridor_evidence_sha256:
            raise StructuralFrameRetentionRootServiceV5Error("source V4 service evidence is stale")
        if not math.isfinite(self.minimum_bilateral_service_separation_mm):
            raise StructuralFrameRetentionRootServiceV5Error("minimum service separation must be finite")
        if self.minimum_bilateral_service_separation_mm != minimum or minimum < MIN_BILATERAL_SERVICE_SEPARATION_MM:
            raise StructuralFrameRetentionRootServiceV5Error("bilateral service separation evidence is stale or insufficient")
        if self.separation_evidence_sha256 != digest or len(digest) != 64:
            raise StructuralFrameRetentionRootServiceV5Error("service separation evidence digest is stale")
        if self.physical_validation_eligible is not False:
            raise StructuralFrameRetentionRootServiceV5Error("digital service geometry is not physical evidence")
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        payload = {
            "schema": SCHEMA,
            "supersedes_schema": SUPERSEDES_SCHEMA,
            "source_v4_evidence_sha256": self.source_v4_evidence_sha256,
            "minimum_bilateral_service_separation_mm": self.minimum_bilateral_service_separation_mm,
            "required_bilateral_service_separation_mm": MIN_BILATERAL_SERVICE_SEPARATION_MM,
            "separation_evidence_sha256": self.separation_evidence_sha256,
            "criterion": "BILATERAL_SERVICE_CORRIDORS_RETAIN_POSITIVE_CONSERVATIVE_SEPARATION_RESERVE",
            "whole_head_removal_status": "OPEN",
            "physical_validation_eligible": self.physical_validation_eligible,
        }
        payload["manifest_sha256"] = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        return payload


def build_structural_frame_retention_root_service_v5() -> StructuralFrameRetentionRootServiceV5:
    source = v4.build_structural_frame_retention_root_service_v4()
    minimum, digest = _separation_evidence()
    return StructuralFrameRetentionRootServiceV5(
        source.bilateral_corridor_evidence_sha256, minimum, digest, False
    ).validate()
