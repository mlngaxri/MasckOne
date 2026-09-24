from __future__ import annotations

"""Tolerance-critical throat-to-bore transition audit for the split retainer.

V4 proves positive nominal material remains. V5 checks the much smaller geometric
margin between the free-throat half width and the retainer bore radius. This margin
controls whether the radial slot actually opens into the bore after manufacture.
No manufacturing process or tolerance is assumed, so this gate intentionally keeps
tolerance closure and physical validation unresolved.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
import math

from . import structural_frame_retention_root_capture_v4 as capture_v4
from .structural_frame_retention_root_capture_v2 import CLIP_THROAT_WIDTH_MM

SCHEMA = "MASCK_ONE_STRUCTURAL_FRAME_RETENTION_ROOT_CAPTURE_V5"
_MIN_POSITIVE_TRANSITION_MM = 0.0


class StructuralFrameRetentionRootCaptureV5Error(ValueError):
    pass


def _transition_metrics() -> tuple[float, float, float, float]:
    v4 = capture_v4.build_structural_frame_retention_root_capture_v4()
    throat_half = CLIP_THROAT_WIDTH_MM / 2.0
    bore_radius = v4.inner_radius_mm
    transition_margin = throat_half - bore_radius
    margin_fraction = transition_margin / bore_radius
    values = (throat_half, bore_radius, transition_margin, margin_fraction)
    if not all(math.isfinite(v) for v in values):
        raise StructuralFrameRetentionRootCaptureV5Error("retainer transition metrics must be finite")
    if throat_half <= 0.0 or bore_radius <= 0.0:
        raise StructuralFrameRetentionRootCaptureV5Error("retainer throat and bore dimensions must be positive")
    if transition_margin <= _MIN_POSITIVE_TRANSITION_MM:
        raise StructuralFrameRetentionRootCaptureV5Error(
            "retainer throat does not positively open into the bore at nominal geometry"
        )
    return throat_half, bore_radius, transition_margin, margin_fraction


@dataclass(frozen=True, slots=True)
class StructuralFrameRetentionRootCaptureV5:
    source_capture_v4_sha256: str
    throat_half_width_mm: float
    bore_radius_mm: float
    throat_to_bore_transition_margin_mm: float
    transition_margin_fraction_of_bore: float
    evidence_sha256: str
    nominal_bore_connectivity_present: bool = True
    manufacturing_tolerance_closure_required: bool = True
    manufactured_connectivity_validated: bool = False
    physical_validation_eligible: bool = False

    def validate(self) -> "StructuralFrameRetentionRootCaptureV5":
        v4 = capture_v4.build_structural_frame_retention_root_capture_v4()
        throat_half, bore_radius, margin, fraction = _transition_metrics()
        if self.source_capture_v4_sha256 != v4.evidence_sha256:
            raise StructuralFrameRetentionRootCaptureV5Error("source capture V4 evidence is stale")
        expected = tuple(round(v, 12) for v in (throat_half, bore_radius, margin, fraction))
        actual = (
            self.throat_half_width_mm,
            self.bore_radius_mm,
            self.throat_to_bore_transition_margin_mm,
            self.transition_margin_fraction_of_bore,
        )
        if actual != expected:
            raise StructuralFrameRetentionRootCaptureV5Error("retainer transition evidence is stale")
        if self.nominal_bore_connectivity_present is not True:
            raise StructuralFrameRetentionRootCaptureV5Error("nominal throat-to-bore connectivity must remain positive")
        if self.manufacturing_tolerance_closure_required is not True:
            raise StructuralFrameRetentionRootCaptureV5Error(
                "nominal transition margin cannot waive manufacturing tolerance closure"
            )
        payload = {
            "source_capture_v4_sha256": self.source_capture_v4_sha256,
            "throat_half_width_mm": self.throat_half_width_mm,
            "bore_radius_mm": self.bore_radius_mm,
            "throat_to_bore_transition_margin_mm": self.throat_to_bore_transition_margin_mm,
            "transition_margin_fraction_of_bore": self.transition_margin_fraction_of_bore,
            "nominal_bore_connectivity_present": self.nominal_bore_connectivity_present,
            "manufacturing_tolerance_closure_required": self.manufacturing_tolerance_closure_required,
        }
        digest = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        if self.evidence_sha256 != digest:
            raise StructuralFrameRetentionRootCaptureV5Error("capture V5 evidence digest is stale")
        if self.manufactured_connectivity_validated is not False or self.physical_validation_eligible is not False:
            raise StructuralFrameRetentionRootCaptureV5Error(
                "nominal throat transition is not manufactured or physical validation"
            )
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        return {
            "schema": SCHEMA,
            "source_capture_v4_sha256": self.source_capture_v4_sha256,
            "throat_half_width_mm": self.throat_half_width_mm,
            "bore_radius_mm": self.bore_radius_mm,
            "throat_to_bore_transition_margin_mm": self.throat_to_bore_transition_margin_mm,
            "transition_margin_fraction_of_bore": self.transition_margin_fraction_of_bore,
            "transition_status": "NOMINAL_CONNECTIVITY_PRESENT_TOLERANCE_CLOSURE_REQUIRED",
            "nominal_bore_connectivity_present": self.nominal_bore_connectivity_present,
            "manufacturing_tolerance_closure_required": self.manufacturing_tolerance_closure_required,
            "manufactured_connectivity_validated": self.manufactured_connectivity_validated,
            "physical_validation_eligible": self.physical_validation_eligible,
            "evidence_sha256": self.evidence_sha256,
        }


def build_structural_frame_retention_root_capture_v5() -> StructuralFrameRetentionRootCaptureV5:
    v4 = capture_v4.build_structural_frame_retention_root_capture_v4()
    metrics = tuple(round(v, 12) for v in _transition_metrics())
    payload = {
        "source_capture_v4_sha256": v4.evidence_sha256,
        "throat_half_width_mm": metrics[0],
        "bore_radius_mm": metrics[1],
        "throat_to_bore_transition_margin_mm": metrics[2],
        "transition_margin_fraction_of_bore": metrics[3],
        "nominal_bore_connectivity_present": True,
        "manufacturing_tolerance_closure_required": True,
    }
    digest = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    return StructuralFrameRetentionRootCaptureV5(
        v4.evidence_sha256,
        *metrics,
        digest,
        True,
        True,
        False,
        False,
    ).validate()
