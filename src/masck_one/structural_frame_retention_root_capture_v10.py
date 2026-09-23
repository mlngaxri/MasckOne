from __future__ import annotations

"""Integrated dimensional closure for the split-retainer capture.

V8 closes the radial/throat stack and V9 closes the axial groove stack. V10 binds
both authorities into one fail-closed acceptance contract so a future change cannot
pass one axis while silently bypassing the other. This is digital drawing evidence,
not process capability or physical validation.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
import math

from . import structural_frame_retention_root_capture_v8 as capture_v8
from . import structural_frame_retention_root_capture_v9 as capture_v9

SCHEMA = "MASCK_ONE_STRUCTURAL_FRAME_RETENTION_ROOT_CAPTURE_V10"


class StructuralFrameRetentionRootCaptureV10Error(ValueError):
    pass


def _sources():
    radial = capture_v8.build_structural_frame_retention_root_capture_v8().validate()
    axial = capture_v9.build_structural_frame_retention_root_capture_v9().validate()
    return radial, axial


@dataclass(frozen=True, slots=True)
class StructuralFrameRetentionRootCaptureV10:
    source_capture_v8_sha256: str
    source_capture_v9_sha256: str
    worst_transition_margin_mm: float
    worst_radial_capture_margin_mm: float
    worst_axial_clearance_mm: float
    governing_margin_mm: float
    evidence_sha256: str
    integrated_dimensional_closure_passes: bool = True
    process_capability_validated: bool = False
    physical_validation_eligible: bool = False

    def validate(self) -> "StructuralFrameRetentionRootCaptureV10":
        radial, axial = _sources()
        if self.source_capture_v8_sha256 != radial.evidence_sha256:
            raise StructuralFrameRetentionRootCaptureV10Error("source capture V8 evidence is stale")
        if self.source_capture_v9_sha256 != axial.evidence_sha256:
            raise StructuralFrameRetentionRootCaptureV10Error("source capture V9 evidence is stale")
        expected = (radial.worst_transition_margin_mm, radial.worst_radial_capture_margin_mm, axial.worst_case_axial_clearance_mm)
        actual = (self.worst_transition_margin_mm, self.worst_radial_capture_margin_mm, self.worst_axial_clearance_mm)
        if actual != expected or not all(math.isfinite(x) and x > 0.0 for x in actual):
            raise StructuralFrameRetentionRootCaptureV10Error("integrated capture margins are stale or non-positive")
        governing = min(expected)
        if self.governing_margin_mm != governing:
            raise StructuralFrameRetentionRootCaptureV10Error("governing capture margin is stale")
        if self.integrated_dimensional_closure_passes is not True:
            raise StructuralFrameRetentionRootCaptureV10Error("integrated dimensional closure must pass")
        payload = {
            "source_capture_v8_sha256": self.source_capture_v8_sha256,
            "source_capture_v9_sha256": self.source_capture_v9_sha256,
            "margins_mm": actual,
            "governing_margin_mm": self.governing_margin_mm,
            "integrated_dimensional_closure_passes": self.integrated_dimensional_closure_passes,
        }
        digest = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        if self.evidence_sha256 != digest:
            raise StructuralFrameRetentionRootCaptureV10Error("capture V10 evidence digest is stale")
        if self.process_capability_validated is not False or self.physical_validation_eligible is not False:
            raise StructuralFrameRetentionRootCaptureV10Error("integrated digital closure is not process capability or physical validation")
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        return {
            "schema": SCHEMA,
            "worst_transition_margin_mm": self.worst_transition_margin_mm,
            "worst_radial_capture_margin_mm": self.worst_radial_capture_margin_mm,
            "worst_axial_clearance_mm": self.worst_axial_clearance_mm,
            "governing_margin_mm": self.governing_margin_mm,
            "integrated_dimensional_closure_passes": self.integrated_dimensional_closure_passes,
            "process_capability_validated": self.process_capability_validated,
            "physical_validation_eligible": self.physical_validation_eligible,
            "evidence_sha256": self.evidence_sha256,
        }


def build_structural_frame_retention_root_capture_v10() -> StructuralFrameRetentionRootCaptureV10:
    radial, axial = _sources()
    margins = (radial.worst_transition_margin_mm, radial.worst_radial_capture_margin_mm, axial.worst_case_axial_clearance_mm)
    governing = min(margins)
    payload = {
        "source_capture_v8_sha256": radial.evidence_sha256,
        "source_capture_v9_sha256": axial.evidence_sha256,
        "margins_mm": margins,
        "governing_margin_mm": governing,
        "integrated_dimensional_closure_passes": True,
    }
    digest = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    return StructuralFrameRetentionRootCaptureV10(radial.evidence_sha256, axial.evidence_sha256, *margins, governing, digest).validate()
