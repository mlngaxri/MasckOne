from __future__ import annotations

"""Worst-case dimensional budget for the split-retainer throat.

V5 establishes nominal throat-to-bore connectivity. V6 converts the two nearest
geometric failure boundaries into explicit aggregate error budgets. It deliberately
does not allocate those budgets to a manufacturing process or claim capability.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
import math

from . import structural_frame_retention_root_capture_v5 as capture_v5
from .structural_frame_retention_root_capture_v2 import CLIP_THROAT_WIDTH_MM
from .structural_frame_retention_roots import ROOT_CAPTURE_PIN_RADIUS_MM

SCHEMA = "MASCK_ONE_STRUCTURAL_FRAME_RETENTION_ROOT_CAPTURE_V6"


class StructuralFrameRetentionRootCaptureV6Error(ValueError):
    pass


def _budget_metrics() -> tuple[float, float, float, float]:
    v5 = capture_v5.build_structural_frame_retention_root_capture_v5()
    transition_budget = v5.throat_to_bore_transition_margin_mm
    shaft_diameter = 2.0 * ROOT_CAPTURE_PIN_RADIUS_MM
    radial_capture_budget = shaft_diameter - CLIP_THROAT_WIDTH_MM
    governing_budget = min(transition_budget, radial_capture_budget)
    governing_fraction = governing_budget / CLIP_THROAT_WIDTH_MM
    values = (transition_budget, radial_capture_budget, governing_budget, governing_fraction)
    if not all(math.isfinite(v) and v > 0.0 for v in values):
        raise StructuralFrameRetentionRootCaptureV6Error("capture tolerance budgets must be finite and positive")
    return values


@dataclass(frozen=True, slots=True)
class StructuralFrameRetentionRootCaptureV6:
    source_capture_v5_sha256: str
    transition_combined_error_budget_mm: float
    radial_escape_combined_error_budget_mm: float
    governing_combined_error_budget_mm: float
    governing_budget_fraction_of_throat: float
    evidence_sha256: str
    manufacturing_tolerance_allocation_required: bool = True
    process_capability_validated: bool = False
    physical_validation_eligible: bool = False

    def validate(self) -> "StructuralFrameRetentionRootCaptureV6":
        v5 = capture_v5.build_structural_frame_retention_root_capture_v5()
        metrics = tuple(round(v, 12) for v in _budget_metrics())
        if self.source_capture_v5_sha256 != v5.evidence_sha256:
            raise StructuralFrameRetentionRootCaptureV6Error("source capture V5 evidence is stale")
        actual = (
            self.transition_combined_error_budget_mm,
            self.radial_escape_combined_error_budget_mm,
            self.governing_combined_error_budget_mm,
            self.governing_budget_fraction_of_throat,
        )
        if actual != metrics:
            raise StructuralFrameRetentionRootCaptureV6Error("capture tolerance-budget evidence is stale")
        if self.manufacturing_tolerance_allocation_required is not True:
            raise StructuralFrameRetentionRootCaptureV6Error("aggregate geometric budget cannot waive tolerance allocation")
        payload = {
            "source_capture_v5_sha256": self.source_capture_v5_sha256,
            "transition_combined_error_budget_mm": self.transition_combined_error_budget_mm,
            "radial_escape_combined_error_budget_mm": self.radial_escape_combined_error_budget_mm,
            "governing_combined_error_budget_mm": self.governing_combined_error_budget_mm,
            "governing_budget_fraction_of_throat": self.governing_budget_fraction_of_throat,
            "manufacturing_tolerance_allocation_required": self.manufacturing_tolerance_allocation_required,
        }
        digest = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        if self.evidence_sha256 != digest:
            raise StructuralFrameRetentionRootCaptureV6Error("capture V6 evidence digest is stale")
        if self.process_capability_validated is not False or self.physical_validation_eligible is not False:
            raise StructuralFrameRetentionRootCaptureV6Error("dimensional budget is not process capability or physical validation")
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        return {
            "schema": SCHEMA,
            "source_capture_v5_sha256": self.source_capture_v5_sha256,
            "transition_combined_error_budget_mm": self.transition_combined_error_budget_mm,
            "radial_escape_combined_error_budget_mm": self.radial_escape_combined_error_budget_mm,
            "governing_combined_error_budget_mm": self.governing_combined_error_budget_mm,
            "governing_budget_fraction_of_throat": self.governing_budget_fraction_of_throat,
            "budget_status": "AGGREGATE_BOUND_ONLY_TOLERANCE_ALLOCATION_REQUIRED",
            "manufacturing_tolerance_allocation_required": self.manufacturing_tolerance_allocation_required,
            "process_capability_validated": self.process_capability_validated,
            "physical_validation_eligible": self.physical_validation_eligible,
            "evidence_sha256": self.evidence_sha256,
        }


def build_structural_frame_retention_root_capture_v6() -> StructuralFrameRetentionRootCaptureV6:
    v5 = capture_v5.build_structural_frame_retention_root_capture_v5()
    metrics = tuple(round(v, 12) for v in _budget_metrics())
    payload = {
        "source_capture_v5_sha256": v5.evidence_sha256,
        "transition_combined_error_budget_mm": metrics[0],
        "radial_escape_combined_error_budget_mm": metrics[1],
        "governing_combined_error_budget_mm": metrics[2],
        "governing_budget_fraction_of_throat": metrics[3],
        "manufacturing_tolerance_allocation_required": True,
    }
    digest = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    return StructuralFrameRetentionRootCaptureV6(v5.evidence_sha256, *metrics, digest).validate()
