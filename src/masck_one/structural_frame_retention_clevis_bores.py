from __future__ import annotations

"""Realize and verify the frame-side capture-pin bores at both retention roots.

The retention-root generator establishes a positive clevis load path and a transverse
capture pin, but its frame counterpart is still solid through the pin axis. This layer
cuts an authority-bound running bore through each frame clevis and verifies that the
installed pin no longer occupies frame material, the bore fully breaks through both
Y ends, and the cut preserves the intended radial clevis ligaments around the bore.
Digital geometry only; this is not manufacturing, strength, wear, or service evidence.
"""

from dataclasses import dataclass, field
import math

import cadquery as cq

from .model import MasckOneModel, build_model
from .structural_frame_retention_roots import (
    CLEVIS_EAR_X_MM,
    CLEVIS_EAR_Z_MM,
    ROOT_IDS,
    ROOT_Y_MM,
    ROOT_Z_MM,
    YOKE_ROOT_BORE_RADIUS_MM,
    StructuralFrameRetentionRootArchitecture,
    build_structural_frame_retention_roots,
)

SCHEMA = "MASCK_ONE_STRUCTURAL_FRAME_RETENTION_CLEVIS_BORES_V3"
CLEVIS_BORE_RADIUS_MM = YOKE_ROOT_BORE_RADIUS_MM
CLEVIS_BORE_LENGTH_MM = 24.0
MIN_BORE_END_OVERTRAVEL_MM = 1.0
# Digital construction floor from the existing 8 x 8 mm clevis-ear seed around the
# authority-bound 1.6 mm bore. This is a geometry regression threshold, not a
# manufacturing tolerance or a strength-derived edge-distance requirement.
MIN_RADIAL_LIGAMENT_MM = min(CLEVIS_EAR_X_MM, CLEVIS_EAR_Z_MM) / 2.0 - CLEVIS_BORE_RADIUS_MM
GEOMETRY_TOLERANCE_MM = 1e-6
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


def _bore_end_overtravel_mm(bore: cq.Workplane, counterpart: cq.Workplane) -> tuple[float, float]:
    try:
        bore_box = bore.val().BoundingBox()
        counterpart_box = counterpart.val().BoundingBox()
        negative_y = float(counterpart_box.ymin - bore_box.ymin)
        positive_y = float(bore_box.ymax - counterpart_box.ymax)
    except Exception as exc:
        raise StructuralFrameRetentionClevisBoreError("B-rep bore extent query failed") from exc
    if not all(math.isfinite(value) for value in (negative_y, positive_y)):
        raise StructuralFrameRetentionClevisBoreError("bore end overtravel must be finite")
    return negative_y, positive_y


def _radial_ligaments_mm(
    counterpart: cq.Workplane,
    *,
    center_x: float,
    center_z: float,
    bore_radius: float,
) -> tuple[float, float, float, float]:
    """Measure exterior-to-bore radial material spans in -X, +X, -Z, +Z."""
    try:
        box = counterpart.val().BoundingBox()
        values = (
            float((center_x - bore_radius) - box.xmin),
            float(box.xmax - (center_x + bore_radius)),
            float((center_z - bore_radius) - box.zmin),
            float(box.zmax - (center_z + bore_radius)),
        )
    except Exception as exc:
        raise StructuralFrameRetentionClevisBoreError("B-rep radial ligament query failed") from exc
    if not all(math.isfinite(value) for value in values):
        raise StructuralFrameRetentionClevisBoreError("radial ligament evidence must be finite")
    return values


@dataclass(frozen=True, slots=True)
class RetentionClevisBore:
    root_id: str
    bore_radius_mm: float
    pre_cut_pin_frame_intersection_mm3: float
    post_cut_pin_frame_intersection_mm3: float
    post_cut_frame_capture_volume_mm3: float
    negative_y_bore_overtravel_mm: float
    positive_y_bore_overtravel_mm: float
    radial_ligaments_mm: tuple[float, float, float, float]
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
        for label, value in (
            ("negative-Y", self.negative_y_bore_overtravel_mm),
            ("positive-Y", self.positive_y_bore_overtravel_mm),
        ):
            if not math.isfinite(value):
                raise StructuralFrameRetentionClevisBoreError(f"{label} bore overtravel must be finite")
            if value < MIN_BORE_END_OVERTRAVEL_MM:
                raise StructuralFrameRetentionClevisBoreError(
                    f"{label} clevis bore does not fully traverse counterpart with required end margin"
                )
        if len(self.radial_ligaments_mm) != 4 or not all(math.isfinite(v) for v in self.radial_ligaments_mm):
            raise StructuralFrameRetentionClevisBoreError("four finite radial ligament measurements are required")
        if min(self.radial_ligaments_mm) + GEOMETRY_TOLERANCE_MM < MIN_RADIAL_LIGAMENT_MM:
            raise StructuralFrameRetentionClevisBoreError("clevis bore leaves insufficient radial material ligament")
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
            "minimum_bore_end_overtravel_mm": MIN_BORE_END_OVERTRAVEL_MM,
            "minimum_radial_ligament_mm": MIN_RADIAL_LIGAMENT_MM,
            "roots": [
                {
                    "root_id": root.root_id,
                    "pre_cut_pin_frame_intersection_mm3": root.pre_cut_pin_frame_intersection_mm3,
                    "post_cut_pin_frame_intersection_mm3": root.post_cut_pin_frame_intersection_mm3,
                    "post_cut_frame_capture_volume_mm3": root.post_cut_frame_capture_volume_mm3,
                    "negative_y_bore_overtravel_mm": root.negative_y_bore_overtravel_mm,
                    "positive_y_bore_overtravel_mm": root.positive_y_bore_overtravel_mm,
                    "radial_ligaments_mm": list(root.radial_ligaments_mm),
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
        negative_y_overtravel, positive_y_overtravel = _bore_end_overtravel_mm(bore, root.frame_counterpart)
        radial_ligaments = _radial_ligaments_mm(
            root.frame_counterpart,
            center_x=x,
            center_z=ROOT_Z_MM,
            bore_radius=CLEVIS_BORE_RADIUS_MM,
        )
        pre_intersection = _intersection_mm3(root.capture_pin, root.frame_counterpart)
        corrected_counterpart = _single(root.frame_counterpart.cut(bore), f"{root.root_id} corrected clevis counterpart")
        corrected_frame = _single(corrected_frame.cut(bore), f"frame after {root.root_id} clevis bore")
        post_intersection = _intersection_mm3(root.capture_pin, corrected_counterpart)
        frame_capture = _intersection_mm3(corrected_counterpart, architecture.frame_with_retention_roots)
        corrected_roots.append(
            RetentionClevisBore(
                root_id=root.root_id,
                bore_radius_mm=CLEVIS_BORE_RADIUS_MM,
                pre_cut_pin_frame_intersection_mm3=pre_intersection,
                post_cut_pin_frame_intersection_mm3=post_intersection,
                post_cut_frame_capture_volume_mm3=frame_capture,
                negative_y_bore_overtravel_mm=negative_y_overtravel,
                positive_y_bore_overtravel_mm=positive_y_overtravel,
                radial_ligaments_mm=radial_ligaments,
                corrected_frame_counterpart=corrected_counterpart,
                bore_reference=bore,
            ).validate()
        )

    return StructuralFrameRetentionClevisBoreArchitecture(
        source_retention_architecture_sha256=architecture.architecture_sha256,
        roots=tuple(corrected_roots),
        frame_with_clevis_bores=corrected_frame,
    ).validate()
