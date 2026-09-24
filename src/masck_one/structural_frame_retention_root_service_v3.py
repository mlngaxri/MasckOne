from __future__ import annotations

"""V3 service-sequence audit for each retention root.

V1 proves service extensions clear frame and local yoke material. V2 proves they clear
the opposite root and its seated hardware. V3 closes the remaining same-root sequencing
gap: pin withdrawal must clear the seated split retainer, and split-retainer installation
must clear the seated capture pin. This is conservative digital packaging evidence only.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
import math

from . import structural_frame_retention_root_service as v1
from . import structural_frame_retention_root_service_v2 as v2
from .structural_frame_retention_roots import build_structural_frame_retention_roots

SCHEMA = "MASCK_ONE_STRUCTURAL_FRAME_RETENTION_ROOT_SERVICE_V3"
SUPERSEDES_SCHEMA = v2.SCHEMA
_INTERSECTION_TOLERANCE_MM3 = 1e-7


class StructuralFrameRetentionRootServiceV3Error(ValueError):
    pass


def _local_sequence_evidence() -> tuple[float, str]:
    roots = build_structural_frame_retention_roots()
    service = v1.build_structural_frame_retention_root_service(roots=roots)
    records: list[tuple[str, str, str, str]] = []
    maximum = 0.0
    try:
        for root, path in zip(roots.roots, service.paths, strict=True):
            checks = (
                ("pin_withdraw", path.pin_withdraw_sweep, "seated_split_retainer", root.split_retainer),
                ("clip_install", path.clip_install_sweep, "seated_capture_pin", root.capture_pin),
            )
            for operation, sweep, obstacle_name, obstacle in checks:
                overlap = v1._intersection(sweep, obstacle)
                if not math.isfinite(overlap) or overlap < 0.0:
                    raise StructuralFrameRetentionRootServiceV3Error(
                        "local service-sequence evidence must be finite and non-negative"
                    )
                if overlap > _INTERSECTION_TOLERANCE_MM3:
                    raise StructuralFrameRetentionRootServiceV3Error(
                        f"{root.root_id} {operation} corridor collides with {obstacle_name}"
                    )
                maximum = max(maximum, overlap)
                records.append((root.root_id, operation, obstacle_name, format(overlap, ".12f")))
    except StructuralFrameRetentionRootServiceV3Error:
        raise
    except Exception as exc:
        raise StructuralFrameRetentionRootServiceV3Error(
            "local service-sequence clearance query failed"
        ) from exc

    v2_audit = v2.build_structural_frame_retention_root_service_v2()
    payload = {
        "source_v2_evidence_sha256": v2_audit.cross_component_evidence_sha256,
        "records": records,
    }
    digest = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return round(maximum, 12), digest


@dataclass(frozen=True, slots=True)
class StructuralFrameRetentionRootServiceV3:
    source_v2_evidence_sha256: str
    local_sequence_max_intersection_mm3: float
    local_sequence_evidence_sha256: str
    physical_validation_eligible: bool = False

    def validate(self) -> "StructuralFrameRetentionRootServiceV3":
        v2_audit = v2.build_structural_frame_retention_root_service_v2()
        maximum, digest = _local_sequence_evidence()
        if self.source_v2_evidence_sha256 != v2_audit.cross_component_evidence_sha256:
            raise StructuralFrameRetentionRootServiceV3Error("source V2 service evidence is stale")
        if (
            not math.isfinite(self.local_sequence_max_intersection_mm3)
            or self.local_sequence_max_intersection_mm3 != maximum
            or maximum > _INTERSECTION_TOLERANCE_MM3
        ):
            raise StructuralFrameRetentionRootServiceV3Error(
                "local service-sequence clearance evidence is stale or colliding"
            )
        if self.local_sequence_evidence_sha256 != digest or len(digest) != 64:
            raise StructuralFrameRetentionRootServiceV3Error("local sequence evidence digest is stale")
        if self.physical_validation_eligible is not False:
            raise StructuralFrameRetentionRootServiceV3Error("digital service geometry is not physical evidence")
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        payload = {
            "schema": SCHEMA,
            "supersedes_schema": SUPERSEDES_SCHEMA,
            "source_v2_evidence_sha256": self.source_v2_evidence_sha256,
            "local_sequence_max_intersection_mm3": self.local_sequence_max_intersection_mm3,
            "local_sequence_evidence_sha256": self.local_sequence_evidence_sha256,
            "criterion": "PIN_WITHDRAWAL_CLEARS_SEATED_LOCAL_RETAINER_AND_RETAINER_INSTALL_CLEARS_SEATED_LOCAL_PIN",
            "whole_head_removal_status": "OPEN",
            "physical_validation_eligible": self.physical_validation_eligible,
        }
        payload["manifest_sha256"] = sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        ).hexdigest()
        return payload


def build_structural_frame_retention_root_service_v3() -> StructuralFrameRetentionRootServiceV3:
    v2_audit = v2.build_structural_frame_retention_root_service_v2()
    maximum, digest = _local_sequence_evidence()
    return StructuralFrameRetentionRootServiceV3(
        v2_audit.cross_component_evidence_sha256, maximum, digest, False
    ).validate()
