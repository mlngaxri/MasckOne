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
from .structural_frame_actuator_reactions import build_structural_frame_actuator_reactions
from .structural_frame_realization import _protected_zone_solid
from .structural_frame_retention_roots import (
    StructuralFrameRetentionRootArchitecture,
    build_structural_frame_retention_roots,
)

SCHEMA = "MASCK_ONE_STRUCTURAL_FRAME_RETENTION_VERIFICATION_V2"
INTERSECTION_TOLERANCE_MM3 = 1e-7
EXPECTED_ROOT_IDS = frozenset({"RETENTION_ROOT_WEARER_LEFT", "RETENTION_ROOT_WEARER_RIGHT"})


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
    source_frame_capture_mm3: float
    yoke_material_intersection_mm3: float
    pin_yoke_material_intersection_mm3: float
    pin_bore_capture_mm3: float
    split_retainer_pin_intersection_mm3: float
    split_retainer_yoke_intersection_mm3: float
    frame_protected_intersection_mm3: float
    pin_protected_intersection_mm3: float
    split_retainer_protected_intersection_mm3: float

    def validate(self) -> "RetentionRootVerificationV2":
        if self.root_id not in EXPECTED_ROOT_IDS:
            raise StructuralFrameRetentionVerificationV2Error(
                f"unexpected retention root identity: {self.root_id!r}"
            )
        for value in (
            self.source_frame_capture_mm3,
            self.yoke_material_intersection_mm3,
            self.pin_yoke_material_intersection_mm3,
            self.pin_bore_capture_mm3,
            self.split_retainer_pin_intersection_mm3,
            self.split_retainer_yoke_intersection_mm3,
            self.frame_protected_intersection_mm3,
            self.pin_protected_intersection_mm3,
            self.split_retainer_protected_intersection_mm3,
        ):
            if not math.isfinite(value) or value < 0.0:
                raise StructuralFrameRetentionVerificationV2Error(
                    "root verification metrics must be finite and nonnegative"
                )
        if self.source_frame_capture_mm3 <= INTERSECTION_TOLERANCE_MM3:
            raise StructuralFrameRetentionVerificationV2Error(
                f"{self.root_id} frame counterpart has no positive source-frame capture"
            )
        if self.yoke_material_intersection_mm3 > INTERSECTION_TOLERANCE_MM3:
            raise StructuralFrameRetentionVerificationV2Error(
                f"{self.root_id} frame counterpart intersects yoke material"
            )
        if self.pin_yoke_material_intersection_mm3 > INTERSECTION_TOLERANCE_MM3:
            raise StructuralFrameRetentionVerificationV2Error(
                f"{self.root_id} capture pin intersects yoke material"
            )
        if self.pin_bore_capture_mm3 <= INTERSECTION_TOLERANCE_MM3:
            raise StructuralFrameRetentionVerificationV2Error(
                f"{self.root_id} capture pin does not positively traverse the yoke bore"
            )
        if self.split_retainer_pin_intersection_mm3 > INTERSECTION_TOLERANCE_MM3:
            raise StructuralFrameRetentionVerificationV2Error(
                f"{self.root_id} split retainer interferes with capture pin"
            )
        if self.split_retainer_yoke_intersection_mm3 > INTERSECTION_TOLERANCE_MM3:
            raise StructuralFrameRetentionVerificationV2Error(
                f"{self.root_id} split retainer intersects yoke material"
            )
        if self.frame_protected_intersection_mm3 > INTERSECTION_TOLERANCE_MM3:
            raise StructuralFrameRetentionVerificationV2Error(
                f"{self.root_id} frame counterpart intersects a protected volume"
            )
        if self.pin_protected_intersection_mm3 > INTERSECTION_TOLERANCE_MM3:
            raise StructuralFrameRetentionVerificationV2Error(
                f"{self.root_id} capture pin intersects a protected volume"
            )
        if self.split_retainer_protected_intersection_mm3 > INTERSECTION_TOLERANCE_MM3:
            raise StructuralFrameRetentionVerificationV2Error(
                f"{self.root_id} split retainer intersects a protected volume"
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
        root_ids = {root.root_id for root in self.roots}
        if root_ids != EXPECTED_ROOT_IDS:
            raise StructuralFrameRetentionVerificationV2Error(
                "fail-closed verification requires exactly one wearer-left and one wearer-right retention root"
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
            "verification_semantics": "FAIL_CLOSED_INDEPENDENT_BREP_COLLISION_SOURCE_CAPTURE_PIN_ASSEMBLY_AND_PROTECTED_ZONE_RECHECK",
            "roots": [
                {
                    "root_id": root.root_id,
                    "source_frame_capture_mm3": root.source_frame_capture_mm3,
                    "yoke_material_intersection_mm3": root.yoke_material_intersection_mm3,
                    "pin_yoke_material_intersection_mm3": root.pin_yoke_material_intersection_mm3,
                    "pin_bore_capture_mm3": root.pin_bore_capture_mm3,
                    "split_retainer_pin_intersection_mm3": root.split_retainer_pin_intersection_mm3,
                    "split_retainer_yoke_intersection_mm3": root.split_retainer_yoke_intersection_mm3,
                    "frame_protected_intersection_mm3": root.frame_protected_intersection_mm3,
                    "pin_protected_intersection_mm3": root.pin_protected_intersection_mm3,
                    "split_retainer_protected_intersection_mm3": root.split_retainer_protected_intersection_mm3,
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
    architecture_root_ids = {root.root_id for root in architecture.roots}
    if len(architecture.roots) != 2 or architecture_root_ids != EXPECTED_ROOT_IDS:
        raise StructuralFrameRetentionVerificationV2Error(
            "retention architecture must contain exactly one wearer-left and one wearer-right root"
        )

    source_reactions = build_structural_frame_actuator_reactions(model=model)
    if architecture.source_frame_reaction_architecture_sha256 != source_reactions.architecture_sha256:
        raise StructuralFrameRetentionVerificationV2Error(
            "retention roots do not identify the reconstructed source reaction frame"
        )
    source_frame = source_reactions.frame_with_reaction_counterparts

    frame_bb = architecture.frame_with_retention_roots.val().BoundingBox()
    z_min = min(root.center_xyz_mm[2] - 10.0 for root in architecture.roots)
    z_max = max(root.center_xyz_mm[2] + 10.0 for root in architecture.roots)
    z_min = min(z_min, float(frame_bb.zmin) - 2.0)
    z_max = max(z_max, float(frame_bb.zmax) + 2.0)

    protected_keepouts: list[cq.Workplane] = []
    for protected in model.protected_volumes.all:
        zone = protected.zone
        protected_keepouts.append(
            _protected_zone_solid(
                center_x_mm=zone.center.x,
                center_y_mm=zone.center.y,
                envelope_width_mm=zone.envelope_width_mm,
                envelope_height_mm=zone.envelope_height_mm,
                angle_deg=zone.angle_deg,
                z_min_mm=z_min,
                z_max_mm=z_max,
            )
        )

    results: list[RetentionRootVerificationV2] = []
    for root in architecture.roots:
        frame_protected_overlap = 0.0
        pin_protected_overlap = 0.0
        split_retainer_protected_overlap = 0.0
        for keepout in protected_keepouts:
            frame_protected_overlap += _strict_intersection_volume(root.frame_counterpart, keepout)
            pin_protected_overlap += _strict_intersection_volume(root.capture_pin, keepout)
            split_retainer_protected_overlap += _strict_intersection_volume(root.split_retainer, keepout)

        results.append(
            RetentionRootVerificationV2(
                root_id=root.root_id,
                source_frame_capture_mm3=_strict_intersection_volume(root.frame_counterpart, source_frame),
                yoke_material_intersection_mm3=_strict_intersection_volume(root.frame_counterpart, root.yoke_root_reference),
                pin_yoke_material_intersection_mm3=_strict_intersection_volume(root.capture_pin, root.yoke_root_reference),
                pin_bore_capture_mm3=_strict_intersection_volume(root.capture_pin, root.yoke_bore_reference),
                split_retainer_pin_intersection_mm3=_strict_intersection_volume(root.split_retainer, root.capture_pin),
                split_retainer_yoke_intersection_mm3=_strict_intersection_volume(root.split_retainer, root.yoke_root_reference),
                frame_protected_intersection_mm3=frame_protected_overlap,
                pin_protected_intersection_mm3=pin_protected_overlap,
                split_retainer_protected_intersection_mm3=split_retainer_protected_overlap,
            ).validate()
        )

    return StructuralFrameRetentionVerificationV2(tuple(results)).validate()
