from __future__ import annotations

"""V15: prove every V14 axial tolerance allocation preserves both stack corners.

V14 bounds unequal per-feature allocations while conserving the recovered combined
bilateral tolerance budget. V15 closes the mechanical implication explicitly: for
this two-feature axial stack, both adverse clearance corners depend only on the sum
of the two bilateral tolerances. Therefore every allocation inside the V14 envelope
must preserve the V13 minimum-clearance and maximum-free-play results.
"""

from dataclasses import dataclass
from hashlib import sha256
import json
import math

from . import structural_frame_retention_root_capture_v2 as capture_v2
from . import structural_frame_retention_root_capture_v13 as capture_v13
from . import structural_frame_retention_root_capture_v14 as capture_v14
from .structural_frame_retention_roots import CLEVIS_PIN_GROOVE_WIDTH_MM

SCHEMA = "MASCK_ONE_STRUCTURAL_FRAME_RETENTION_ROOT_CAPTURE_V15"


class StructuralFrameRetentionRootCaptureV15Error(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class StructuralFrameRetentionRootCaptureV15:
    source_capture_v14_sha256: str
    nominal_axial_clearance_mm: float
    allocation_budget_mm: float
    clip_min_allocation_min_clearance_mm: float
    clip_min_allocation_max_free_play_mm: float
    clip_max_allocation_min_clearance_mm: float
    clip_max_allocation_max_free_play_mm: float
    allocation_corner_spread_mm: float
    evidence_sha256: str
    nominal_geometry_unchanged: bool = True
    process_capability_validated: bool = False
    physical_validation_eligible: bool = False

    def validate(self) -> "StructuralFrameRetentionRootCaptureV15":
        envelope = capture_v14.build_structural_frame_retention_root_capture_v14().validate()
        target = capture_v13.build_structural_frame_retention_root_capture_v13().validate()
        if self.source_capture_v14_sha256 != envelope.evidence_sha256:
            raise StructuralFrameRetentionRootCaptureV15Error("capture V15 is not bound to current V14 authority")

        nominal = CLEVIS_PIN_GROOVE_WIDTH_MM - capture_v2.CLIP_AXIAL_THICKNESS_MM
        budget = envelope.required_combined_tolerance_budget_mm
        allocations = (
            (envelope.clip_tolerance_min_mm, envelope.groove_tolerance_max_mm),
            (envelope.clip_tolerance_max_mm, envelope.groove_tolerance_min_mm),
        )
        corners = []
        for clip_tol, groove_tol in allocations:
            if round(clip_tol + groove_tol, 12) != round(budget, 12):
                raise StructuralFrameRetentionRootCaptureV15Error("V14 boundary allocation does not conserve axial budget")
            corners.extend((nominal - clip_tol - groove_tol, nominal + clip_tol + groove_tol))
        spread = max(corners) - min(corners)
        # Spread across all values includes the intentional clearance window. The
        # allocation-dependent spread compares like corners below.
        allocation_spread = max(abs(corners[0] - corners[2]), abs(corners[1] - corners[3]))
        expected = tuple(round(v, 12) for v in (nominal, budget, *corners, allocation_spread))
        actual = (
            self.nominal_axial_clearance_mm, self.allocation_budget_mm,
            self.clip_min_allocation_min_clearance_mm, self.clip_min_allocation_max_free_play_mm,
            self.clip_max_allocation_min_clearance_mm, self.clip_max_allocation_max_free_play_mm,
            self.allocation_corner_spread_mm,
        )
        if actual != expected or not all(math.isfinite(v) and v >= 0.0 for v in actual):
            raise StructuralFrameRetentionRootCaptureV15Error("axial allocation corner evidence is stale or invalid")
        if self.allocation_corner_spread_mm != 0.0:
            raise StructuralFrameRetentionRootCaptureV15Error("axial stack corners vary across conserved allocations")
        if self.clip_min_allocation_min_clearance_mm != target.candidate_minimum_axial_clearance_mm:
            raise StructuralFrameRetentionRootCaptureV15Error("unequal allocation lost V13 minimum-clearance authority")
        if self.clip_min_allocation_max_free_play_mm != target.candidate_maximum_axial_free_play_mm:
            raise StructuralFrameRetentionRootCaptureV15Error("unequal allocation lost V13 maximum-free-play authority")
        if self.nominal_geometry_unchanged is not True:
            raise StructuralFrameRetentionRootCaptureV15Error("V15 must not change nominal geometry")
        payload = {"source_capture_v14_sha256": self.source_capture_v14_sha256, "values": actual,
                   "nominal_geometry_unchanged": self.nominal_geometry_unchanged}
        digest = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        if self.evidence_sha256 != digest:
            raise StructuralFrameRetentionRootCaptureV15Error("capture V15 evidence digest is stale")
        if self.process_capability_validated is not False or self.physical_validation_eligible is not False:
            raise StructuralFrameRetentionRootCaptureV15Error("allocation invariance is not process capability or physical validation")
        return self


def build_structural_frame_retention_root_capture_v15() -> StructuralFrameRetentionRootCaptureV15:
    envelope = capture_v14.build_structural_frame_retention_root_capture_v14().validate()
    nominal = CLEVIS_PIN_GROOVE_WIDTH_MM - capture_v2.CLIP_AXIAL_THICKNESS_MM
    budget = envelope.required_combined_tolerance_budget_mm
    a = (envelope.clip_tolerance_min_mm, envelope.groove_tolerance_max_mm)
    b = (envelope.clip_tolerance_max_mm, envelope.groove_tolerance_min_mm)
    corners = (nominal - sum(a), nominal + sum(a), nominal - sum(b), nominal + sum(b))
    allocation_spread = max(abs(corners[0] - corners[2]), abs(corners[1] - corners[3]))
    values = tuple(round(v, 12) for v in (nominal, budget, *corners, allocation_spread))
    payload = {"source_capture_v14_sha256": envelope.evidence_sha256, "values": values,
               "nominal_geometry_unchanged": True}
    digest = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    return StructuralFrameRetentionRootCaptureV15(envelope.evidence_sha256, *values, digest).validate()
