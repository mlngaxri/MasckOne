from __future__ import annotations

"""V16: executable gate for arbitrary axial tolerance allocations.

V14 defines the feasible per-feature allocation envelope and V15 proves its boundary
allocations preserve the V13 axial stack. This module turns that evidence into a
reusable fail-closed check for a proposed retainer/groove drawing allocation without
changing nominal geometry or claiming process capability.
"""

from dataclasses import dataclass
import math

from . import structural_frame_retention_root_capture_v2 as capture_v2
from . import structural_frame_retention_root_capture_v13 as capture_v13
from . import structural_frame_retention_root_capture_v14 as capture_v14
from .structural_frame_retention_roots import CLEVIS_PIN_GROOVE_WIDTH_MM

SCHEMA = "MASCK_ONE_STRUCTURAL_FRAME_RETENTION_ROOT_CAPTURE_V16"
_EPS_MM = 1e-12


class StructuralFrameRetentionRootCaptureV16Error(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class AxialToleranceAllocation:
    clip_tolerance_mm: float
    groove_tolerance_mm: float
    minimum_clearance_mm: float
    maximum_free_play_mm: float


def evaluate_axial_tolerance_allocation(
    clip_tolerance_mm: float,
    groove_tolerance_mm: float,
) -> AxialToleranceAllocation:
    """Validate one bilateral tolerance allocation against current V13/V14 authority."""
    envelope = capture_v14.build_structural_frame_retention_root_capture_v14().validate()
    target = capture_v13.build_structural_frame_retention_root_capture_v13().validate()

    values = (clip_tolerance_mm, groove_tolerance_mm)
    if not all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in values):
        raise StructuralFrameRetentionRootCaptureV16Error("axial tolerances must be finite real numbers")
    if not envelope.clip_tolerance_min_mm - _EPS_MM <= clip_tolerance_mm <= envelope.clip_tolerance_max_mm + _EPS_MM:
        raise StructuralFrameRetentionRootCaptureV16Error("clip tolerance is outside the V14 feasible envelope")
    if not envelope.groove_tolerance_min_mm - _EPS_MM <= groove_tolerance_mm <= envelope.groove_tolerance_max_mm + _EPS_MM:
        raise StructuralFrameRetentionRootCaptureV16Error("groove tolerance is outside the V14 feasible envelope")

    budget = clip_tolerance_mm + groove_tolerance_mm
    if not math.isclose(budget, envelope.required_combined_tolerance_budget_mm, rel_tol=0.0, abs_tol=_EPS_MM):
        raise StructuralFrameRetentionRootCaptureV16Error("allocation does not conserve the V14 axial tolerance budget")

    nominal = CLEVIS_PIN_GROOVE_WIDTH_MM - capture_v2.CLIP_AXIAL_THICKNESS_MM
    minimum = nominal - budget
    maximum = nominal + budget
    if minimum + _EPS_MM < target.candidate_minimum_axial_clearance_mm:
        raise StructuralFrameRetentionRootCaptureV16Error("allocation loses V13 minimum-clearance authority")
    if maximum - _EPS_MM > target.candidate_maximum_axial_free_play_mm:
        raise StructuralFrameRetentionRootCaptureV16Error("allocation loses V13 maximum-free-play authority")

    return AxialToleranceAllocation(
        round(float(clip_tolerance_mm), 12),
        round(float(groove_tolerance_mm), 12),
        round(minimum, 12),
        round(maximum, 12),
    )
