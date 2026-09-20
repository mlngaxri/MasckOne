from __future__ import annotations

"""Fail closed on split-retainer seating inside the capture-pin groove.

V10 proves axial registration. V11 independently reconstructs the groove-bottom
reference and verifies that each installed split retainer has the intended digital
radial seating clearance without volumetric interference with the actual capture pin.
This remains digital geometry evidence only.
"""

from dataclasses import dataclass
import math

import cadquery as cq

from .model import MasckOneModel, build_model
from .structural_frame_retention_roots import (
    CLEVIS_PIN_GROOVE_DEPTH_MM,
    CLEVIS_PIN_GROOVE_WIDTH_MM,
    CLEVIS_PIN_RADIUS_MM,
    StructuralFrameRetentionRootArchitecture,
    build_structural_frame_retention_roots,
)
from .structural_frame_retention_verification_v10 import (
    StructuralFrameRetentionVerificationV10,
    StructuralFrameRetentionVerificationV10Error,
    _authority_groove_center_y_mm,
    verify_structural_frame_retention_roots_v10,
)

SCHEMA = "MASCK_ONE_STRUCTURAL_FRAME_RETENTION_VERIFICATION_V11"
EXPECTED_ROOT_IDS = frozenset({"RETENTION_ROOT_WEARER_LEFT", "RETENTION_ROOT_WEARER_RIGHT"})
NOMINAL_CLIP_GROOVE_RADIAL_CLEARANCE_MM = 0.08
CLEARANCE_NUMERICAL_TOLERANCE_MM = 1e-6
INTERFERENCE_TOLERANCE_MM3 = 1e-7


class StructuralFrameRetentionVerificationV11Error(ValueError):
    pass


def _cylinder_y(radius: float, length: float, center: tuple[float, float, float]) -> cq.Workplane:
    x, y, z = center
    start = cq.Vector(x, y - length / 2.0, z)
    solid = cq.Solid.makeCylinder(radius, length, start, cq.Vector(0.0, 1.0, 0.0))
    return cq.Workplane("XY").newObject([solid])


@dataclass(frozen=True, slots=True)
class StructuralFrameRetentionVerificationV11:
    v10: StructuralFrameRetentionVerificationV10
    groove_bottom_clearances_mm: tuple[tuple[str, float], ...]
    retainer_pin_intersections_mm3: tuple[tuple[str, float], ...]
    physical_validation_eligible: bool = False

    def validate(self) -> "StructuralFrameRetentionVerificationV11":
        try:
            self.v10.validate()
        except StructuralFrameRetentionVerificationV10Error as exc:
            raise StructuralFrameRetentionVerificationV11Error("V10 prerequisite verification failed") from exc
        clearances = dict(self.groove_bottom_clearances_mm)
        intersections = dict(self.retainer_pin_intersections_mm3)
        if len(clearances) != 2 or set(clearances) != EXPECTED_ROOT_IDS:
            raise StructuralFrameRetentionVerificationV11Error("groove clearances require exactly one wearer-left and one wearer-right root")
        if len(intersections) != 2 or set(intersections) != EXPECTED_ROOT_IDS:
            raise StructuralFrameRetentionVerificationV11Error("pin intersections require exactly one wearer-left and one wearer-right root")
        for root_id in EXPECTED_ROOT_IDS:
            clearance = clearances[root_id]
            interference = intersections[root_id]
            if not math.isfinite(clearance) or clearance < 0.0:
                raise StructuralFrameRetentionVerificationV11Error(f"{root_id} groove-bottom clearance must be finite and nonnegative")
            if abs(clearance - NOMINAL_CLIP_GROOVE_RADIAL_CLEARANCE_MM) > CLEARANCE_NUMERICAL_TOLERANCE_MM:
                raise StructuralFrameRetentionVerificationV11Error(f"{root_id} split retainer does not preserve nominal groove seating clearance")
            if not math.isfinite(interference) or interference < 0.0:
                raise StructuralFrameRetentionVerificationV11Error(f"{root_id} retainer/pin intersection must be finite and nonnegative")
            if interference > INTERFERENCE_TOLERANCE_MM3:
                raise StructuralFrameRetentionVerificationV11Error(f"{root_id} split retainer volumetrically interferes with capture pin")
        if self.physical_validation_eligible is not False:
            raise StructuralFrameRetentionVerificationV11Error("digital groove seating is not physical validation evidence")
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        clearances = dict(self.groove_bottom_clearances_mm)
        intersections = dict(self.retainer_pin_intersections_mm3)
        return {
            "schema": SCHEMA,
            "verification_semantics": "FAIL_CLOSED_V10_PLUS_SPLIT_RETAINER_GROOVE_SEATING",
            "nominal_clip_groove_radial_clearance_mm": NOMINAL_CLIP_GROOVE_RADIAL_CLEARANCE_MM,
            "clearance_numerical_tolerance_mm": CLEARANCE_NUMERICAL_TOLERANCE_MM,
            "interference_tolerance_mm3": INTERFERENCE_TOLERANCE_MM3,
            "roots": [
                {
                    "root_id": root_id,
                    "groove_bottom_clearance_mm": clearances[root_id],
                    "retainer_pin_intersection_mm3": intersections[root_id],
                }
                for root_id in sorted(EXPECTED_ROOT_IDS)
            ],
            "physical_validation_eligible": False,
        }


def verify_structural_frame_retention_roots_v11(
    *, model: MasckOneModel | None = None,
    architecture: StructuralFrameRetentionRootArchitecture | None = None,
) -> StructuralFrameRetentionVerificationV11:
    model = build_model() if model is None else model
    architecture = build_structural_frame_retention_roots(model=model) if architecture is None else architecture
    if type(model) is not MasckOneModel or type(architecture) is not StructuralFrameRetentionRootArchitecture:
        raise StructuralFrameRetentionVerificationV11Error("exact model and retention-root architecture types are required")
    if len(architecture.roots) != 2 or {root.root_id for root in architecture.roots} != EXPECTED_ROOT_IDS:
        raise StructuralFrameRetentionVerificationV11Error("retention architecture must contain exactly one wearer-left and one wearer-right root")

    groove_radius = CLEVIS_PIN_RADIUS_MM - CLEVIS_PIN_GROOVE_DEPTH_MM
    groove_y = _authority_groove_center_y_mm()
    clearances: list[tuple[str, float]] = []
    intersections: list[tuple[str, float]] = []
    for root in architecture.roots:
        center_x, _, center_z = root.center_xyz_mm
        groove_bottom = _cylinder_y(
            groove_radius,
            CLEVIS_PIN_GROOVE_WIDTH_MM,
            (center_x, groove_y, center_z),
        )
        try:
            clearance = float(root.split_retainer.val().distance(groove_bottom.val()))
            interference = float(root.split_retainer.intersect(root.capture_pin).val().Volume())
        except Exception as exc:
            raise StructuralFrameRetentionVerificationV11Error("split-retainer B-rep seating query failed") from exc
        clearances.append((root.root_id, clearance))
        intersections.append((root.root_id, interference))

    v10 = verify_structural_frame_retention_roots_v10(model=model, architecture=architecture)
    return StructuralFrameRetentionVerificationV11(
        v10=v10,
        groove_bottom_clearances_mm=tuple(clearances),
        retainer_pin_intersections_mm3=tuple(intersections),
    ).validate()
