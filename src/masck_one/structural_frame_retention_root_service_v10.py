from __future__ import annotations

"""V10 service-corridor travel closure gate.

V9 proves each realized corridor is at least as long as the authored service travel. V10
closes the opposite failure mode: a corridor may not silently grow beyond that travel and
consume packaging space that is not part of the quick-release interface contract.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
import math

from . import structural_frame_retention_root_service as v1
from . import structural_frame_retention_root_service_v9 as v9

SCHEMA = "MASCK_ONE_STRUCTURAL_FRAME_RETENTION_ROOT_SERVICE_V10"
SUPERSEDES_SCHEMA = v9.SCHEMA
TRAVEL_TOLERANCE_MM = v9.GEOMETRY_TOLERANCE_MM


class StructuralFrameRetentionRootServiceV10Error(ValueError):
    pass


def _travel_closure_evidence() -> tuple[tuple[tuple[str, float, float], ...], str]:
    source = v9.build_structural_frame_retention_root_service_v9()
    records = []
    for root_id, pin_reach, retainer_reach in source.service_reach_mm:
        pin_error = pin_reach - v1.PIN_WITHDRAW_EXTENSION_MM
        retainer_error = retainer_reach - v1.CLIP_RADIAL_EXTENSION_MM
        if not all(math.isfinite(value) for value in (pin_error, retainer_error)):
            raise StructuralFrameRetentionRootServiceV10Error("service travel closure must be finite")
        if abs(pin_error) > TRAVEL_TOLERANCE_MM:
            raise StructuralFrameRetentionRootServiceV10Error(f"{root_id} pin corridor exceeds authored travel closure")
        if abs(retainer_error) > TRAVEL_TOLERANCE_MM:
            raise StructuralFrameRetentionRootServiceV10Error(f"{root_id} retainer corridor exceeds authored travel closure")
        records.append((root_id, round(pin_error, 12), round(retainer_error, 12)))

    payload = {
        "source_v9_reach_evidence_sha256": source.reach_evidence_sha256,
        "travel_error_mm": records,
        "required_pin_withdraw_extension_mm": v1.PIN_WITHDRAW_EXTENSION_MM,
        "required_retainer_install_extension_mm": v1.CLIP_RADIAL_EXTENSION_MM,
        "travel_tolerance_mm": TRAVEL_TOLERANCE_MM,
    }
    digest = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    return tuple(records), digest


@dataclass(frozen=True, slots=True)
class StructuralFrameRetentionRootServiceV10:
    source_v9_reach_evidence_sha256: str
    travel_error_mm: tuple[tuple[str, float, float], ...]
    travel_closure_evidence_sha256: str
    physical_validation_eligible: bool = False

    def validate(self) -> "StructuralFrameRetentionRootServiceV10":
        source = v9.build_structural_frame_retention_root_service_v9()
        records, digest = _travel_closure_evidence()
        if self.source_v9_reach_evidence_sha256 != source.reach_evidence_sha256:
            raise StructuralFrameRetentionRootServiceV10Error("source V9 reach evidence is stale")
        if self.travel_error_mm != records:
            raise StructuralFrameRetentionRootServiceV10Error("service travel closure evidence is stale")
        if self.travel_closure_evidence_sha256 != digest or len(digest) != 64:
            raise StructuralFrameRetentionRootServiceV10Error("service travel closure digest is stale")
        if self.physical_validation_eligible is not False:
            raise StructuralFrameRetentionRootServiceV10Error("digital service geometry is not physical evidence")
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        payload = {
            "schema": SCHEMA,
            "supersedes_schema": SUPERSEDES_SCHEMA,
            "source_v9_reach_evidence_sha256": self.source_v9_reach_evidence_sha256,
            "travel_error_mm": [list(record) for record in self.travel_error_mm],
            "travel_tolerance_mm": TRAVEL_TOLERANCE_MM,
            "travel_closure_evidence_sha256": self.travel_closure_evidence_sha256,
            "criterion": "SERVICE_CORRIDORS_MATCH_AUTHORED_TRAVEL_WITHOUT_TRUNCATION_OR_PACKAGING_OVERSHOOT",
            "whole_head_removal_status": "OPEN",
            "physical_validation_eligible": self.physical_validation_eligible,
        }
        payload["manifest_sha256"] = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        return payload


def build_structural_frame_retention_root_service_v10() -> StructuralFrameRetentionRootServiceV10:
    source = v9.build_structural_frame_retention_root_service_v9()
    records, digest = _travel_closure_evidence()
    return StructuralFrameRetentionRootServiceV10(source.reach_evidence_sha256, records, digest, False).validate()
