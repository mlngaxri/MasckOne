from __future__ import annotations

"""V11: bound the complete axial free-play window of the split retainer.

V9 proves minimum axial assembly clearance. V11 also checks the opposite tolerance
corner, where the groove is widest and the retainer is thinnest, so a tolerance
change cannot preserve assembly clearance while silently creating excessive axial
float. This is drawing-level digital evidence only.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
import math

from . import structural_frame_retention_root_capture_v9 as capture_v9

SCHEMA = "MASCK_ONE_STRUCTURAL_FRAME_RETENTION_ROOT_CAPTURE_V11"
MAX_WORST_CASE_AXIAL_FREE_PLAY_MM = 0.25


class StructuralFrameRetentionRootCaptureV11Error(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class StructuralFrameRetentionRootCaptureV11:
    source_capture_v9_sha256: str
    minimum_axial_free_play_mm: float
    nominal_axial_free_play_mm: float
    maximum_axial_free_play_mm: float
    axial_free_play_window_mm: float
    evidence_sha256: str
    axial_free_play_window_passes: bool = True
    process_capability_validated: bool = False
    physical_validation_eligible: bool = False

    def validate(self) -> "StructuralFrameRetentionRootCaptureV11":
        prior = capture_v9.build_structural_frame_retention_root_capture_v9().validate()
        expected_min = prior.groove_width_min_mm - prior.clip_thickness_max_mm
        expected_nom = prior.nominal_axial_clearance_mm
        expected_max = prior.groove_width_max_mm - prior.clip_thickness_min_mm
        expected_window = expected_max - expected_min
        expected = tuple(round(v, 12) for v in (expected_min, expected_nom, expected_max, expected_window))
        actual = (
            self.minimum_axial_free_play_mm,
            self.nominal_axial_free_play_mm,
            self.maximum_axial_free_play_mm,
            self.axial_free_play_window_mm,
        )
        if self.source_capture_v9_sha256 != prior.evidence_sha256:
            raise StructuralFrameRetentionRootCaptureV11Error("source capture V9 evidence is stale")
        if actual != expected or not all(math.isfinite(v) and v > 0.0 for v in actual):
            raise StructuralFrameRetentionRootCaptureV11Error("axial free-play window evidence is stale or invalid")
        if not (expected[0] <= expected[1] <= expected[2]):
            raise StructuralFrameRetentionRootCaptureV11Error("axial free-play ordering is invalid")
        if expected[2] > MAX_WORST_CASE_AXIAL_FREE_PLAY_MM:
            raise StructuralFrameRetentionRootCaptureV11Error("worst-case axial free play exceeds drawing limit")
        if self.axial_free_play_window_passes is not True:
            raise StructuralFrameRetentionRootCaptureV11Error("axial free-play window must pass")
        payload = {
            "source_capture_v9_sha256": self.source_capture_v9_sha256,
            "free_play_mm": actual,
            "maximum_worst_case_axial_free_play_mm": MAX_WORST_CASE_AXIAL_FREE_PLAY_MM,
            "axial_free_play_window_passes": self.axial_free_play_window_passes,
        }
        digest = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        if self.evidence_sha256 != digest:
            raise StructuralFrameRetentionRootCaptureV11Error("capture V11 evidence digest is stale")
        if self.process_capability_validated is not False or self.physical_validation_eligible is not False:
            raise StructuralFrameRetentionRootCaptureV11Error("digital free-play closure is not process capability or physical validation")
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        return {
            "schema": SCHEMA,
            "minimum_axial_free_play_mm": self.minimum_axial_free_play_mm,
            "nominal_axial_free_play_mm": self.nominal_axial_free_play_mm,
            "maximum_axial_free_play_mm": self.maximum_axial_free_play_mm,
            "axial_free_play_window_mm": self.axial_free_play_window_mm,
            "maximum_worst_case_axial_free_play_mm": MAX_WORST_CASE_AXIAL_FREE_PLAY_MM,
            "axial_free_play_window_passes": self.axial_free_play_window_passes,
            "process_capability_validated": self.process_capability_validated,
            "physical_validation_eligible": self.physical_validation_eligible,
            "evidence_sha256": self.evidence_sha256,
        }


def build_structural_frame_retention_root_capture_v11() -> StructuralFrameRetentionRootCaptureV11:
    prior = capture_v9.build_structural_frame_retention_root_capture_v9().validate()
    values = tuple(round(v, 12) for v in (
        prior.groove_width_min_mm - prior.clip_thickness_max_mm,
        prior.nominal_axial_clearance_mm,
        prior.groove_width_max_mm - prior.clip_thickness_min_mm,
        (prior.groove_width_max_mm - prior.clip_thickness_min_mm) - (prior.groove_width_min_mm - prior.clip_thickness_max_mm),
    ))
    payload = {
        "source_capture_v9_sha256": prior.evidence_sha256,
        "free_play_mm": values,
        "maximum_worst_case_axial_free_play_mm": MAX_WORST_CASE_AXIAL_FREE_PLAY_MM,
        "axial_free_play_window_passes": True,
    }
    digest = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    return StructuralFrameRetentionRootCaptureV11(prior.evidence_sha256, *values, digest).validate()
