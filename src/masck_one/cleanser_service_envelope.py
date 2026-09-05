"""Complete attached cleanser-module service envelope.

The original cassette-removal sweep predates the realized refill/purge closure and its
retention key. This layer source-binds the successor cleanser service geometry and
conservatively carries every attached module material solid through the existing
cassette-withdrawal travel. It is a digital collision/service reservation only.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import re

import cadquery as cq

from .authority import Authority
from .cleanser_service_interfaces import (
    SCHEMA as SERVICE_SCHEMA,
    CleanserServiceGeometry,
    build_cleanser_service_geometry,
)
from .realized_cleanser_storage import CASSETTE_WITHDRAWAL_TRAVEL_MM

WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"
SCHEMA = "MASCK_ONE_CELL4_CLEANSER_COMPLETE_MODULE_SERVICE_ENVELOPE_V1"
SOURCE_SERVICE_BLOB_SHA = "7977c6d12e3b2883a246ca00d1570ad683229243"
EVIDENCE_STATUS = "CONSERVATIVE_DIGITAL_SERVICE_ENVELOPE_ONLY_NOT_WET_HAND_OR_PHYSICAL_SERVICE_VALIDATION"

_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
_BLOB_RE = re.compile(r"[0-9a-f]{40}\Z")


class CleanserServiceEnvelopeError(ValueError):
    pass


def _box(dx: float, dy: float, dz: float, x: float, y: float, z: float) -> cq.Workplane:
    return cq.Workplane("XY").box(dx, dy, dz, centered=(True, True, True)).translate((x, y, z))


def _bounds(shape: cq.Workplane) -> tuple[float, float, float, float, float, float]:
    bb = shape.val().BoundingBox()
    return (
        float(bb.xmin), float(bb.xmax),
        float(bb.ymin), float(bb.ymax),
        float(bb.zmin), float(bb.zmax),
    )


@dataclass(frozen=True, slots=True)
class CleanserCompleteModuleServiceEnvelope:
    source_authority_revision: str
    source_service_manifest_sha256: str
    source_service_blob_sha: str
    module_removal_sweep_solid: cq.Workplane
    withdrawal_travel_mm: float
    physical_validation_eligible: bool = False
    evidence_status: str = EVIDENCE_STATUS

    def __post_init__(self) -> None:
        if type(self.source_authority_revision) is not str or not self.source_authority_revision:
            raise CleanserServiceEnvelopeError("service envelope requires exact authority revision")
        if type(self.source_service_manifest_sha256) is not str or _SHA256_RE.fullmatch(self.source_service_manifest_sha256) is None:
            raise CleanserServiceEnvelopeError("service envelope source manifest must be canonical SHA-256")
        if type(self.source_service_blob_sha) is not str or _BLOB_RE.fullmatch(self.source_service_blob_sha) is None:
            raise CleanserServiceEnvelopeError("service envelope source blob must be exact lowercase 40-hex")
        if type(self.withdrawal_travel_mm) not in (int, float) or float(self.withdrawal_travel_mm) != CASSETTE_WITHDRAWAL_TRAVEL_MM:
            raise CleanserServiceEnvelopeError("complete module removal must retain controlled cassette withdrawal travel")
        if self.module_removal_sweep_solid.solids().size() != 1 or not self.module_removal_sweep_solid.val().isValid():
            raise CleanserServiceEnvelopeError("complete module service envelope must be one valid deterministic solid")
        if self.module_removal_sweep_solid.val().Volume() <= 0.0:
            raise CleanserServiceEnvelopeError("complete module service envelope must have positive volume")
        if type(self.physical_validation_eligible) is not bool or self.physical_validation_eligible:
            raise CleanserServiceEnvelopeError("digital service envelope cannot become physical validation evidence")
        if self.evidence_status != EVIDENCE_STATUS:
            raise CleanserServiceEnvelopeError("service-envelope evidence firewall changed")

    @property
    def manifest_sha256(self) -> str:
        raw = json.dumps(self.manifest(include_sha=False), sort_keys=True, separators=(",", ":")).encode("utf-8")
        return sha256(raw).hexdigest()

    def validate_current_sources(self, authority: Authority) -> CleanserServiceGeometry:
        if type(authority) is not Authority:
            raise CleanserServiceEnvelopeError("authority must be an exact Authority contract")
        service = build_cleanser_service_geometry(authority)
        service.validate_current_sources(authority)
        if self.source_authority_revision != str(authority.get("project", "authority_revision")):
            raise CleanserServiceEnvelopeError("complete cleanser service envelope is stale for current authority")
        if self.source_service_manifest_sha256 != service.manifest_sha256:
            raise CleanserServiceEnvelopeError("complete cleanser service envelope is stale for service geometry")
        if self.source_service_blob_sha != SOURCE_SERVICE_BLOB_SHA:
            raise CleanserServiceEnvelopeError("complete cleanser service envelope source blob identity changed")
        return service

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        bb = self.module_removal_sweep_solid.val().BoundingBox()
        payload: dict[str, object] = {
            "schema": SCHEMA,
            "source_service_schema": SERVICE_SCHEMA,
            "source_authority_revision": self.source_authority_revision,
            "source_service_manifest_sha256": self.source_service_manifest_sha256,
            "source_service_blob_sha": self.source_service_blob_sha,
            "world_frame_id": WORLD_FRAME_ID,
            "moving_package": "CLEANSER_SUCCESSOR_BODY_PLUS_REFILL_PURGE_CLOSURE_PLUS_CLOSURE_KEY",
            "withdrawal_translation_world_mm": [0.0, 0.0, -self.withdrawal_travel_mm],
            "precondition": "BASE_CASSETTE_RETENTION_KEY_RETRACTED_MASK_UNPOWERED",
            "sweep_construction": "CONSERVATIVE_AXIS_ALIGNED_BOUND_OF_ALL_ATTACHED_MATERIAL_THROUGH_FULL_TRANSLATION",
            "sweep_bounds_world_mm": {
                "x": [float(bb.xmin), float(bb.xmax)],
                "y": [float(bb.ymin), float(bb.ymax)],
                "z": [float(bb.zmin), float(bb.zmax)],
            },
            "physical_validation_eligible": self.physical_validation_eligible,
            "evidence_status": self.evidence_status,
        }
        if include_sha:
            payload["manifest_sha256"] = self.manifest_sha256
        return payload


def build_complete_cleanser_module_service_envelope(authority: Authority) -> CleanserCompleteModuleServiceEnvelope:
    if type(authority) is not Authority:
        raise CleanserServiceEnvelopeError("authority must be an exact Authority contract")
    service = build_cleanser_service_geometry(authority)
    service.validate_current_sources(authority)

    attached_material = (
        service.ported_body_solid,
        service.service_closure_solid,
        service.service_retention_key_solid,
    )
    bounds = tuple(_bounds(shape) for shape in attached_material)
    xmin = min(item[0] for item in bounds)
    xmax = max(item[1] for item in bounds)
    ymin = min(item[2] for item in bounds)
    ymax = max(item[3] for item in bounds)
    zmin = min(item[4] for item in bounds)
    zmax = max(item[5] for item in bounds)
    travel = float(CASSETTE_WITHDRAWAL_TRAVEL_MM)

    sweep = _box(
        xmax - xmin,
        ymax - ymin,
        (zmax - zmin) + travel,
        (xmin + xmax) / 2.0,
        (ymin + ymax) / 2.0,
        (zmin + zmax - travel) / 2.0,
    )
    envelope = CleanserCompleteModuleServiceEnvelope(
        source_authority_revision=str(authority.get("project", "authority_revision")),
        source_service_manifest_sha256=service.manifest_sha256,
        source_service_blob_sha=SOURCE_SERVICE_BLOB_SHA,
        module_removal_sweep_solid=sweep,
        withdrawal_travel_mm=travel,
    )
    envelope.validate_current_sources(authority)
    return envelope
