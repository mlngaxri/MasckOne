from __future__ import annotations

"""Residual-section audit for the controlled split-retainer geometry.

V2 establishes a real controlled throat and V3 exposes the elastic opening demand.
V4 checks the nominal material that remains around that throat before any material
or force model is allowed to treat the retainer as buildable. This is geometric
evidence only, not a strength or fatigue claim.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
import math

from . import structural_frame_retention_root_capture_v3 as capture_v3
from .structural_frame_retention_root_capture_v2 import CLIP_HOLE_RELIEF_MM, CLIP_THROAT_WIDTH_MM
from .structural_frame_retention_roots import (
    CLEVIS_CLIP_RADIAL_THICKNESS_MM,
    CLEVIS_PIN_GROOVE_DEPTH_MM,
    CLEVIS_PIN_GROOVE_WIDTH_MM,
    CLEVIS_PIN_RADIUS_MM,
)

SCHEMA = "MASCK_ONE_STRUCTURAL_FRAME_RETENTION_ROOT_CAPTURE_V4"
_MIN_DIGITAL_SECTION_MM = 0.02


class StructuralFrameRetentionRootCaptureV4Error(ValueError):
    pass


def _section_metrics() -> tuple[float, float, float, float, float]:
    inner_radius = CLEVIS_PIN_RADIUS_MM - CLEVIS_PIN_GROOVE_DEPTH_MM + CLIP_HOLE_RELIEF_MM
    outer_radius = CLEVIS_PIN_RADIUS_MM + CLEVIS_CLIP_RADIAL_THICKNESS_MM
    radial_annulus = outer_radius - inner_radius
    throat_side_stock = outer_radius - CLIP_THROAT_WIDTH_MM / 2.0
    axial_stock = CLEVIS_PIN_GROOVE_WIDTH_MM
    throat_fraction = CLIP_THROAT_WIDTH_MM / (2.0 * outer_radius)
    values = (inner_radius, outer_radius, radial_annulus, throat_side_stock, axial_stock, throat_fraction)
    if not all(math.isfinite(v) and v > 0.0 for v in values):
        raise StructuralFrameRetentionRootCaptureV4Error("retainer section metrics must be finite and positive")
    if radial_annulus <= _MIN_DIGITAL_SECTION_MM:
        raise StructuralFrameRetentionRootCaptureV4Error("retainer radial annulus collapses")
    if throat_side_stock <= _MIN_DIGITAL_SECTION_MM:
        raise StructuralFrameRetentionRootCaptureV4Error("retainer throat leaves no side-arm stock")
    if not 0.0 < throat_fraction < 1.0:
        raise StructuralFrameRetentionRootCaptureV4Error("retainer throat fraction must remain inside the outer diameter")
    return inner_radius, outer_radius, radial_annulus, throat_side_stock, axial_stock


@dataclass(frozen=True, slots=True)
class StructuralFrameRetentionRootCaptureV4:
    source_capture_v3_sha256: str
    inner_radius_mm: float
    outer_radius_mm: float
    radial_annulus_mm: float
    throat_side_stock_mm: float
    axial_stock_mm: float
    evidence_sha256: str
    residual_section_present: bool = True
    strength_validated: bool = False
    fatigue_validated: bool = False
    physical_validation_eligible: bool = False

    def validate(self) -> "StructuralFrameRetentionRootCaptureV4":
        v3 = capture_v3.build_structural_frame_retention_root_capture_v3()
        inner, outer, radial, side, axial = _section_metrics()
        if self.source_capture_v3_sha256 != v3.evidence_sha256:
            raise StructuralFrameRetentionRootCaptureV4Error("source capture V3 evidence is stale")
        expected = tuple(round(v, 12) for v in (inner, outer, radial, side, axial))
        actual = (self.inner_radius_mm, self.outer_radius_mm, self.radial_annulus_mm, self.throat_side_stock_mm, self.axial_stock_mm)
        if actual != expected:
            raise StructuralFrameRetentionRootCaptureV4Error("retainer residual-section evidence is stale")
        if self.residual_section_present is not True:
            raise StructuralFrameRetentionRootCaptureV4Error("controlled throat must leave positive nominal arm stock")
        payload = {
            "source_capture_v3_sha256": self.source_capture_v3_sha256,
            "inner_radius_mm": self.inner_radius_mm,
            "outer_radius_mm": self.outer_radius_mm,
            "radial_annulus_mm": self.radial_annulus_mm,
            "throat_side_stock_mm": self.throat_side_stock_mm,
            "axial_stock_mm": self.axial_stock_mm,
            "residual_section_present": self.residual_section_present,
        }
        digest = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        if self.evidence_sha256 != digest:
            raise StructuralFrameRetentionRootCaptureV4Error("capture V4 evidence digest is stale")
        if self.strength_validated is not False or self.fatigue_validated is not False or self.physical_validation_eligible is not False:
            raise StructuralFrameRetentionRootCaptureV4Error("nominal residual section is not strength, fatigue, or physical validation")
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        return {
            "schema": SCHEMA,
            "source_capture_v3_sha256": self.source_capture_v3_sha256,
            "inner_radius_mm": self.inner_radius_mm,
            "outer_radius_mm": self.outer_radius_mm,
            "radial_annulus_mm": self.radial_annulus_mm,
            "throat_side_stock_mm": self.throat_side_stock_mm,
            "axial_stock_mm": self.axial_stock_mm,
            "section_status": "POSITIVE_NOMINAL_SECTION_STRENGTH_UNVALIDATED",
            "residual_section_present": self.residual_section_present,
            "strength_validated": self.strength_validated,
            "fatigue_validated": self.fatigue_validated,
            "physical_validation_eligible": self.physical_validation_eligible,
            "evidence_sha256": self.evidence_sha256,
        }


def build_structural_frame_retention_root_capture_v4() -> StructuralFrameRetentionRootCaptureV4:
    v3 = capture_v3.build_structural_frame_retention_root_capture_v3()
    inner, outer, radial, side, axial = _section_metrics()
    metrics = tuple(round(v, 12) for v in (inner, outer, radial, side, axial))
    payload = {
        "source_capture_v3_sha256": v3.evidence_sha256,
        "inner_radius_mm": metrics[0],
        "outer_radius_mm": metrics[1],
        "radial_annulus_mm": metrics[2],
        "throat_side_stock_mm": metrics[3],
        "axial_stock_mm": metrics[4],
        "residual_section_present": True,
    }
    digest = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    return StructuralFrameRetentionRootCaptureV4(v3.evidence_sha256, *metrics, digest, True, False, False, False).validate()
