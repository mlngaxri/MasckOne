from __future__ import annotations

"""V4 bilateral coexistence audit for retention-root service corridors.

V1 proves each local service extension clears frame/yoke material, V2 clears the
opposite seated root, and V3 closes same-root sequencing. V4 verifies that the
left/right access corridors themselves do not collide for either service operation,
so bilateral pin withdrawal and retainer access remain geometrically independent.
This is conservative digital packaging evidence only.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
import math

from . import structural_frame_retention_root_service as v1
from . import structural_frame_retention_root_service_v3 as v3
from .structural_frame_retention_roots import build_structural_frame_retention_roots

SCHEMA = "MASCK_ONE_STRUCTURAL_FRAME_RETENTION_ROOT_SERVICE_V4"
SUPERSEDES_SCHEMA = v3.SCHEMA
_INTERSECTION_TOLERANCE_MM3 = 1e-7


class StructuralFrameRetentionRootServiceV4Error(ValueError):
    pass


def _bilateral_corridor_evidence() -> tuple[float, str]:
    roots = build_structural_frame_retention_roots()
    service = v1.build_structural_frame_retention_root_service(roots=roots)
    if len(service.paths) != 2:
        raise StructuralFrameRetentionRootServiceV4Error("exactly two bilateral service paths are required")

    left, right = service.paths
    checks = (
        ("pin_withdraw_vs_pin_withdraw", left.pin_withdraw_sweep, right.pin_withdraw_sweep),
        ("clip_install_vs_clip_install", left.clip_install_sweep, right.clip_install_sweep),
        ("left_pin_withdraw_vs_right_clip_install", left.pin_withdraw_sweep, right.clip_install_sweep),
        ("left_clip_install_vs_right_pin_withdraw", left.clip_install_sweep, right.pin_withdraw_sweep),
    )
    records: list[tuple[str, str]] = []
    maximum = 0.0
    try:
        for operation_pair, first, second in checks:
            overlap = v1._intersection(first, second)
            if not math.isfinite(overlap) or overlap < 0.0:
                raise StructuralFrameRetentionRootServiceV4Error(
                    "bilateral service-corridor evidence must be finite and non-negative"
                )
            if overlap > _INTERSECTION_TOLERANCE_MM3:
                raise StructuralFrameRetentionRootServiceV4Error(
                    f"bilateral service corridors collide for {operation_pair}"
                )
            maximum = max(maximum, overlap)
            records.append((operation_pair, format(overlap, ".12f")))
    except StructuralFrameRetentionRootServiceV4Error:
        raise
    except Exception as exc:
        raise StructuralFrameRetentionRootServiceV4Error(
            "bilateral service-corridor coexistence query failed"
        ) from exc

    v3_audit = v3.build_structural_frame_retention_root_service_v3()
    payload = {
        "source_v3_evidence_sha256": v3_audit.local_sequence_evidence_sha256,
        "records": records,
    }
    digest = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return round(maximum, 12), digest


@dataclass(frozen=True, slots=True)
class StructuralFrameRetentionRootServiceV4:
    source_v3_evidence_sha256: str
    bilateral_corridor_max_intersection_mm3: float
    bilateral_corridor_evidence_sha256: str
    physical_validation_eligible: bool = False

    def validate(self) -> "StructuralFrameRetentionRootServiceV4":
        v3_audit = v3.build_structural_frame_retention_root_service_v3()
        maximum, digest = _bilateral_corridor_evidence()
        if self.source_v3_evidence_sha256 != v3_audit.local_sequence_evidence_sha256:
            raise StructuralFrameRetentionRootServiceV4Error("source V3 service evidence is stale")
        if (
            not math.isfinite(self.bilateral_corridor_max_intersection_mm3)
            or self.bilateral_corridor_max_intersection_mm3 != maximum
            or maximum > _INTERSECTION_TOLERANCE_MM3
        ):
            raise StructuralFrameRetentionRootServiceV4Error(
                "bilateral service-corridor evidence is stale or colliding"
            )
        if self.bilateral_corridor_evidence_sha256 != digest or len(digest) != 64:
            raise StructuralFrameRetentionRootServiceV4Error("bilateral corridor evidence digest is stale")
        if self.physical_validation_eligible is not False:
            raise StructuralFrameRetentionRootServiceV4Error("digital service geometry is not physical evidence")
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        payload = {
            "schema": SCHEMA,
            "supersedes_schema": SUPERSEDES_SCHEMA,
            "source_v3_evidence_sha256": self.source_v3_evidence_sha256,
            "bilateral_corridor_max_intersection_mm3": self.bilateral_corridor_max_intersection_mm3,
            "bilateral_corridor_evidence_sha256": self.bilateral_corridor_evidence_sha256,
            "criterion": "BILATERAL_PIN_AND_RETAINER_SERVICE_CORRIDORS_ARE_MUTUALLY_COLLISION_FREE",
            "whole_head_removal_status": "OPEN",
            "physical_validation_eligible": self.physical_validation_eligible,
        }
        payload["manifest_sha256"] = sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        ).hexdigest()
        return payload


def build_structural_frame_retention_root_service_v4() -> StructuralFrameRetentionRootServiceV4:
    v3_audit = v3.build_structural_frame_retention_root_service_v3()
    maximum, digest = _bilateral_corridor_evidence()
    return StructuralFrameRetentionRootServiceV4(
        v3_audit.local_sequence_evidence_sha256, maximum, digest, False
    ).validate()
