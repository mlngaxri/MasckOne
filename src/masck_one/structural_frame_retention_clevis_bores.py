from __future__ import annotations

"""Realize the missing frame-side capture-pin bores at both retention roots.

The retention-root generator establishes a positive clevis load path and a transverse
capture pin, but its frame counterpart is still solid through the pin axis. This layer
cuts an authority-bound running bore through each frame clevis and verifies that the
installed pin no longer occupies frame material while positive frame capture remains.
Digital geometry only; this is not manufacturing, strength, wear, or service evidence.
"""

from dataclasses import dataclass, field
import math

import cadquery as cq

from .model import MasckOneModel, build_model
from .structural_frame_retention_roots import (
    ROOT_IDS,
    ROOT_Y_MM,
    ROOT_Z_MM,
    YOKE_ROOT_BORE_RADIUS_MM,
    StructuralFrameRetentionRootArchitecture,
    build_structural_frame_retention_roots,
)

SCHEMA = "MASCK_ONE_STRUCTURAL_FRAME_RETENTION_CLEVIS_BORES_V1"
CLEVIS_BORE_RADIUS_MM = YOKE_ROOT_BORE_RADIUS_MM
CLEVIS_BORE_LENGTH_MM = 24.0
INTERSECTION_TOLERANCE_MM3 = 1e-7


class StructuralFrameRetentionClevisBoreError(ValueError):
    pass


def _single(shape: cq.Workplane, label: str) -> cq.Workplane:
    value = shape.val()
    if not value.isValid() or len(value.Solids()) != 1 or float(value.Volume()) <= 0.0:
        raise StructuralFrameRetentionClevisBoreError(f"{label} must be one valid positive-volume solid")
    return shape


def _cylinder_y(radius: float, length: float, center: tuple[float, float, float]) -> cq.Workplane:
    x, y, z = center
    start = cq.Vector(x, y - length / 2.0, z)
    solid = cq.Solid.makeCylinder(radius, length, start, cq.Vector(0.0, 1.0, 0.0))
    return cq.Workplane("XY").newObject([solid])


def _intersection_mm3(a: cq.Workplane, b: cq.Workplane) -> float:
    try:
        value = float(a.intersect(b).val().Volume())
    except Exception as exc:
        raise StructuralFrameRetentionClevisBoreError("B-rep intersection query failed") from exc
    if not math.isfinite(value) or value < 0.0:
        raise StructuralFrameRetentionClevisBoreError("intersection volume must be finite and nonnegative")
    return 0.0 if value <= INTERSECTION_TOLERANCE_MM3 else value


@dataclass(frozen=True, slots=True)
class RetentionClevisBore:
    root_id: str
    bore_radius_mm: float
    pre_cut_pin_frame_intersection_mm3: float
    post_cut_pin_frame_intersection_mm3: float
    post_cut_frame_capture_volume_mm3: float
    corrected_frame_counterpart: cq.Workplane = field(repr=False, compare=False)
    bore_reference: cq.Workplane = field(repr=False, compare=False)

    def validate(self) -> "RetentionClevisBore":
        if self.root_id not in ROOT_IDS:
            raise StructuralFrameRetentionClevisBoreError("unknown retention root")
        if not math.isclose(self.bore_radius_mm, CLEVIS_BORE_RADIUS_MM, abs_tol=1e-12):
            raise StructuralFrameRetentionClevisBoreError("clevis bore radius drifted from mating yoke bore authority")
        if self.pre_cut_pin_frame_intersection_mm3 <= INTERSECTION_TOLERANCE_MM3:
            raise StructuralFrameRetentionClevisBoreError("expected legacy solid-clevis pin interference is absent")
        if self.post_cut_pin_frame_intersection_mm3 > INTERSECTION_TOLERANCE_MM3:
            raise StructuralFrameRetentionClevisBoreError("capture pin still intersects corrected frame clevis")
        if self.post_cut_frame_capture_volume_mm3 <= INTERSECTION_TOLERANCE_MM3:
            raise StructuralFrameRetentionClevisBoreError("clevis bore cut destroyed positive frame attachment")
        _single(self.corrected_frame_counterpart, "corrected frame counterpart")
        _single(self.bore_reference, "clevis bore reference")
        return self


