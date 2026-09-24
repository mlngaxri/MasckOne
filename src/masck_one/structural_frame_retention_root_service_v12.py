from __future__ import annotations

"""V12 service-corridor cross-section registration gate.

V11 binds corridor travel to the seated hardware boundary. V12 additionally proves the
corridor cross-section remains registered to the seated part plus the authored access
clearance, preventing a laterally shifted corridor from preserving travel while no longer
providing usable tool/finger access around the hardware.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
import math

from . import structural_frame_retention_root_service as v1
from . import structural_frame_retention_root_service_v11 as v11
from .structural_frame_retention_roots import build_structural_frame_retention_roots

SCHEMA = "MASCK_ONE_STRUCTURAL_FRAME_RETENTION_ROOT_SERVICE_V12"
SUPERSEDES_SCHEMA = v11.SCHEMA
REGISTRATION_TOLERANCE_MM = v11.REGISTRATION_TOLERANCE_MM


class StructuralFrameRetentionRootServiceV12Error(ValueError):
    pass


def _cross_section_evidence() -> tuple[tuple[tuple[str, tuple[float, ...], tuple[float, ...]], ...], str]:
    upstream = v11.build_structural_frame_retention_root_service_v11()
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
        c = v1.ACCESS_CLEARANCE_MM

        pin_errors = (
            pin_sweep.xmin - (pin.xmin - c),
            pin_sweep.xmax - (pin.xmax + c),
            pin_sweep.zmin - (pin.zmin - c),
            pin_sweep.zmax - (pin.zmax + c),
        )
        retainer_errors = (
            retainer_sweep.xmin - (retainer.xmin - c),
            retainer_sweep.xmax - (retainer.xmax + c),
            retainer_sweep.ymin - (retainer.ymin - c),
            retainer_sweep.ymax - (retainer.ymax + c),
        )
        values = pin_errors + retainer_errors
        if not all(math.isfinite(value) for value in values):
            raise StructuralFrameRetentionRootServiceV12Error("service cross-section registration must be finite")
        if any(abs(value) > REGISTRATION_TOLERANCE_MM for value in pin_errors):
            raise StructuralFrameRetentionRootServiceV12Error(f"{root.root_id} pin corridor cross-section is misregistered")
        if any(abs(value) > REGISTRATION_TOLERANCE_MM for value in retainer_errors):
            raise StructuralFrameRetentionRootServiceV12Error(f"{root.root_id} retainer corridor cross-section is misregistered")
        records.append((root.root_id, tuple(round(v, 12) for v in pin_errors), tuple(round(v, 12) for v in retainer_errors)))

    payload = {
        "source_v11_seat_registration_evidence_sha256": upstream.seat_registration_evidence_sha256,
        "source_service_architecture_sha256": service.architecture_sha256,
        "source_retention_root_architecture_sha256": roots.architecture_sha256,
        "access_clearance_mm": v1.ACCESS_CLEARANCE_MM,
        "cross_section_boundary_error_mm": records,
        "registration_tolerance_mm": REGISTRATION_TOLERANCE_MM,
    }
    digest = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    return tuple(records), digest


@dataclass(frozen=True, slots=True)
class StructuralFrameRetentionRootServiceV12:
    source_v11_seat_registration_evidence_sha256: str
    cross_section_boundary_error_mm: tuple[tuple[str, tuple[float, ...], tuple[float, ...]], ...]
    cross_section_registration_evidence_sha256: str
    physical_validation_eligible: bool = False

    def validate(self) -> "StructuralFrameRetentionRootServiceV12":
        upstream = v11.build_structural_frame_retention_root_service_v11()
        records, digest = _cross_section_evidence()
        if self.source_v11_seat_registration_evidence_sha256 != upstream.seat_registration_evidence_sha256:
            raise StructuralFrameRetentionRootServiceV12Error("source V11 seat registration evidence is stale")
        if self.cross_section_boundary_error_mm != records:
            raise StructuralFrameRetentionRootServiceV12Error("service cross-section registration evidence is stale")
        if self.cross_section_registration_evidence_sha256 != digest or len(digest) != 64:
            raise StructuralFrameRetentionRootServiceV12Error("service cross-section registration digest is stale")
        if self.physical_validation_eligible is not False:
            raise StructuralFrameRetentionRootServiceV12Error("digital service geometry is not physical evidence")
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        payload = {
            "schema": SCHEMA,
            "supersedes_schema": SUPERSEDES_SCHEMA,
            "source_v11_seat_registration_evidence_sha256": self.source_v11_seat_registration_evidence_sha256,
            "cross_section_boundary_error_mm": self.cross_section_boundary_error_mm,
            "access_clearance_mm": v1.ACCESS_CLEARANCE_MM,
            "registration_tolerance_mm": REGISTRATION_TOLERANCE_MM,
            "cross_section_registration_evidence_sha256": self.cross_section_registration_evidence_sha256,
            "criterion": "SERVICE_CORRIDOR_CROSS_SECTIONS_REGISTER_TO_SEATED_HARDWARE_PLUS_ACCESS_CLEARANCE",
            "whole_head_removal_status": "OPEN",
            "physical_validation_eligible": self.physical_validation_eligible,
        }
        payload["manifest_sha256"] = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        return payload


def build_structural_frame_retention_root_service_v12() -> StructuralFrameRetentionRootServiceV12:
    upstream = v11.build_structural_frame_retention_root_service_v11()
    records, digest = _cross_section_evidence()
    return StructuralFrameRetentionRootServiceV12(
        upstream.seat_registration_evidence_sha256, records, digest, False
    ).validate()
