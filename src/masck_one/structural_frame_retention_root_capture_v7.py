from __future__ import annotations

"""Conservative dimensional allocation for the split-retainer capture geometry.

V6 establishes aggregate geometric failure budgets. V7 converts those bounds into
an explicit design allocation with 2x geometric reserve. This is a drawing-level
tolerance target only; it is not evidence that any manufacturing process can hold it.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
import math

from . import structural_frame_retention_root_capture_v6 as capture_v6

SCHEMA = "MASCK_ONE_STRUCTURAL_FRAME_RETENTION_ROOT_CAPTURE_V7"
GEOMETRIC_RESERVE_FACTOR = 2.0


class StructuralFrameRetentionRootCaptureV7Error(ValueError):
    pass


def _allocation_metrics() -> tuple[float, float, float, float, float]:
    v6 = capture_v6.build_structural_frame_retention_root_capture_v6()
    # Transition failure is driven by throat width low and clip bore diameter high.
    # Equal full-diameter tolerances contribute half their value to the radial margin.
    equal_feature_tolerance = v6.transition_combined_error_budget_mm / GEOMETRIC_RESERVE_FACTOR
    transition_consumed = equal_feature_tolerance
    transition_reserve = v6.transition_combined_error_budget_mm - transition_consumed

    # Radial escape is driven by throat width high and pin diameter low. The same
    # equal feature allocation consumes the two full-diameter errors directly.
    radial_escape_consumed = 2.0 * equal_feature_tolerance
    radial_escape_reserve = v6.radial_escape_combined_error_budget_mm - radial_escape_consumed
    values = (
        equal_feature_tolerance,
        transition_consumed,
        transition_reserve,
        radial_escape_consumed,
        radial_escape_reserve,
    )
    if not all(math.isfinite(v) and v > 0.0 for v in values):
        raise StructuralFrameRetentionRootCaptureV7Error("capture tolerance allocation must retain positive reserve")
    return values


@dataclass(frozen=True, slots=True)
class StructuralFrameRetentionRootCaptureV7:
    source_capture_v6_sha256: str
    throat_width_bilateral_tolerance_mm: float
    clip_bore_diameter_bilateral_tolerance_mm: float
    pin_diameter_bilateral_tolerance_mm: float
    transition_budget_consumed_mm: float
    transition_budget_reserve_mm: float
    radial_escape_budget_consumed_mm: float
    radial_escape_budget_reserve_mm: float
    geometric_reserve_factor: float
    evidence_sha256: str
    drawing_tolerance_allocation_defined: bool = True
    process_capability_validated: bool = False
    physical_validation_eligible: bool = False

    def validate(self) -> "StructuralFrameRetentionRootCaptureV7":
        v6 = capture_v6.build_structural_frame_retention_root_capture_v6()
        metrics = tuple(round(v, 12) for v in _allocation_metrics())
        if self.source_capture_v6_sha256 != v6.evidence_sha256:
            raise StructuralFrameRetentionRootCaptureV7Error("source capture V6 evidence is stale")
        actual = (
            self.throat_width_bilateral_tolerance_mm,
            self.clip_bore_diameter_bilateral_tolerance_mm,
            self.pin_diameter_bilateral_tolerance_mm,
            self.transition_budget_consumed_mm,
            self.transition_budget_reserve_mm,
            self.radial_escape_budget_consumed_mm,
            self.radial_escape_budget_reserve_mm,
            self.geometric_reserve_factor,
        )
        expected = (metrics[0], metrics[0], metrics[0], metrics[1], metrics[2], metrics[3], metrics[4], GEOMETRIC_RESERVE_FACTOR)
        if actual != expected:
            raise StructuralFrameRetentionRootCaptureV7Error("capture tolerance allocation evidence is stale")
        if self.drawing_tolerance_allocation_defined is not True:
            raise StructuralFrameRetentionRootCaptureV7Error("capture geometry requires explicit drawing tolerance allocation")
        payload = {
            "source_capture_v6_sha256": self.source_capture_v6_sha256,
            "throat_width_bilateral_tolerance_mm": self.throat_width_bilateral_tolerance_mm,
            "clip_bore_diameter_bilateral_tolerance_mm": self.clip_bore_diameter_bilateral_tolerance_mm,
            "pin_diameter_bilateral_tolerance_mm": self.pin_diameter_bilateral_tolerance_mm,
            "transition_budget_consumed_mm": self.transition_budget_consumed_mm,
            "transition_budget_reserve_mm": self.transition_budget_reserve_mm,
            "radial_escape_budget_consumed_mm": self.radial_escape_budget_consumed_mm,
            "radial_escape_budget_reserve_mm": self.radial_escape_budget_reserve_mm,
            "geometric_reserve_factor": self.geometric_reserve_factor,
            "drawing_tolerance_allocation_defined": self.drawing_tolerance_allocation_defined,
        }
        digest = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        if self.evidence_sha256 != digest:
            raise StructuralFrameRetentionRootCaptureV7Error("capture V7 evidence digest is stale")
        if self.process_capability_validated is not False or self.physical_validation_eligible is not False:
            raise StructuralFrameRetentionRootCaptureV7Error("drawing tolerance allocation is not process capability or physical validation")
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        return {
            "schema": SCHEMA,
            "source_capture_v6_sha256": self.source_capture_v6_sha256,
            "throat_width_bilateral_tolerance_mm": self.throat_width_bilateral_tolerance_mm,
            "clip_bore_diameter_bilateral_tolerance_mm": self.clip_bore_diameter_bilateral_tolerance_mm,
            "pin_diameter_bilateral_tolerance_mm": self.pin_diameter_bilateral_tolerance_mm,
            "transition_budget_reserve_mm": self.transition_budget_reserve_mm,
            "radial_escape_budget_reserve_mm": self.radial_escape_budget_reserve_mm,
            "geometric_reserve_factor": self.geometric_reserve_factor,
            "allocation_status": "DRAWING_TARGET_WITH_GEOMETRIC_RESERVE_PROCESS_CAPABILITY_REQUIRED",
            "process_capability_validated": self.process_capability_validated,
            "physical_validation_eligible": self.physical_validation_eligible,
            "evidence_sha256": self.evidence_sha256,
        }


def build_structural_frame_retention_root_capture_v7() -> StructuralFrameRetentionRootCaptureV7:
    v6 = capture_v6.build_structural_frame_retention_root_capture_v6()
    m = tuple(round(v, 12) for v in _allocation_metrics())
    payload = {
        "source_capture_v6_sha256": v6.evidence_sha256,
        "throat_width_bilateral_tolerance_mm": m[0],
        "clip_bore_diameter_bilateral_tolerance_mm": m[0],
        "pin_diameter_bilateral_tolerance_mm": m[0],
        "transition_budget_consumed_mm": m[1],
        "transition_budget_reserve_mm": m[2],
        "radial_escape_budget_consumed_mm": m[3],
        "radial_escape_budget_reserve_mm": m[4],
        "geometric_reserve_factor": GEOMETRIC_RESERVE_FACTOR,
        "drawing_tolerance_allocation_defined": True,
    }
    digest = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    return StructuralFrameRetentionRootCaptureV7(
        v6.evidence_sha256, m[0], m[0], m[0], m[1], m[2], m[3], m[4], GEOMETRIC_RESERVE_FACTOR, digest
    ).validate()
