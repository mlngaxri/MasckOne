from __future__ import annotations

"""Fail closed unless installed capture pins retain their authoritative outer dimensions.

V13 proves proximal seating and a minimum radial stop. V14 closes the remaining coherent
geometry-drift gap by independently measuring each installed capture-pin B-rep and binding
its overall axial length and head radius to the structural-root authority constants. This
is digital geometry evidence only and does not establish strength, tolerance, or service life.
"""

from dataclasses import dataclass
import math

from .model import MasckOneModel, build_model
from .structural_frame_retention_roots import (
    CLEVIS_PIN_DISTAL_EXTENSION_MM,
    CLEVIS_PIN_HEAD_RADIUS_MM,
    CLEVIS_PIN_HEAD_THICKNESS_MM,
    CLEVIS_SIDE_CLEARANCE_MM,
    CLEVIS_EAR_Y_THICKNESS_MM,
    YOKE_ROOT_BOSS_XYZ_MM,
    StructuralFrameRetentionRootArchitecture,
    build_structural_frame_retention_roots,
)
from .structural_frame_retention_verification_v13 import (
    StructuralFrameRetentionVerificationV13,
    StructuralFrameRetentionVerificationV13Error,
    verify_structural_frame_retention_roots_v13,
)

SCHEMA = "MASCK_ONE_STRUCTURAL_FRAME_RETENTION_VERIFICATION_V14"
EXPECTED_ROOT_IDS = frozenset({"RETENTION_ROOT_WEARER_LEFT", "RETENTION_ROOT_WEARER_RIGHT"})
DIMENSIONAL_NUMERICAL_TOLERANCE_MM = 1e-6
EXPECTED_PIN_STACK_Y_MM = YOKE_ROOT_BOSS_XYZ_MM[1] + 2.0 * (
    CLEVIS_SIDE_CLEARANCE_MM + CLEVIS_EAR_Y_THICKNESS_MM
)
EXPECTED_PIN_OVERALL_LENGTH_MM = (
    EXPECTED_PIN_STACK_Y_MM + CLEVIS_PIN_HEAD_THICKNESS_MM + CLEVIS_PIN_DISTAL_EXTENSION_MM
)


class StructuralFrameRetentionVerificationV14Error(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class StructuralFrameRetentionVerificationV14:
    v13: StructuralFrameRetentionVerificationV13
    pin_overall_lengths_mm: tuple[tuple[str, float], ...]
    pin_head_radii_mm: tuple[tuple[str, float], ...]
    physical_validation_eligible: bool = False

    def validate(self) -> "StructuralFrameRetentionVerificationV14":
        try:
            self.v13.validate()
        except StructuralFrameRetentionVerificationV13Error as exc:
            raise StructuralFrameRetentionVerificationV14Error("V13 prerequisite verification failed") from exc
        lengths = dict(self.pin_overall_lengths_mm)
        radii = dict(self.pin_head_radii_mm)
        if len(lengths) != 2 or set(lengths) != EXPECTED_ROOT_IDS:
            raise StructuralFrameRetentionVerificationV14Error(
                "pin lengths require exactly one wearer-left and one wearer-right root"
            )
        if len(radii) != 2 or set(radii) != EXPECTED_ROOT_IDS:
            raise StructuralFrameRetentionVerificationV14Error(
                "pin head radii require exactly one wearer-left and one wearer-right root"
            )
        for root_id in EXPECTED_ROOT_IDS:
            length = lengths[root_id]
            radius = radii[root_id]
            if not math.isfinite(length) or abs(length - EXPECTED_PIN_OVERALL_LENGTH_MM) > DIMENSIONAL_NUMERICAL_TOLERANCE_MM:
                raise StructuralFrameRetentionVerificationV14Error(
                    f"{root_id} capture-pin overall length drifted from structural authority"
                )
            if not math.isfinite(radius) or abs(radius - CLEVIS_PIN_HEAD_RADIUS_MM) > DIMENSIONAL_NUMERICAL_TOLERANCE_MM:
                raise StructuralFrameRetentionVerificationV14Error(
                    f"{root_id} capture-pin head radius drifted from structural authority"
                )
        if self.physical_validation_eligible is not False:
            raise StructuralFrameRetentionVerificationV14Error(
                "digital capture-pin dimensional authority is not physical validation evidence"
            )
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        lengths = dict(self.pin_overall_lengths_mm)
        radii = dict(self.pin_head_radii_mm)
        return {
            "schema": SCHEMA,
            "verification_semantics": "FAIL_CLOSED_V13_PLUS_CAPTURE_PIN_DIMENSIONAL_AUTHORITY",
            "dimensional_numerical_tolerance_mm": DIMENSIONAL_NUMERICAL_TOLERANCE_MM,
            "expected_pin_overall_length_mm": EXPECTED_PIN_OVERALL_LENGTH_MM,
            "expected_pin_head_radius_mm": CLEVIS_PIN_HEAD_RADIUS_MM,
            "roots": [
                {
                    "root_id": root_id,
                    "pin_overall_length_mm": lengths[root_id],
                    "pin_head_radius_mm": radii[root_id],
                }
                for root_id in sorted(EXPECTED_ROOT_IDS)
            ],
            "physical_validation_eligible": False,
        }


def verify_structural_frame_retention_roots_v14(
    *, model: MasckOneModel | None = None,
    architecture: StructuralFrameRetentionRootArchitecture | None = None,
) -> StructuralFrameRetentionVerificationV14:
    model = build_model() if model is None else model
    architecture = build_structural_frame_retention_roots(model=model) if architecture is None else architecture
    if type(model) is not MasckOneModel or type(architecture) is not StructuralFrameRetentionRootArchitecture:
        raise StructuralFrameRetentionVerificationV14Error("exact model and retention-root architecture types are required")
    if len(architecture.roots) != 2 or {root.root_id for root in architecture.roots} != EXPECTED_ROOT_IDS:
        raise StructuralFrameRetentionVerificationV14Error(
            "retention architecture must contain exactly one wearer-left and one wearer-right root"
        )

    lengths: list[tuple[str, float]] = []
    radii: list[tuple[str, float]] = []
    for root in architecture.roots:
        try:
            bb = root.capture_pin.val().BoundingBox()
            length = float(bb.ymax) - float(bb.ymin)
            radius = (float(bb.xmax) - float(bb.xmin)) / 2.0
        except Exception as exc:
            raise StructuralFrameRetentionVerificationV14Error(
                "capture-pin dimensional B-rep query failed"
            ) from exc
        lengths.append((root.root_id, length))
        radii.append((root.root_id, radius))

    v13 = verify_structural_frame_retention_roots_v13(model=model, architecture=architecture)
    return StructuralFrameRetentionVerificationV14(
        v13=v13,
        pin_overall_lengths_mm=tuple(lengths),
        pin_head_radii_mm=tuple(radii),
    ).validate()
