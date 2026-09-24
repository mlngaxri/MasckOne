from __future__ import annotations

"""V13: quantify axial free-play headroom and verify both candidate tolerance corners.

V12 exposes zero headroom at the maximum axial free-play corner. V13 does not
silently tighten drawing tolerances. It turns that boundary condition into an
explicit sensitivity contract and proves that the candidate allocation preserves
the minimum-clearance requirement as well as recovering free-play reserve.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
import math

from . import structural_frame_retention_root_capture_v2 as capture_v2
from . import structural_frame_retention_root_capture_v9 as capture_v9
from . import structural_frame_retention_root_capture_v12 as capture_v12
from .structural_frame_retention_roots import CLEVIS_PIN_GROOVE_WIDTH_MM

SCHEMA = "MASCK_ONE_STRUCTURAL_FRAME_RETENTION_ROOT_CAPTURE_V13"
TARGET_AXIAL_FREE_PLAY_HEADROOM_MM = 0.02


class StructuralFrameRetentionRootCaptureV13Error(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class StructuralFrameRetentionRootCaptureV13:
    source_capture_v12_sha256: str
    current_headroom_mm: float
    target_headroom_mm: float
    additional_headroom_required_mm: float
    combined_bilateral_tolerance_reduction_required_mm: float
    equal_split_reduction_per_feature_mm: float
    candidate_clip_tolerance_mm: float
    candidate_groove_tolerance_mm: float
    candidate_minimum_axial_clearance_mm: float
    candidate_maximum_axial_free_play_mm: float
    evidence_sha256: str
    nominal_geometry_unchanged: bool = True
    process_capability_validated: bool = False
    physical_validation_eligible: bool = False

    def validate(self) -> "StructuralFrameRetentionRootCaptureV13":
        prior = capture_v12.build_structural_frame_retention_root_capture_v12().validate()
        if self.source_capture_v12_sha256 != prior.evidence_sha256:
            raise StructuralFrameRetentionRootCaptureV13Error("capture V13 is not bound to current V12 authority")
        current = prior.axial_free_play_headroom_mm
        required = max(0.0, TARGET_AXIAL_FREE_PLAY_HEADROOM_MM - current)
        split = required / 2.0
        clip_candidate = capture_v9.CLIP_AXIAL_THICKNESS_BILATERAL_TOLERANCE_MM - split
        groove_candidate = capture_v9.GROOVE_WIDTH_BILATERAL_TOLERANCE_MM - split
        nominal_clearance = CLEVIS_PIN_GROOVE_WIDTH_MM - capture_v2.CLIP_AXIAL_THICKNESS_MM
        candidate_min = nominal_clearance - clip_candidate - groove_candidate
        candidate_max = nominal_clearance + clip_candidate + groove_candidate
        expected = tuple(round(v, 12) for v in (
            current, TARGET_AXIAL_FREE_PLAY_HEADROOM_MM, required, required, split,
            clip_candidate, groove_candidate, candidate_min, candidate_max,
        ))
        actual = (
            self.current_headroom_mm, self.target_headroom_mm,
            self.additional_headroom_required_mm,
            self.combined_bilateral_tolerance_reduction_required_mm,
            self.equal_split_reduction_per_feature_mm,
            self.candidate_clip_tolerance_mm, self.candidate_groove_tolerance_mm,
            self.candidate_minimum_axial_clearance_mm,
            self.candidate_maximum_axial_free_play_mm,
        )
        if actual != expected or not all(math.isfinite(v) and v >= 0.0 for v in actual):
            raise StructuralFrameRetentionRootCaptureV13Error("axial tolerance sensitivity evidence is stale or invalid")
        if self.candidate_clip_tolerance_mm <= 0.0 or self.candidate_groove_tolerance_mm <= 0.0:
            raise StructuralFrameRetentionRootCaptureV13Error("candidate drawing tolerances must remain positive")
        if self.candidate_minimum_axial_clearance_mm < capture_v9.MIN_WORST_CASE_AXIAL_CLEARANCE_MM:
            raise StructuralFrameRetentionRootCaptureV13Error("candidate allocation violates minimum axial clearance")
        recovered = prior.maximum_axial_free_play_limit_mm - self.candidate_maximum_axial_free_play_mm
        if round(recovered, 12) < self.target_headroom_mm:
            raise StructuralFrameRetentionRootCaptureV13Error("candidate allocation does not recover target headroom")
        if self.nominal_geometry_unchanged is not True:
            raise StructuralFrameRetentionRootCaptureV13Error("V13 must not change nominal geometry")
        payload = {"source_capture_v12_sha256": self.source_capture_v12_sha256, "values": actual,
                   "nominal_geometry_unchanged": self.nominal_geometry_unchanged}
        digest = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        if self.evidence_sha256 != digest:
            raise StructuralFrameRetentionRootCaptureV13Error("capture V13 evidence digest is stale")
        if self.process_capability_validated is not False or self.physical_validation_eligible is not False:
            raise StructuralFrameRetentionRootCaptureV13Error("tolerance sensitivity is not process capability or physical validation")
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        return {
            "schema": SCHEMA,
            "current_headroom_mm": self.current_headroom_mm,
            "target_headroom_mm": self.target_headroom_mm,
            "additional_headroom_required_mm": self.additional_headroom_required_mm,
            "combined_bilateral_tolerance_reduction_required_mm": self.combined_bilateral_tolerance_reduction_required_mm,
            "equal_split_reduction_per_feature_mm": self.equal_split_reduction_per_feature_mm,
            "candidate_clip_tolerance_mm": self.candidate_clip_tolerance_mm,
            "candidate_groove_tolerance_mm": self.candidate_groove_tolerance_mm,
            "candidate_minimum_axial_clearance_mm": self.candidate_minimum_axial_clearance_mm,
            "candidate_maximum_axial_free_play_mm": self.candidate_maximum_axial_free_play_mm,
            "nominal_geometry_unchanged": self.nominal_geometry_unchanged,
            "process_capability_validated": self.process_capability_validated,
            "physical_validation_eligible": self.physical_validation_eligible,
            "evidence_sha256": self.evidence_sha256,
        }


def build_structural_frame_retention_root_capture_v13() -> StructuralFrameRetentionRootCaptureV13:
    prior = capture_v12.build_structural_frame_retention_root_capture_v12().validate()
    current = prior.axial_free_play_headroom_mm
    required = max(0.0, TARGET_AXIAL_FREE_PLAY_HEADROOM_MM - current)
    split = required / 2.0
    clip_candidate = capture_v9.CLIP_AXIAL_THICKNESS_BILATERAL_TOLERANCE_MM - split
    groove_candidate = capture_v9.GROOVE_WIDTH_BILATERAL_TOLERANCE_MM - split
    nominal_clearance = CLEVIS_PIN_GROOVE_WIDTH_MM - capture_v2.CLIP_AXIAL_THICKNESS_MM
    values = tuple(round(v, 12) for v in (
        current, TARGET_AXIAL_FREE_PLAY_HEADROOM_MM, required, required, split,
        clip_candidate, groove_candidate,
        nominal_clearance - clip_candidate - groove_candidate,
        nominal_clearance + clip_candidate + groove_candidate,
    ))
    payload = {"source_capture_v12_sha256": prior.evidence_sha256, "values": values,
               "nominal_geometry_unchanged": True}
    digest = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    return StructuralFrameRetentionRootCaptureV13(prior.evidence_sha256, *values, digest).validate()
