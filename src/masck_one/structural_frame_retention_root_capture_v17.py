from __future__ import annotations

"""V17: independently enumerate the axial tolerance stack corners.

V16 uses the conserved bilateral tolerance budget to evaluate the two adverse axial
corners. V17 removes the algebraic shortcut from verification: it constructs all four
physical groove/retainer size combinations and proves that the extrema agree with V16.
This is drawing-level dimensional evidence only.
"""

from dataclasses import dataclass
import math

from . import structural_frame_retention_root_capture_v2 as capture_v2
from . import structural_frame_retention_root_capture_v16 as capture_v16
from .structural_frame_retention_roots import CLEVIS_PIN_GROOVE_WIDTH_MM

SCHEMA = "MASCK_ONE_STRUCTURAL_FRAME_RETENTION_ROOT_CAPTURE_V17"
_EPS_MM = 1e-12


class StructuralFrameRetentionRootCaptureV17Error(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class AxialCornerSweep:
    clip_tolerance_mm: float
    groove_tolerance_mm: float
    clearances_mm: tuple[float, float, float, float]
    minimum_clearance_mm: float
    maximum_free_play_mm: float


def enumerate_axial_tolerance_corners(
    clip_tolerance_mm: float,
    groove_tolerance_mm: float,
) -> AxialCornerSweep:
    """Enumerate groove minus retainer clearance at every bilateral size corner."""
    authority = capture_v16.evaluate_axial_tolerance_allocation(
        clip_tolerance_mm, groove_tolerance_mm
    )
    clip_nominal = capture_v2.CLIP_AXIAL_THICKNESS_MM
    groove_nominal = CLEVIS_PIN_GROOVE_WIDTH_MM

    clip_sizes = (clip_nominal - clip_tolerance_mm, clip_nominal + clip_tolerance_mm)
    groove_sizes = (groove_nominal - groove_tolerance_mm, groove_nominal + groove_tolerance_mm)
    corners = tuple(round(groove - clip, 12) for groove in groove_sizes for clip in clip_sizes)
    if len(corners) != 4 or not all(math.isfinite(v) for v in corners):
        raise StructuralFrameRetentionRootCaptureV17Error("axial corner sweep is incomplete or non-finite")

    minimum = min(corners)
    maximum = max(corners)
    if not math.isclose(minimum, authority.minimum_clearance_mm, rel_tol=0.0, abs_tol=_EPS_MM):
        raise StructuralFrameRetentionRootCaptureV17Error("enumerated minimum disagrees with V16 authority")
    if not math.isclose(maximum, authority.maximum_free_play_mm, rel_tol=0.0, abs_tol=_EPS_MM):
        raise StructuralFrameRetentionRootCaptureV17Error("enumerated maximum disagrees with V16 authority")
    if minimum <= 0.0:
        raise StructuralFrameRetentionRootCaptureV17Error("worst-case axial corner loses positive clearance")

    return AxialCornerSweep(
        round(float(clip_tolerance_mm), 12),
        round(float(groove_tolerance_mm), 12),
        corners,
        minimum,
        maximum,
    )
