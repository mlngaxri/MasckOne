from __future__ import annotations

"""V2 integration audit for bilateral retention-root service corridors.

V1 proves each pin-withdrawal and retainer-installation extension clears the integrated
frame and its local yoke. V2 closes the cross-side packaging gap by screening every
service extension against the opposite yoke, seated capture pin, and seated split
retainer. This is sequential digital service evidence only, not whole-head removal,
strength, ergonomics, wet-use, or physical validation.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
import math

from . import structural_frame_retention_root_service as v1
from .structural_frame_retention_roots import build_structural_frame_retention_roots

SCHEMA = "MASCK_ONE_STRUCTURAL_FRAME_RETENTION_ROOT_SERVICE_V2"
SUPERSEDES_SCHEMA = v1.SCHEMA
_INTERSECTION_TOLERANCE_MM3 = 1e-7


class StructuralFrameRetentionRootServiceV2Error(ValueError):
    pass


def _cross_component_evidence() -> tuple[float, str]:
    roots = build_structural_frame_retention_roots()
    service = v1.build_structural_frame_retention_root_service(roots=roots)
    records: list[tuple[str, str, str, str]] = []
    maximum = 0.0
    try:
        for index, path in enumerate(service.paths):
            opposite = roots.roots[1 - index]
            obstacles = (
                ("opposite_yoke", opposite.yoke_root_reference),
                ("opposite_capture_pin", opposite.capture_pin),
                ("opposite_split_retainer", opposite.split_retainer),
            )
            for sweep_name, sweep in (
                ("pin_withdraw", path.pin_withdraw_sweep),
                ("clip_install", path.clip_install_sweep),
            ):
                for obstacle_name, obstacle in obstacles:
                    overlap = v1._intersection(sweep, obstacle)
                    if not math.isfinite(overlap) or overlap < 0.0:
                        raise StructuralFrameRetentionRootServiceV2Error(
                            "cross-component service evidence must be finite and non-negative"
                        )
                    if overlap > _INTERSECTION_TOLERANCE_MM3:
                        raise StructuralFrameRetentionRootServiceV2Error(
                            f"{path.root_id} {sweep_name} corridor collides with {obstacle_name}"
                        )
                    maximum = max(maximum, overlap)
                    records.append((path.root_id, sweep_name, obstacle_name, format(overlap, ".12f")))
    except StructuralFrameRetentionRootServiceV2Error:
        raise
    except Exception as exc:
        raise StructuralFrameRetentionRootServiceV2Error(
            "cross-component service clearance query failed"
        ) from exc

    payload = {
        "source_service_sha256": service.architecture_sha256,
        "records": records,
    }
    digest = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return round(maximum, 12), digest


@dataclass(frozen=True, slots=True)
class StructuralFrameRetentionRootServiceV2:
    source_service_sha256: str
    cross_component_max_intersection_mm3: float
    cross_component_evidence_sha256: str
    physical_validation_eligible: bool = False

    def validate(self) -> "StructuralFrameRetentionRootServiceV2":
        service = v1.build_structural_frame_retention_root_service()
        maximum, digest = _cross_component_evidence()
        if self.source_service_sha256 != service.architecture_sha256:
            raise StructuralFrameRetentionRootServiceV2Error("source service architecture is stale")
        if (
            not math.isfinite(self.cross_component_max_intersection_mm3)
            or self.cross_component_max_intersection_mm3 != maximum
            or maximum > _INTERSECTION_TOLERANCE_MM3
        ):
            raise StructuralFrameRetentionRootServiceV2Error(
                "cross-component service clearance evidence is stale or colliding"
            )
        if self.cross_component_evidence_sha256 != digest or len(digest) != 64:
            raise StructuralFrameRetentionRootServiceV2Error("cross-component evidence digest is stale")
        if self.physical_validation_eligible is not False:
            raise StructuralFrameRetentionRootServiceV2Error("digital service geometry is not physical evidence")
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        payload = {
            "schema": SCHEMA,
            "supersedes_schema": SUPERSEDES_SCHEMA,
            "source_service_sha256": self.source_service_sha256,
            "cross_component_max_intersection_mm3": self.cross_component_max_intersection_mm3,
            "cross_component_evidence_sha256": self.cross_component_evidence_sha256,
            "criterion": "BILATERAL_PIN_AND_RETAINER_SERVICE_EXTENSIONS_CLEAR_OPPOSITE_YOKE_AND_SEATED_HARDWARE",
            "whole_head_removal_status": "OPEN",
            "physical_validation_eligible": self.physical_validation_eligible,
        }
        payload["manifest_sha256"] = sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        ).hexdigest()
        return payload


def build_structural_frame_retention_root_service_v2() -> StructuralFrameRetentionRootServiceV2:
    service = v1.build_structural_frame_retention_root_service()
    maximum, digest = _cross_component_evidence()
    return StructuralFrameRetentionRootServiceV2(
        service.architecture_sha256, maximum, digest, False
    ).validate()
