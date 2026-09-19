from __future__ import annotations

"""Fail-closed verification for the bilateral structural retention roots.

The V1 root generator contains several Boolean intersection checks. This verifier
independently re-runs the safety-relevant checks without converting CAD-kernel errors
into zero overlap. A failed Boolean therefore blocks evidence instead of being
indistinguishable from valid clearance.
"""

from dataclasses import dataclass
import math

import cadquery as cq

from .model import MasckOneModel, build_model
from .structural_frame_realization import _protected_zone_solid
from .structural_frame_retention_roots import (
    StructuralFrameRetentionRootArchitecture,
    build_structural_frame_retention_roots,
)

SCHEMA = "MASCK_ONE_STRUCTURAL_FRAME_RETENTION_VERIFICATION_V2"
INTERSECTION_TOLERANCE_MM3 = 1e-7


class StructuralFrameRetentionVerificationV2Error(ValueError):
    pass


def _strict_intersection_volume(a: cq.Workplane, b: cq.Workplane) -> float:
    try:
        result = a.intersect(b)
        value = result.val()
        volume = float(value.Volume())
    except Exception as exc:
        raise StructuralFrameRetentionVerificationV2Error(
            "B-rep intersection query failed closed"
        ) from exc
    if not value.isValid() or not math.isfinite(volume) or volume < 0.0:
        raise StructuralFrameRetentionVerificationV2Error(
            "B-rep intersection result must be valid, finite and nonnegative"
        )
    return 0.0 if volume <= INTERSECTION_TOLERANCE_MM3 else volume


@dataclass(frozen=True, slots=True)
class RetentionRootVerificationV2:
    root_id: str
    yoke_material_intersection_mm3: float
    pin_yoke_material_intersection_mm3: float
    protected_intersection_mm3: float

    def validate(self) -> "RetentionRootVerificationV2":
        for value in (
            self.yoke_material_intersection_mm3,
            self.pin_yoke_material_intersection_mm3,
            self.protected_intersection_mm3,
        ):
            if not math.isfinite(value) or value < 0.0:
                raise StructuralFrameRetentionVerificationV2Error(
                    "root verification metrics must be finite and nonnegative"
                )
        if self.yoke_material_intersection_mm3 > INTERSECTION_TOLERANCE_MM3:
            raise StructuralFrameRetentionVerificationV2Error(
                f"{self.root_id} frame counterpart intersects yoke material"
            )
        if self.pin_yoke_material_intersection_mm3 > INTERSECTION_TOLERANCE_MM3:
            raise StructuralFrameRetentionVerificationV2Error(
                f"{self.root_id} capture pin intersects yoke material"
            )
        if self.protected_intersection_mm3 > INTERSECTION_TOLERANCE_MM3:
            raise StructuralFrameRetentionVerificationV2Error(
                f"{self.root_id} frame counterpart intersects a protected volume"
            )
        return self


@dataclass(frozen=True, slots=True)
class StructuralFrameRetentionVerificationV2:
    roots: tuple[RetentionRootVerificationV2, ...]
    physical_validation_eligible: bool = False

    def validate(self) -> "StructuralFrameRetentionVerificationV2":
        if len(self.roots) != 2:
            raise StructuralFrameRetentionVerificationV2Error(
                "fail-closed verification requires both retention roots"
            )
        for root in self.roots:
            root.validate()
        if self.physical_validation_eligible is not False:
            raise StructuralFrameRetentionVerificationV2Error(
                "digital collision verification is not physical validation evidence"
            )
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        return {
            "schema": SCHEMA,
            "verification_semantics": "FAIL_CLOSED_INDEPENDENT_BREP_COLLISION_RECHECK",
            "roots": [
                {
                    "root_id": root.root_id,
                    "yoke_material_intersection_mm3": root.yoke_material_intersection_mm3,
                    "pin_yoke_material_intersection_mm3": root.pin_yoke_material_intersection_mm3,
                    "protected_intersection_mm3": root.protected_intersection_mm3,
                }
                for root in self.roots
            ],
            "physical_validation_eligible": False,
        }


def verify_structural_frame_retention_roots_v2(
    *,
    model: MasckOneModel | None = None,
    architecture: StructuralFrameRetentionRootArchitecture | None = None,
) -> StructuralFrameRetentionVerificationV2:
    model = build_model() if model is None else model
    architecture = (
        build_structural_frame_retention_roots(model=model)
        if architecture is None
        else architecture
    )
    if type(model) is not MasckOneModel or type(architecture) is not StructuralFrameRetentionRootArchitecture:
        raise StructuralFrameRetentionVerificationV2Error(
            "exact model and retention-root architecture types are required"
        )

    frame_bb = architecture.frame_with_retention_roots.val().BoundingBox()
    z_min = min(root.center_xyz_mm[2] - 10.0 for root in architecture.roots)
    z_max = max(root.center_xyz_mm[2] + 10.0 for root in architecture.roots)
    z_min = min(z_min, float(frame_bb.zmin) - 2.0)
    z_max = max(z_max, float(frame_bb.zmax) + 2.0)

    results: list[RetentionRootVerificationV2] = []
    for root in architecture.roots:
        protected_overlap = 0.0
        for protected in model.protected_volumes.all:
            zone = protected.zone
            keepout = _protected_zone_solid(
                center_x_mm=zone.center.x,
                center_y_mm=zone.center.y,
                envelope_width_mm=zone.envelope_width_mm,
                envelope_height_mm=zone.envelope_height_mm,
                angle_deg=zone.angle_deg,
                z_min_mm=z_min,
                z_max_mm=z_max,
            )
            protected_overlap += _strict_intersection_volume(root.frame_counterpart, keepout)

        results.append(
            RetentionRootVerificationV2(
                root_id=root.root_id,
                yoke_material_intersection_mm3=_strict_intersection_volume(
                    root.frame_counterpart, root.yoke_root_reference
                ),
                pin_yoke_material_intersection_mm3=_strict_intersection_volume(
                    root.capture_pin, root.yoke_root_reference
                ),
                protected_intersection_mm3=protected_overlap,
            ).validate()
        )

    return StructuralFrameRetentionVerificationV2(tuple(results)).validate()
