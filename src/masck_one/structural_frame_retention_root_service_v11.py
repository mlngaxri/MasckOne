from __future__ import annotations

"""V11 service-corridor seated-boundary registration gate.

V9/V10 prove the realized service corridors have exactly the authored travel. They do not
prove that this travel begins at the seated hardware boundary. V11 closes that gap by
binding each withdrawal/installation sweep to its corresponding seated part B-rep.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
import math

from . import structural_frame_retention_root_service as v1
from . import structural_frame_retention_root_service_v10 as v10
from .structural_frame_retention_roots import build_structural_frame_retention_roots

SCHEMA = "MASCK_ONE_STRUCTURAL_FRAME_RETENTION_ROOT_SERVICE_V11"
SUPERSEDES_SCHEMA = v10.SCHEMA
REGISTRATION_TOLERANCE_MM = v10.TRAVEL_TOLERANCE_MM


class StructuralFrameRetentionRootServiceV11Error(ValueError):
    pass


def _seat_registration_evidence() -> tuple[tuple[tuple[str, float, float], ...], str]:
    upstream = v10.build_structural_frame_retention_root_service_v10()
    service = v1.build_structural_frame_retention_root_service()
    roots = build_structural_frame_retention_roots()
    service_by_id = {path.root_id: path for path in service.paths}
    records = []

    for root in roots.roots:
        path = service_by_id[root.root_id]
        pin = root.capture_pin.val().BoundingBox()
        pin_sweep = path.pin_withdraw_sweep.val().BoundingBox()
        retainer = root.split_retainer.val().BoundingBox()
        retainer_sweep = path.clip_install_sweep.val().BoundingBox()

        # Withdrawal is toward -Y, so the extension must terminate exactly at the seated
        # pin's negative-Y boundary. Retainer installation is from +Z, so its extension
        # must begin exactly at the seated retainer's positive-Z boundary.
        pin_boundary_error = pin_sweep.ymax - pin.ymin
        retainer_boundary_error = retainer_sweep.zmin - retainer.zmax
        if not all(math.isfinite(value) for value in (pin_boundary_error, retainer_boundary_error)):
            raise StructuralFrameRetentionRootServiceV11Error("service seat registration must be finite")
        if abs(pin_boundary_error) > REGISTRATION_TOLERANCE_MM:
            raise StructuralFrameRetentionRootServiceV11Error(f"{root.root_id} pin withdrawal corridor is detached from seated pin")
        if abs(retainer_boundary_error) > REGISTRATION_TOLERANCE_MM:
            raise StructuralFrameRetentionRootServiceV11Error(f"{root.root_id} retainer corridor is detached from seated retainer")
        records.append((root.root_id, round(pin_boundary_error, 12), round(retainer_boundary_error, 12)))

    payload = {
        "source_v10_travel_closure_evidence_sha256": upstream.travel_closure_evidence_sha256,
        "source_service_architecture_sha256": service.architecture_sha256,
        "source_retention_root_architecture_sha256": roots.architecture_sha256,
        "seat_boundary_error_mm": records,
        "registration_tolerance_mm": REGISTRATION_TOLERANCE_MM,
    }
    digest = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    return tuple(records), digest


@dataclass(frozen=True, slots=True)
class StructuralFrameRetentionRootServiceV11:
    source_v10_travel_closure_evidence_sha256: str
    seat_boundary_error_mm: tuple[tuple[str, float, float], ...]
    seat_registration_evidence_sha256: str
    physical_validation_eligible: bool = False

    def validate(self) -> "StructuralFrameRetentionRootServiceV11":
        upstream = v10.build_structural_frame_retention_root_service_v10()
        records, digest = _seat_registration_evidence()
        if self.source_v10_travel_closure_evidence_sha256 != upstream.travel_closure_evidence_sha256:
            raise StructuralFrameRetentionRootServiceV11Error("source V10 travel closure evidence is stale")
        if self.seat_boundary_error_mm != records:
            raise StructuralFrameRetentionRootServiceV11Error("service seat registration evidence is stale")
        if self.seat_registration_evidence_sha256 != digest or len(digest) != 64:
            raise StructuralFrameRetentionRootServiceV11Error("service seat registration digest is stale")
        if self.physical_validation_eligible is not False:
            raise StructuralFrameRetentionRootServiceV11Error("digital service geometry is not physical evidence")
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        payload = {
            "schema": SCHEMA,
            "supersedes_schema": SUPERSEDES_SCHEMA,
            "source_v10_travel_closure_evidence_sha256": self.source_v10_travel_closure_evidence_sha256,
            "seat_boundary_error_mm": [list(record) for record in self.seat_boundary_error_mm],
            "registration_tolerance_mm": REGISTRATION_TOLERANCE_MM,
            "seat_registration_evidence_sha256": self.seat_registration_evidence_sha256,
            "criterion": "SERVICE_CORRIDORS_BEGIN_AT_SEATED_HARDWARE_BOUNDARIES_WITHOUT_GAP_OR_OVERLAP",
            "whole_head_removal_status": "OPEN",
            "physical_validation_eligible": self.physical_validation_eligible,
        }
        payload["manifest_sha256"] = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        return payload


def build_structural_frame_retention_root_service_v11() -> StructuralFrameRetentionRootServiceV11:
    upstream = v10.build_structural_frame_retention_root_service_v10()
    records, digest = _seat_registration_evidence()
    return StructuralFrameRetentionRootServiceV11(
        upstream.travel_closure_evidence_sha256, records, digest, False
    ).validate()
