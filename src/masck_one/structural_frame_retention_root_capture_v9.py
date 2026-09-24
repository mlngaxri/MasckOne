from __future__ import annotations

"""Worst-case axial assembly-clearance verification for the V2 split retainer."""

from dataclasses import dataclass
from hashlib import sha256
import json
import math

from . import structural_frame_retention_root_capture_v2 as capture_v2
from .structural_frame_retention_roots import CLEVIS_PIN_GROOVE_WIDTH_MM

SCHEMA = "MASCK_ONE_STRUCTURAL_FRAME_RETENTION_ROOT_CAPTURE_V9"

# Drawing-level bilateral targets only. They are deliberately independent so a
# future allocation change cannot silently apply one feature's tolerance to both.
CLIP_AXIAL_THICKNESS_BILATERAL_TOLERANCE_MM = 0.05
GROOVE_WIDTH_BILATERAL_TOLERANCE_MM = 0.05
MIN_WORST_CASE_AXIAL_CLEARANCE_MM = 0.05


class StructuralFrameRetentionRootCaptureV9Error(ValueError):
    pass


def _axial_stack() -> tuple[float, ...]:
    clip_nom = capture_v2.CLIP_AXIAL_THICKNESS_MM
    groove_nom = CLEVIS_PIN_GROOVE_WIDTH_MM
    ct = CLIP_AXIAL_THICKNESS_BILATERAL_TOLERANCE_MM
    gt = GROOVE_WIDTH_BILATERAL_TOLERANCE_MM
    values = (
        clip_nom - ct,
        clip_nom + ct,
        groove_nom - gt,
        groove_nom + gt,
        (groove_nom - gt) - (clip_nom + ct),
        groove_nom - clip_nom,
    )
    if not all(math.isfinite(v) and v > 0.0 for v in values):
        raise StructuralFrameRetentionRootCaptureV9Error("axial tolerance stack must remain finite and positive")
    return tuple(round(v, 12) for v in values)


@dataclass(frozen=True, slots=True)
class StructuralFrameRetentionRootCaptureV9:
    source_capture_v2_sha256: str
    clip_thickness_min_mm: float
    clip_thickness_max_mm: float
    groove_width_min_mm: float
    groove_width_max_mm: float
    worst_case_axial_clearance_mm: float
    nominal_axial_clearance_mm: float
    evidence_sha256: str
    drawing_tolerance_stack_passes: bool = True
    process_capability_validated: bool = False
    physical_validation_eligible: bool = False

    def validate(self) -> "StructuralFrameRetentionRootCaptureV9":
        v2 = capture_v2.build_structural_frame_retention_root_capture_v2()
        expected = _axial_stack()
        actual = (
            self.clip_thickness_min_mm,
            self.clip_thickness_max_mm,
            self.groove_width_min_mm,
            self.groove_width_max_mm,
            self.worst_case_axial_clearance_mm,
            self.nominal_axial_clearance_mm,
        )
        if self.source_capture_v2_sha256 != v2.evidence_sha256:
            raise StructuralFrameRetentionRootCaptureV9Error("source capture V2 evidence is stale")
        if actual != expected:
            raise StructuralFrameRetentionRootCaptureV9Error("axial tolerance-stack evidence is stale")
        if expected[4] < MIN_WORST_CASE_AXIAL_CLEARANCE_MM:
            raise StructuralFrameRetentionRootCaptureV9Error("worst-case axial groove clearance is below drawing target")
        if self.drawing_tolerance_stack_passes is not True:
            raise StructuralFrameRetentionRootCaptureV9Error("axial drawing tolerance stack must pass")
        payload = {
            "source_capture_v2_sha256": self.source_capture_v2_sha256,
            "clip_axial_thickness_bilateral_tolerance_mm": CLIP_AXIAL_THICKNESS_BILATERAL_TOLERANCE_MM,
            "groove_width_bilateral_tolerance_mm": GROOVE_WIDTH_BILATERAL_TOLERANCE_MM,
            "intervals": actual,
            "drawing_tolerance_stack_passes": self.drawing_tolerance_stack_passes,
        }
        digest = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        if self.evidence_sha256 != digest:
            raise StructuralFrameRetentionRootCaptureV9Error("capture V9 evidence digest is stale")
        if self.process_capability_validated is not False or self.physical_validation_eligible is not False:
            raise StructuralFrameRetentionRootCaptureV9Error("drawing tolerance closure is not process capability or physical validation")
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        return {
            "schema": SCHEMA,
            "clip_axial_thickness_bilateral_tolerance_mm": CLIP_AXIAL_THICKNESS_BILATERAL_TOLERANCE_MM,
            "groove_width_bilateral_tolerance_mm": GROOVE_WIDTH_BILATERAL_TOLERANCE_MM,
            "worst_case_axial_clearance_mm": self.worst_case_axial_clearance_mm,
            "nominal_axial_clearance_mm": self.nominal_axial_clearance_mm,
            "drawing_tolerance_stack_passes": self.drawing_tolerance_stack_passes,
            "process_capability_validated": self.process_capability_validated,
            "physical_validation_eligible": self.physical_validation_eligible,
            "evidence_sha256": self.evidence_sha256,
        }


def build_structural_frame_retention_root_capture_v9() -> StructuralFrameRetentionRootCaptureV9:
    v2 = capture_v2.build_structural_frame_retention_root_capture_v2()
    values = _axial_stack()
    payload = {
        "source_capture_v2_sha256": v2.evidence_sha256,
        "clip_axial_thickness_bilateral_tolerance_mm": CLIP_AXIAL_THICKNESS_BILATERAL_TOLERANCE_MM,
        "groove_width_bilateral_tolerance_mm": GROOVE_WIDTH_BILATERAL_TOLERANCE_MM,
        "intervals": values,
        "drawing_tolerance_stack_passes": True,
    }
    digest = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    return StructuralFrameRetentionRootCaptureV9(v2.evidence_sha256, *values, digest).validate()