@dataclass(frozen=True, slots=True)
class StructuralFrameRetentionClevisBoreArchitecture:
    source_retention_architecture_sha256: str
    roots: tuple[RetentionClevisBore, ...]
    frame_with_clevis_bores: cq.Workplane = field(repr=False, compare=False)
    physical_validation_eligible: bool = False

    def validate(self) -> "StructuralFrameRetentionClevisBoreArchitecture":
        if len(self.source_retention_architecture_sha256) != 64:
            raise StructuralFrameRetentionClevisBoreError("source retention architecture digest is invalid")
        if tuple(root.root_id for root in self.roots) != ROOT_IDS:
            raise StructuralFrameRetentionClevisBoreError("both bilateral clevis bores are required in controlled order")
        for root in self.roots:
            root.validate()
        _single(self.frame_with_clevis_bores, "frame with bilateral clevis bores")
        if self.physical_validation_eligible is not False:
            raise StructuralFrameRetentionClevisBoreError("digital clevis-bore geometry is not physical validation evidence")
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        return {
            "schema": SCHEMA,
            "source_retention_architecture_sha256": self.source_retention_architecture_sha256,
            "bore_radius_mm": CLEVIS_BORE_RADIUS_MM,
            "bore_length_mm": CLEVIS_BORE_LENGTH_MM,
            "roots": [
                {
                    "root_id": root.root_id,
                    "pre_cut_pin_frame_intersection_mm3": root.pre_cut_pin_frame_intersection_mm3,
                    "post_cut_pin_frame_intersection_mm3": root.post_cut_pin_frame_intersection_mm3,
                    "post_cut_frame_capture_volume_mm3": root.post_cut_frame_capture_volume_mm3,
                }
                for root in self.roots
            ],
            "physical_validation_eligible": False,
        }


def build_structural_frame_retention_clevis_bores(
    *,
    model: MasckOneModel | None = None,
    architecture: StructuralFrameRetentionRootArchitecture | None = None,
) -> StructuralFrameRetentionClevisBoreArchitecture:
    model = build_model() if model is None else model
    architecture = build_structural_frame_retention_roots(model=model) if architecture is None else architecture
    if type(model) is not MasckOneModel or type(architecture) is not StructuralFrameRetentionRootArchitecture:
        raise StructuralFrameRetentionClevisBoreError("exact model and retention-root architecture types are required")

    corrected_frame = architecture.frame_with_retention_roots
    corrected_roots: list[RetentionClevisBore] = []
    for root in architecture.roots:
        x, _, _ = root.center_xyz_mm
        bore = _single(
            _cylinder_y(CLEVIS_BORE_RADIUS_MM, CLEVIS_BORE_LENGTH_MM, (x, ROOT_Y_MM, ROOT_Z_MM)),
            f"{root.root_id} clevis bore",
        )
        pre_intersection = _intersection_mm3(root.capture_pin, root.frame_counterpart)
        corrected_counterpart = _single(
            root.frame_counterpart.cut(bore),
            f"{root.root_id} corrected clevis counterpart",
        )
        corrected_frame = _single(
            corrected_frame.cut(bore),
            f"frame after {root.root_id} clevis bore",
        )
        post_intersection = _intersection_mm3(root.capture_pin, corrected_counterpart)
        frame_capture = _intersection_mm3(corrected_counterpart, architecture.frame_with_retention_roots)
        corrected_roots.append(
            RetentionClevisBore(
                root_id=root.root_id,
                bore_radius_mm=CLEVIS_BORE_RADIUS_MM,
                pre_cut_pin_frame_intersection_mm3=pre_intersection,
                post_cut_pin_frame_intersection_mm3=post_intersection,
                post_cut_frame_capture_volume_mm3=frame_capture,
                corrected_frame_counterpart=corrected_counterpart,
                bore_reference=bore,
            ).validate()
        )

    return StructuralFrameRetentionClevisBoreArchitecture(
        source_retention_architecture_sha256=architecture.architecture_sha256,
        roots=tuple(corrected_roots),
        frame_with_clevis_bores=corrected_frame,
    ).validate()
