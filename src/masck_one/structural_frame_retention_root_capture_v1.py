from __future__ import annotations

"""Positive-capture audit for the bilateral retention-root split retainers.

This audit proves the nominal CAD seeds form a positive axial capture rather than a
purely frictional pin restraint. It intentionally does not claim strength, fatigue,
wear, insertion force, accidental-release performance, or manufactured tolerance
closure.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
import math

from . import structural_frame_retention_root_service_v3 as service_v3
from .structural_frame_retention_roots import (
    CLEVIS_PIN_GROOVE_DEPTH_MM,
    CLEVIS_PIN_GROOVE_WIDTH_MM,
    CLEVIS_PIN_RADIUS_MM,
    CLEVIS_CLIP_RADIAL_THICKNESS_MM,
    ROOT_IDS,
    build_structural_frame_retention_roots,
)

SCHEMA = "MASCK_ONE_STRUCTURAL_FRAME_RETENTION_ROOT_CAPTURE_V1"
CLIP_HOLE_RELIEF_MM = 0.08
_GEOMETRY_TOLERANCE_MM = 1e-6


class StructuralFrameRetentionRootCaptureError(ValueError):
    pass


def _capture_metrics() -> tuple[float, float, str]:
    roots = build_structural_frame_retention_roots()
    if tuple(root.root_id for root in roots.roots) != ROOT_IDS:
        raise StructuralFrameRetentionRootCaptureError("bilateral retention roots are required")

    groove_bottom_radius = CLEVIS_PIN_RADIUS_MM - CLEVIS_PIN_GROOVE_DEPTH_MM
    clip_inner_radius = groove_bottom_radius + CLIP_HOLE_RELIEF_MM
    clip_outer_radius = CLEVIS_PIN_RADIUS_MM + CLEVIS_CLIP_RADIAL_THICKNESS_MM
    radial_shoulder_engagement = CLEVIS_PIN_RADIUS_MM - clip_inner_radius
    axial_groove_coverage = CLEVIS_PIN_GROOVE_WIDTH_MM

    values = (
        groove_bottom_radius,
        clip_inner_radius,
        clip_outer_radius,
        radial_shoulder_engagement,
        axial_groove_coverage,
    )
    if not all(math.isfinite(value) and value > 0.0 for value in values):
        raise StructuralFrameRetentionRootCaptureError("capture dimensions must be finite and positive")
    if clip_inner_radius <= groove_bottom_radius + _GEOMETRY_TOLERANCE_MM:
        raise StructuralFrameRetentionRootCaptureError("split retainer requires radial installation relief over groove bottom")
    if radial_shoulder_engagement <= _GEOMETRY_TOLERANCE_MM:
        raise StructuralFrameRetentionRootCaptureError("split retainer does not positively overlap the pin shoulder")
    if clip_outer_radius <= CLEVIS_PIN_RADIUS_MM + _GEOMETRY_TOLERANCE_MM:
        raise StructuralFrameRetentionRootCaptureError("split retainer requires material outside the pin shaft envelope")

    service = service_v3.build_structural_frame_retention_root_service_v3()
    payload = {
        "source_root_architecture_sha256": roots.architecture_sha256,
        "source_service_v3_evidence_sha256": service.local_sequence_evidence_sha256,
        "root_ids": list(ROOT_IDS),
        "pin_radius_mm": CLEVIS_PIN_RADIUS_MM,
        "groove_depth_mm": CLEVIS_PIN_GROOVE_DEPTH_MM,
        "groove_width_mm": CLEVIS_PIN_GROOVE_WIDTH_MM,
        "clip_hole_relief_mm": CLIP_HOLE_RELIEF_MM,
        "clip_radial_thickness_mm": CLEVIS_CLIP_RADIAL_THICKNESS_MM,
        "groove_bottom_radius_mm": groove_bottom_radius,
        "clip_inner_radius_mm": clip_inner_radius,
        "clip_outer_radius_mm": clip_outer_radius,
        "radial_shoulder_engagement_mm": radial_shoulder_engagement,
        "axial_groove_coverage_mm": axial_groove_coverage,
    }
    digest = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    return round(radial_shoulder_engagement, 12), round(axial_groove_coverage, 12), digest


@dataclass(frozen=True, slots=True)
class StructuralFrameRetentionRootCaptureV1:
    source_root_architecture_sha256: str
    source_service_v3_evidence_sha256: str
    radial_shoulder_engagement_mm: float
    axial_groove_coverage_mm: float
    capture_evidence_sha256: str
    accidental_release_validated: bool = False
    physical_validation_eligible: bool = False

    def validate(self) -> "StructuralFrameRetentionRootCaptureV1":
        roots = build_structural_frame_retention_roots()
        service = service_v3.build_structural_frame_retention_root_service_v3()
        radial, axial, digest = _capture_metrics()
        if self.source_root_architecture_sha256 != roots.architecture_sha256:
            raise StructuralFrameRetentionRootCaptureError("source retention-root architecture is stale")
        if self.source_service_v3_evidence_sha256 != service.local_sequence_evidence_sha256:
            raise StructuralFrameRetentionRootCaptureError("source service V3 evidence is stale")
        if self.radial_shoulder_engagement_mm != radial or radial <= _GEOMETRY_TOLERANCE_MM:
            raise StructuralFrameRetentionRootCaptureError("positive radial shoulder engagement evidence is stale")
        if self.axial_groove_coverage_mm != axial or axial <= _GEOMETRY_TOLERANCE_MM:
            raise StructuralFrameRetentionRootCaptureError("axial groove coverage evidence is stale")
        if self.capture_evidence_sha256 != digest or len(digest) != 64:
            raise StructuralFrameRetentionRootCaptureError("capture evidence digest is stale")
        if self.accidental_release_validated is not False:
            raise StructuralFrameRetentionRootCaptureError("nominal geometry does not validate accidental-release risk")
        if self.physical_validation_eligible is not False:
            raise StructuralFrameRetentionRootCaptureError("digital capture geometry is not physical evidence")
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        return {
            "schema": SCHEMA,
            "source_root_architecture_sha256": self.source_root_architecture_sha256,
            "source_service_v3_evidence_sha256": self.source_service_v3_evidence_sha256,
            "radial_shoulder_engagement_mm": self.radial_shoulder_engagement_mm,
            "axial_groove_coverage_mm": self.axial_groove_coverage_mm,
            "capture_evidence_sha256": self.capture_evidence_sha256,
            "capture_status": "NOMINAL_POSITIVE_AXIAL_CAPTURE_GEOMETRY_PROVEN",
            "accidental_release_validated": self.accidental_release_validated,
            "physical_validation_eligible": self.physical_validation_eligible,
        }


def build_structural_frame_retention_root_capture_v1() -> StructuralFrameRetentionRootCaptureV1:
    roots = build_structural_frame_retention_roots()
    service = service_v3.build_structural_frame_retention_root_service_v3()
    radial, axial, digest = _capture_metrics()
    return StructuralFrameRetentionRootCaptureV1(
        roots.architecture_sha256,
        service.local_sequence_evidence_sha256,
        radial,
        axial,
        digest,
        False,
        False,
    ).validate()
