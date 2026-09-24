from __future__ import annotations

"""Fail closed on split-retainer registration to the authoritative pin groove.

V9 bounds retainer width and radial withdrawal block. V10 additionally proves that the
installed retainer is axially registered over the groove center. Without this check an
offset but correctly sized retainer could satisfy V9 while providing no real capture.
This remains digital geometry evidence only.
"""

from dataclasses import dataclass
import math

from .model import MasckOneModel, build_model
from .structural_frame_retention_roots import (
    CLEVIS_EAR_Y_THICKNESS_MM,
    CLEVIS_PIN_DISTAL_EXTENSION_MM,
    CLEVIS_PIN_GROOVE_WIDTH_MM,
    CLEVIS_SIDE_CLEARANCE_MM,
    ROOT_Y_MM,
    YOKE_ROOT_BOSS_XYZ_MM,
    StructuralFrameRetentionRootArchitecture,
    build_structural_frame_retention_roots,
)
from .structural_frame_retention_verification_v9 import (
    StructuralFrameRetentionVerificationV9,
    StructuralFrameRetentionVerificationV9Error,
    verify_structural_frame_retention_roots_v9,
)

SCHEMA = "MASCK_ONE_STRUCTURAL_FRAME_RETENTION_VERIFICATION_V10"
EXPECTED_ROOT_IDS = frozenset({"RETENTION_ROOT_WEARER_LEFT", "RETENTION_ROOT_WEARER_RIGHT"})
AXIAL_REGISTRATION_TOLERANCE_MM = 1e-6


class StructuralFrameRetentionVerificationV10Error(ValueError):
    pass


def _authority_groove_center_y_mm() -> float:
    pin_stack_y = YOKE_ROOT_BOSS_XYZ_MM[1] + 2.0 * (
        CLEVIS_SIDE_CLEARANCE_MM + CLEVIS_EAR_Y_THICKNESS_MM
    )
    distal_y = ROOT_Y_MM + pin_stack_y / 2.0 + CLEVIS_PIN_DISTAL_EXTENSION_MM / 2.0
    return distal_y - CLEVIS_PIN_GROOVE_WIDTH_MM / 2.0


@dataclass(frozen=True, slots=True)
class StructuralFrameRetentionVerificationV10:
    v9: StructuralFrameRetentionVerificationV9
    retainer_center_y_mm: tuple[tuple[str, float], ...]
    physical_validation_eligible: bool = False

    def validate(self) -> "StructuralFrameRetentionVerificationV10":
        try:
            self.v9.validate()
        except StructuralFrameRetentionVerificationV9Error as exc:
            raise StructuralFrameRetentionVerificationV10Error("V9 prerequisite verification failed") from exc
        centers = dict(self.retainer_center_y_mm)
        if len(centers) != 2 or set(centers) != EXPECTED_ROOT_IDS:
            raise StructuralFrameRetentionVerificationV10Error(
                "retainer centers require exactly one wearer-left and one wearer-right root"
            )
        authority = _authority_groove_center_y_mm()
        for root_id in EXPECTED_ROOT_IDS:
            center = centers[root_id]
            if not math.isfinite(center):
                raise StructuralFrameRetentionVerificationV10Error(
                    f"{root_id} retainer axial center must be finite"
                )
            if abs(center - authority) > AXIAL_REGISTRATION_TOLERANCE_MM:
                raise StructuralFrameRetentionVerificationV10Error(
                    f"{root_id} split retainer is not registered to the authoritative pin groove"
                )
        if self.physical_validation_eligible is not False:
            raise StructuralFrameRetentionVerificationV10Error(
                "digital retainer registration is not physical validation evidence"
            )
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        centers = dict(self.retainer_center_y_mm)
        authority = _authority_groove_center_y_mm()
        return {
            "schema": SCHEMA,
            "verification_semantics": "FAIL_CLOSED_V9_PLUS_SPLIT_RETAINER_AXIAL_REGISTRATION",
            "authority_groove_center_y_mm": authority,
            "axial_registration_tolerance_mm": AXIAL_REGISTRATION_TOLERANCE_MM,
            "roots": [
                {
                    "root_id": root_id,
                    "retainer_center_y_mm": centers[root_id],
                    "axial_registration_error_mm": abs(centers[root_id] - authority),
                }
                for root_id in sorted(EXPECTED_ROOT_IDS)
            ],
            "physical_validation_eligible": False,
        }


def verify_structural_frame_retention_roots_v10(
    *,
    model: MasckOneModel | None = None,
    architecture: StructuralFrameRetentionRootArchitecture | None = None,
) -> StructuralFrameRetentionVerificationV10:
    model = build_model() if model is None else model
    architecture = (
        build_structural_frame_retention_roots(model=model)
        if architecture is None
        else architecture
    )
    if type(model) is not MasckOneModel or type(architecture) is not StructuralFrameRetentionRootArchitecture:
        raise StructuralFrameRetentionVerificationV10Error(
            "exact model and retention-root architecture types are required"
        )
    if len(architecture.roots) != 2 or {root.root_id for root in architecture.roots} != EXPECTED_ROOT_IDS:
        raise StructuralFrameRetentionVerificationV10Error(
            "retention architecture must contain exactly one wearer-left and one wearer-right root"
        )
    centers: list[tuple[str, float]] = []
    for root in architecture.roots:
        bb = root.split_retainer.val().BoundingBox()
        centers.append((root.root_id, (float(bb.ymin) + float(bb.ymax)) / 2.0))
    v9 = verify_structural_frame_retention_roots_v9(model=model, architecture=architecture)
    return StructuralFrameRetentionVerificationV10(
        v9=v9,
        retainer_center_y_mm=tuple(centers),
    ).validate()
