from __future__ import annotations

"""Worst-case interval verification for the V7 split-retainer tolerance allocation."""

from dataclasses import dataclass
from hashlib import sha256
import json
import math

from . import structural_frame_retention_root_capture_v7 as capture_v7
from . import structural_frame_retention_root_capture_v2 as capture_v2
from .structural_frame_retention_roots import (
    CLEVIS_PIN_GROOVE_DEPTH_MM,
    CLEVIS_PIN_RADIUS_MM,
)

SCHEMA = "MASCK_ONE_STRUCTURAL_FRAME_RETENTION_ROOT_CAPTURE_V8"


class StructuralFrameRetentionRootCaptureV8Error(ValueError):
    pass


def _nominal_geometry() -> tuple[float, float, float]:
    """Return throat, seated clip-bore diameter and pin diameter from live authority.

    V8 previously attempted to read convenience fields that do not exist on the V2
    evidence dataclass. Bind directly to the authoritative V2 throat constant and the
    accepted root pin/groove constants instead, so the worst-case audit is executable
    and cannot silently depend on an absent duplicate representation.
    """
    throat = capture_v2.CLIP_THROAT_WIDTH_MM
    bore = 2.0 * (
        CLEVIS_PIN_RADIUS_MM
        - CLEVIS_PIN_GROOVE_DEPTH_MM
        + capture_v2.CLIP_HOLE_RELIEF_MM
    )
    pin = 2.0 * CLEVIS_PIN_RADIUS_MM
    values = (throat, bore, pin)
    if not all(math.isfinite(v) and v > 0.0 for v in values):
        raise StructuralFrameRetentionRootCaptureV8Error("nominal capture geometry must be finite and positive")
    return values


def _intervals() -> tuple[float, ...]:
    """Resolve each interval from its own V7 drawing tolerance."""
    v7 = capture_v7.build_structural_frame_retention_root_capture_v7()
    throat, bore, pin = _nominal_geometry()
    tt = v7.throat_width_bilateral_tolerance_mm
    bt = v7.clip_bore_diameter_bilateral_tolerance_mm
    pt = v7.pin_diameter_bilateral_tolerance_mm
    return tuple(round(x, 12) for x in (
        throat - tt, throat + tt,
        bore - bt, bore + bt,
        pin - pt, pin + pt,
        (throat - tt - (bore + bt)) / 2.0,
        (pin - pt) - (throat + tt),
    ))


@dataclass(frozen=True, slots=True)
class StructuralFrameRetentionRootCaptureV8:
    source_capture_v7_sha256: str
    throat_min_mm: float
    throat_max_mm: float
    clip_bore_min_mm: float
    clip_bore_max_mm: float
    pin_min_mm: float
    pin_max_mm: float
    worst_transition_margin_mm: float
    worst_radial_capture_margin_mm: float
    evidence_sha256: str
    worst_case_stack_passes: bool = True
    process_capability_validated: bool = False
    physical_validation_eligible: bool = False

    def validate(self) -> "StructuralFrameRetentionRootCaptureV8":
        v7 = capture_v7.build_structural_frame_retention_root_capture_v7()
        expected = _intervals()
        actual = (self.throat_min_mm, self.throat_max_mm, self.clip_bore_min_mm,
                  self.clip_bore_max_mm, self.pin_min_mm, self.pin_max_mm,
                  self.worst_transition_margin_mm, self.worst_radial_capture_margin_mm)
        if self.source_capture_v7_sha256 != v7.evidence_sha256:
            raise StructuralFrameRetentionRootCaptureV8Error("source capture V7 evidence is stale")
        if actual != expected:
            raise StructuralFrameRetentionRootCaptureV8Error("worst-case capture stack evidence is stale")
        if not all(math.isfinite(x) for x in actual) or expected[6] <= 0.0 or expected[7] <= 0.0:
            raise StructuralFrameRetentionRootCaptureV8Error("V7 tolerance stack does not preserve positive capture margins")
        if self.worst_case_stack_passes is not True:
            raise StructuralFrameRetentionRootCaptureV8Error("worst-case capture stack must pass")
        payload = {"source_capture_v7_sha256": self.source_capture_v7_sha256, "intervals": actual,
                   "worst_case_stack_passes": self.worst_case_stack_passes}
        digest = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        if self.evidence_sha256 != digest:
            raise StructuralFrameRetentionRootCaptureV8Error("capture V8 evidence digest is stale")
        if self.process_capability_validated is not False or self.physical_validation_eligible is not False:
            raise StructuralFrameRetentionRootCaptureV8Error("digital worst-case stack is not process capability or physical validation")
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        return {"schema": SCHEMA, "worst_transition_margin_mm": self.worst_transition_margin_mm,
                "worst_radial_capture_margin_mm": self.worst_radial_capture_margin_mm,
                "worst_case_stack_passes": self.worst_case_stack_passes,
                "process_capability_validated": self.process_capability_validated,
                "physical_validation_eligible": self.physical_validation_eligible,
                "evidence_sha256": self.evidence_sha256}


def build_structural_frame_retention_root_capture_v8() -> StructuralFrameRetentionRootCaptureV8:
    v7 = capture_v7.build_structural_frame_retention_root_capture_v7()
    values = _intervals()
    payload = {"source_capture_v7_sha256": v7.evidence_sha256, "intervals": values, "worst_case_stack_passes": True}
    digest = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    return StructuralFrameRetentionRootCaptureV8(v7.evidence_sha256, *values, digest).validate()
