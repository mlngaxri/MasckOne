from __future__ import annotations

"""Fail closed unless each capture pin has a seated proximal axial stop.

V12 proves local split-retainer packaging. V13 independently interrogates the actual
capture-pin and frame-counterpart B-reps to prove the headed end reaches the proximal
clevis face and retains radial material beyond the shaft. This remains digital geometry
evidence only and does not establish strength, wear, service force, or physical safety.
"""

from dataclasses import dataclass
import math

from .model import MasckOneModel, build_model
from .structural_frame_retention_roots import (
    CLEVIS_PIN_HEAD_THICKNESS_MM,
    CLEVIS_PIN_RADIUS_MM,
    StructuralFrameRetentionRootArchitecture,
    build_structural_frame_retention_roots,
)
from .structural_frame_retention_verification_v12 import (
    StructuralFrameRetentionVerificationV12,
    StructuralFrameRetentionVerificationV12Error,
    verify_structural_frame_retention_roots_v12,
)

SCHEMA = "MASCK_ONE_STRUCTURAL_FRAME_RETENTION_VERIFICATION_V13"
EXPECTED_ROOT_IDS = frozenset({"RETENTION_ROOT_WEARER_LEFT", "RETENTION_ROOT_WEARER_RIGHT"})
AXIAL_SEATING_NUMERICAL_TOLERANCE_MM = 1e-6
MIN_HEAD_RADIAL_STOP_MARGIN_MM = 0.20


class StructuralFrameRetentionVerificationV13Error(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class StructuralFrameRetentionVerificationV13:
    v12: StructuralFrameRetentionVerificationV12
    head_seating_gaps_mm: tuple[tuple[str, float], ...]
    head_radial_stop_margins_mm: tuple[tuple[str, float], ...]
    physical_validation_eligible: bool = False

    def validate(self) -> "StructuralFrameRetentionVerificationV13":
        try:
            self.v12.validate()
        except StructuralFrameRetentionVerificationV12Error as exc:
            raise StructuralFrameRetentionVerificationV13Error("V12 prerequisite verification failed") from exc
        gaps = dict(self.head_seating_gaps_mm)
        margins = dict(self.head_radial_stop_margins_mm)
        if len(gaps) != 2 or set(gaps) != EXPECTED_ROOT_IDS:
            raise StructuralFrameRetentionVerificationV13Error(
                "head seating gaps require exactly one wearer-left and one wearer-right root"
            )
        if len(margins) != 2 or set(margins) != EXPECTED_ROOT_IDS:
            raise StructuralFrameRetentionVerificationV13Error(
                "head stop margins require exactly one wearer-left and one wearer-right root"
            )
        for root_id in EXPECTED_ROOT_IDS:
            gap = gaps[root_id]
            margin = margins[root_id]
            if not math.isfinite(gap) or gap < 0.0:
                raise StructuralFrameRetentionVerificationV13Error(
                    f"{root_id} capture-pin head seating gap must be finite and nonnegative"
                )
            if gap > AXIAL_SEATING_NUMERICAL_TOLERANCE_MM:
                raise StructuralFrameRetentionVerificationV13Error(
                    f"{root_id} capture-pin head is not seated against the proximal clevis face"
                )
            if not math.isfinite(margin) or margin < MIN_HEAD_RADIAL_STOP_MARGIN_MM:
                raise StructuralFrameRetentionVerificationV13Error(
                    f"{root_id} capture-pin head lacks required radial axial-stop material"
                )
        if self.physical_validation_eligible is not False:
            raise StructuralFrameRetentionVerificationV13Error(
                "digital capture-pin head seating is not physical validation evidence"
            )
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        gaps = dict(self.head_seating_gaps_mm)
        margins = dict(self.head_radial_stop_margins_mm)
        return {
            "schema": SCHEMA,
            "verification_semantics": "FAIL_CLOSED_V12_PLUS_CAPTURE_PIN_PROXIMAL_AXIAL_STOP",
            "axial_seating_numerical_tolerance_mm": AXIAL_SEATING_NUMERICAL_TOLERANCE_MM,
            "minimum_head_radial_stop_margin_mm": MIN_HEAD_RADIAL_STOP_MARGIN_MM,
            "roots": [
                {
                    "root_id": root_id,
                    "head_seating_gap_mm": gaps[root_id],
                    "head_radial_stop_margin_mm": margins[root_id],
                }
                for root_id in sorted(EXPECTED_ROOT_IDS)
            ],
            "physical_validation_eligible": False,
        }


def verify_structural_frame_retention_roots_v13(
    *, model: MasckOneModel | None = None,
    architecture: StructuralFrameRetentionRootArchitecture | None = None,
) -> StructuralFrameRetentionVerificationV13:
    model = build_model() if model is None else model
    architecture = build_structural_frame_retention_roots(model=model) if architecture is None else architecture
    if type(model) is not MasckOneModel or type(architecture) is not StructuralFrameRetentionRootArchitecture:
        raise StructuralFrameRetentionVerificationV13Error("exact model and retention-root architecture types are required")
    if len(architecture.roots) != 2 or {root.root_id for root in architecture.roots} != EXPECTED_ROOT_IDS:
        raise StructuralFrameRetentionVerificationV13Error(
            "retention architecture must contain exactly one wearer-left and one wearer-right root"
        )

    gaps: list[tuple[str, float]] = []
    margins: list[tuple[str, float]] = []
    for root in architecture.roots:
        try:
            pin_bb = root.capture_pin.val().BoundingBox()
            frame_bb = root.frame_counterpart.val().BoundingBox()
            # The headed pin is inserted along +Y. Its proximal head occupies the first
            # HEAD_THICKNESS of the actual pin B-rep and should terminate at the outer
            # proximal clevis face.
            head_contact_y = float(pin_bb.ymin) + CLEVIS_PIN_HEAD_THICKNESS_MM
            seating_gap = abs(float(frame_bb.ymin) - head_contact_y)
            measured_head_radius_x = (float(pin_bb.xmax) - float(pin_bb.xmin)) / 2.0
            radial_stop_margin = measured_head_radius_x - CLEVIS_PIN_RADIUS_MM
        except Exception as exc:
            raise StructuralFrameRetentionVerificationV13Error(
                "capture-pin head axial-stop B-rep query failed"
            ) from exc
        gaps.append((root.root_id, seating_gap))
        margins.append((root.root_id, radial_stop_margin))

    v12 = verify_structural_frame_retention_roots_v12(model=model, architecture=architecture)
    return StructuralFrameRetentionVerificationV13(
        v12=v12,
        head_seating_gaps_mm=tuple(gaps),
        head_radial_stop_margins_mm=tuple(margins),
    ).validate()
