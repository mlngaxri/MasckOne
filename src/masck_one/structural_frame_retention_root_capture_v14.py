from __future__ import annotations

"""V14: prove the feasible unequal axial tolerance-allocation envelope.

V13 identifies an equal-split candidate. V14 removes the hidden assumption that
both features must receive identical tolerances. It derives the complete positive
allocation interval that preserves the V13 free-play reserve and minimum-clearance
contract without changing nominal geometry or claiming process capability.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
import math

from . import structural_frame_retention_root_capture_v9 as capture_v9
from . import structural_frame_retention_root_capture_v13 as capture_v13

SCHEMA = "MASCK_ONE_STRUCTURAL_FRAME_RETENTION_ROOT_CAPTURE_V14"
MIN_FEATURE_BILATERAL_TOLERANCE_MM = 0.01


class StructuralFrameRetentionRootCaptureV14Error(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class StructuralFrameRetentionRootCaptureV14:
    source_capture_v13_sha256: str
    required_combined_tolerance_budget_mm: float
    minimum_feature_tolerance_mm: float
    clip_tolerance_min_mm: float
    clip_tolerance_max_mm: float
    groove_tolerance_min_mm: float
    groove_tolerance_max_mm: float
    allocation_span_mm: float
    evidence_sha256: str
    nominal_geometry_unchanged: bool = True
    process_capability_validated: bool = False
    physical_validation_eligible: bool = False

    def validate(self) -> "StructuralFrameRetentionRootCaptureV14":
        prior = capture_v13.build_structural_frame_retention_root_capture_v13().validate()
        if self.source_capture_v13_sha256 != prior.evidence_sha256:
            raise StructuralFrameRetentionRootCaptureV14Error("capture V14 is not bound to current V13 authority")
        budget = prior.candidate_clip_tolerance_mm + prior.candidate_groove_tolerance_mm
        floor = MIN_FEATURE_BILATERAL_TOLERANCE_MM
        upper = budget - floor
        if upper < floor:
            raise StructuralFrameRetentionRootCaptureV14Error("combined tolerance budget cannot support the feature tolerance floor")
        expected = tuple(round(v, 12) for v in (budget, floor, floor, upper, floor, upper, upper - floor))
        actual = (
            self.required_combined_tolerance_budget_mm,
            self.minimum_feature_tolerance_mm,
            self.clip_tolerance_min_mm,
            self.clip_tolerance_max_mm,
            self.groove_tolerance_min_mm,
            self.groove_tolerance_max_mm,
            self.allocation_span_mm,
        )
        if actual != expected or not all(math.isfinite(v) and v >= 0.0 for v in actual):
            raise StructuralFrameRetentionRootCaptureV14Error("axial allocation envelope evidence is stale or invalid")
        if round(self.clip_tolerance_min_mm + self.groove_tolerance_max_mm, 12) != round(budget, 12):
            raise StructuralFrameRetentionRootCaptureV14Error("clip-min allocation does not conserve tolerance budget")
        if round(self.clip_tolerance_max_mm + self.groove_tolerance_min_mm, 12) != round(budget, 12):
            raise StructuralFrameRetentionRootCaptureV14Error("groove-min allocation does not conserve tolerance budget")
        current_budget = capture_v9.CLIP_AXIAL_THICKNESS_BILATERAL_TOLERANCE_MM + capture_v9.GROOVE_WIDTH_BILATERAL_TOLERANCE_MM
        if budget >= current_budget:
            raise StructuralFrameRetentionRootCaptureV14Error("V14 must retain the V13 tolerance-budget recovery")
        if self.nominal_geometry_unchanged is not True:
            raise StructuralFrameRetentionRootCaptureV14Error("V14 must not change nominal geometry")
        payload = {"source_capture_v13_sha256": self.source_capture_v13_sha256, "values": actual,
                   "nominal_geometry_unchanged": self.nominal_geometry_unchanged}
        digest = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        if self.evidence_sha256 != digest:
            raise StructuralFrameRetentionRootCaptureV14Error("capture V14 evidence digest is stale")
        if self.process_capability_validated is not False or self.physical_validation_eligible is not False:
            raise StructuralFrameRetentionRootCaptureV14Error("allocation envelope is not process capability or physical validation")
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        return {"schema": SCHEMA, "required_combined_tolerance_budget_mm": self.required_combined_tolerance_budget_mm,
                "minimum_feature_tolerance_mm": self.minimum_feature_tolerance_mm,
                "clip_tolerance_interval_mm": [self.clip_tolerance_min_mm, self.clip_tolerance_max_mm],
                "groove_tolerance_interval_mm": [self.groove_tolerance_min_mm, self.groove_tolerance_max_mm],
                "allocation_span_mm": self.allocation_span_mm,
                "nominal_geometry_unchanged": self.nominal_geometry_unchanged,
                "process_capability_validated": self.process_capability_validated,
                "physical_validation_eligible": self.physical_validation_eligible,
                "evidence_sha256": self.evidence_sha256}


def build_structural_frame_retention_root_capture_v14() -> StructuralFrameRetentionRootCaptureV14:
    prior = capture_v13.build_structural_frame_retention_root_capture_v13().validate()
    budget = prior.candidate_clip_tolerance_mm + prior.candidate_groove_tolerance_mm
    floor = MIN_FEATURE_BILATERAL_TOLERANCE_MM
    upper = budget - floor
    values = tuple(round(v, 12) for v in (budget, floor, floor, upper, floor, upper, upper - floor))
    payload = {"source_capture_v13_sha256": prior.evidence_sha256, "values": values, "nominal_geometry_unchanged": True}
    digest = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    return StructuralFrameRetentionRootCaptureV14(prior.evidence_sha256, *values, digest).validate()
