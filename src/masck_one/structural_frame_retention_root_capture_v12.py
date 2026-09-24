from __future__ import annotations

"""V12: bind both axial tolerance corners into integrated capture closure.

V10 integrates positive radial, throat and minimum axial margins. V11 separately
bounds maximum axial free play. V12 binds both evidence authorities so the primary
capture contract cannot remain green while the retainer becomes excessively loose.
This is drawing-level digital evidence only.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
import math

from . import structural_frame_retention_root_capture_v10 as capture_v10
from . import structural_frame_retention_root_capture_v11 as capture_v11

SCHEMA = "MASCK_ONE_STRUCTURAL_FRAME_RETENTION_ROOT_CAPTURE_V12"


class StructuralFrameRetentionRootCaptureV12Error(ValueError):
    pass


def _sources():
    integrated = capture_v10.build_structural_frame_retention_root_capture_v10().validate()
    free_play = capture_v11.build_structural_frame_retention_root_capture_v11().validate()
    return integrated, free_play


@dataclass(frozen=True, slots=True)
class StructuralFrameRetentionRootCaptureV12:
    source_capture_v10_sha256: str
    source_capture_v11_sha256: str
    governing_positive_margin_mm: float
    maximum_axial_free_play_mm: float
    maximum_axial_free_play_limit_mm: float
    axial_free_play_headroom_mm: float
    evidence_sha256: str
    complete_capture_closure_passes: bool = True
    process_capability_validated: bool = False
    physical_validation_eligible: bool = False

    def validate(self) -> "StructuralFrameRetentionRootCaptureV12":
        integrated, free_play = _sources()
        if self.source_capture_v10_sha256 != integrated.evidence_sha256:
            raise StructuralFrameRetentionRootCaptureV12Error("source capture V10 evidence is stale")
        if self.source_capture_v11_sha256 != free_play.evidence_sha256:
            raise StructuralFrameRetentionRootCaptureV12Error("source capture V11 evidence is stale")
        limit = capture_v11.MAX_WORST_CASE_AXIAL_FREE_PLAY_MM
        expected = (
            integrated.governing_margin_mm,
            free_play.maximum_axial_free_play_mm,
            limit,
            round(limit - free_play.maximum_axial_free_play_mm, 12),
        )
        actual = (
            self.governing_positive_margin_mm,
            self.maximum_axial_free_play_mm,
            self.maximum_axial_free_play_limit_mm,
            self.axial_free_play_headroom_mm,
        )
        if actual != expected or not all(math.isfinite(v) for v in actual):
            raise StructuralFrameRetentionRootCaptureV12Error("complete capture evidence is stale or invalid")
        if self.governing_positive_margin_mm <= 0.0:
            raise StructuralFrameRetentionRootCaptureV12Error("capture requires positive governing clearance")
        if self.maximum_axial_free_play_mm > self.maximum_axial_free_play_limit_mm:
            raise StructuralFrameRetentionRootCaptureV12Error("maximum axial free play exceeds drawing limit")
        if self.axial_free_play_headroom_mm < 0.0:
            raise StructuralFrameRetentionRootCaptureV12Error("axial free-play headroom is negative")
        if self.complete_capture_closure_passes is not True:
            raise StructuralFrameRetentionRootCaptureV12Error("complete capture closure must pass")
        payload = {
            "source_capture_v10_sha256": self.source_capture_v10_sha256,
            "source_capture_v11_sha256": self.source_capture_v11_sha256,
            "governing_positive_margin_mm": self.governing_positive_margin_mm,
            "maximum_axial_free_play_mm": self.maximum_axial_free_play_mm,
            "maximum_axial_free_play_limit_mm": self.maximum_axial_free_play_limit_mm,
            "axial_free_play_headroom_mm": self.axial_free_play_headroom_mm,
            "complete_capture_closure_passes": self.complete_capture_closure_passes,
        }
        digest = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        if self.evidence_sha256 != digest:
            raise StructuralFrameRetentionRootCaptureV12Error("capture V12 evidence digest is stale")
        if self.process_capability_validated is not False or self.physical_validation_eligible is not False:
            raise StructuralFrameRetentionRootCaptureV12Error("digital capture closure is not process capability or physical validation")
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        return {
            "schema": SCHEMA,
            "governing_positive_margin_mm": self.governing_positive_margin_mm,
            "maximum_axial_free_play_mm": self.maximum_axial_free_play_mm,
            "maximum_axial_free_play_limit_mm": self.maximum_axial_free_play_limit_mm,
            "axial_free_play_headroom_mm": self.axial_free_play_headroom_mm,
            "complete_capture_closure_passes": self.complete_capture_closure_passes,
            "process_capability_validated": self.process_capability_validated,
            "physical_validation_eligible": self.physical_validation_eligible,
            "evidence_sha256": self.evidence_sha256,
        }


def build_structural_frame_retention_root_capture_v12() -> StructuralFrameRetentionRootCaptureV12:
    integrated, free_play = _sources()
    limit = capture_v11.MAX_WORST_CASE_AXIAL_FREE_PLAY_MM
    values = (
        integrated.governing_margin_mm,
        free_play.maximum_axial_free_play_mm,
        limit,
        round(limit - free_play.maximum_axial_free_play_mm, 12),
    )
    payload = {
        "source_capture_v10_sha256": integrated.evidence_sha256,
        "source_capture_v11_sha256": free_play.evidence_sha256,
        "governing_positive_margin_mm": values[0],
        "maximum_axial_free_play_mm": values[1],
        "maximum_axial_free_play_limit_mm": values[2],
        "axial_free_play_headroom_mm": values[3],
        "complete_capture_closure_passes": True,
    }
    digest = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    return StructuralFrameRetentionRootCaptureV12(integrated.evidence_sha256, free_play.evidence_sha256, *values, digest).validate()
