from __future__ import annotations

"""Buildable split-retainer throat overlay for the bilateral retention roots.

V1 proved radial shoulder overlap but did not constrain the open C-clip throat. The
legacy seed cut can leave an opening wider than the pin shaft, allowing nominal
radial escape. V2 makes the throat explicit and fail-closed while preserving the
accepted pin, groove, root, yoke and service-corridor geometry.
"""

from dataclasses import dataclass, field
from hashlib import sha256
import json
import math

import cadquery as cq

from . import structural_frame_retention_root_capture_v1 as capture_v1
from .structural_frame_retention_roots import (
    CLEVIS_CLIP_RADIAL_THICKNESS_MM,
    CLEVIS_PIN_GROOVE_DEPTH_MM,
    CLEVIS_PIN_GROOVE_WIDTH_MM,
    CLEVIS_PIN_RADIUS_MM,
    ROOT_IDS,
    StructuralFrameRetentionRootArchitecture,
    build_structural_frame_retention_roots,
)

SCHEMA = "MASCK_ONE_STRUCTURAL_FRAME_RETENTION_ROOT_CAPTURE_V2"
CLIP_HOLE_RELIEF_MM = capture_v1.CLIP_HOLE_RELIEF_MM
CLIP_THROAT_WIDTH_MM = 2.43
# The legacy retainer used the full 0.75 mm groove width as its axial thickness,
# leaving zero nominal assembly clearance. Keep the accepted groove unchanged and
# make the corrected retainer 0.60 mm thick, leaving 0.15 mm total axial clearance.
CLIP_AXIAL_THICKNESS_MM = 0.60
_MIN_DIGITAL_MARGIN_MM = 0.02


class StructuralFrameRetentionRootCaptureV2Error(ValueError):
    pass


def _cylinder_y(radius: float, length: float, center: tuple[float, float, float]) -> cq.Workplane:
    x, y, z = center
    start = cq.Vector(x, y - length / 2.0, z)
    solid = cq.Solid.makeCylinder(radius, length, start, cq.Vector(0.0, 1.0, 0.0))
    return cq.Workplane("XY").newObject([solid])


def _single(shape: cq.Workplane, label: str) -> cq.Workplane:
    value = shape.val()
    if not value.isValid() or len(value.Solids()) != 1 or float(value.Volume()) <= 0.0:
        raise StructuralFrameRetentionRootCaptureV2Error(f"{label} must be one valid positive-volume solid")
    return shape


def _throat_metrics() -> tuple[float, float, float, float]:
    groove_bottom_diameter = 2.0 * (CLEVIS_PIN_RADIUS_MM - CLEVIS_PIN_GROOVE_DEPTH_MM)
    clip_inner_diameter = 2.0 * (CLEVIS_PIN_RADIUS_MM - CLEVIS_PIN_GROOVE_DEPTH_MM + CLIP_HOLE_RELIEF_MM)
    shaft_diameter = 2.0 * CLEVIS_PIN_RADIUS_MM
    installation_margin = CLIP_THROAT_WIDTH_MM - clip_inner_diameter
    capture_margin = shaft_diameter - CLIP_THROAT_WIDTH_MM
    values = (groove_bottom_diameter, clip_inner_diameter, installation_margin, capture_margin)
    if not all(math.isfinite(v) and v > 0.0 for v in values):
        raise StructuralFrameRetentionRootCaptureV2Error("split-retainer throat metrics must be finite and positive")
    if CLIP_THROAT_WIDTH_MM <= clip_inner_diameter + _MIN_DIGITAL_MARGIN_MM:
        raise StructuralFrameRetentionRootCaptureV2Error("retainer throat does not clear its seated inner diameter")
    if CLIP_THROAT_WIDTH_MM >= shaft_diameter - _MIN_DIGITAL_MARGIN_MM:
        raise StructuralFrameRetentionRootCaptureV2Error("retainer throat is not narrower than the capture-pin shaft")
    if not (0.0 < CLIP_AXIAL_THICKNESS_MM < CLEVIS_PIN_GROOVE_WIDTH_MM):
        raise StructuralFrameRetentionRootCaptureV2Error("split retainer requires positive nominal axial groove clearance")
    return groove_bottom_diameter, clip_inner_diameter, installation_margin, capture_margin


def build_positive_capture_split_retainer(*, center_x: float, groove_center_y: float, center_z: float) -> cq.Workplane:
    _throat_metrics()
    inner = CLEVIS_PIN_RADIUS_MM - CLEVIS_PIN_GROOVE_DEPTH_MM + CLIP_HOLE_RELIEF_MM
    outer = CLEVIS_PIN_RADIUS_MM + CLEVIS_CLIP_RADIAL_THICKNESS_MM
    if CLIP_THROAT_WIDTH_MM >= 2.0 * outer:
        raise StructuralFrameRetentionRootCaptureV2Error("retainer throat exceeds outer diameter")
    full = _cylinder_y(outer, CLIP_AXIAL_THICKNESS_MM, (center_x, groove_center_y, center_z))
    hole = _cylinder_y(inner, CLIP_AXIAL_THICKNESS_MM + 0.2, (center_x, groove_center_y, center_z))
    ring = full.cut(hole)
    cut_height = outer + 0.04
    split = cq.Workplane("XY").box(
        CLIP_THROAT_WIDTH_MM,
        CLIP_AXIAL_THICKNESS_MM + 0.4,
        cut_height,
        centered=(True, True, True),
    ).translate((center_x, groove_center_y, center_z + cut_height / 2.0 - 0.01))
    return _single(ring.cut(split), "positive-capture split retainer")


@dataclass(frozen=True, slots=True)
class StructuralFrameRetentionRootCaptureV2:
    source_root_architecture_sha256: str
    source_capture_v1_sha256: str
    throat_width_mm: float
    installation_margin_mm: float
    radial_escape_capture_margin_mm: float
    evidence_sha256: str
    retainers: tuple[cq.Workplane, ...] = field(repr=False, compare=False)
    accidental_release_validated: bool = False
    physical_validation_eligible: bool = False

    def validate(self) -> "StructuralFrameRetentionRootCaptureV2":
        roots = build_structural_frame_retention_roots()
        v1 = capture_v1.build_structural_frame_retention_root_capture_v1()
        _, _, install, capture = _throat_metrics()
        if self.source_root_architecture_sha256 != roots.architecture_sha256:
            raise StructuralFrameRetentionRootCaptureV2Error("source retention-root architecture is stale")
        if self.source_capture_v1_sha256 != v1.capture_evidence_sha256:
            raise StructuralFrameRetentionRootCaptureV2Error("source capture V1 evidence is stale")
        if self.throat_width_mm != CLIP_THROAT_WIDTH_MM:
            raise StructuralFrameRetentionRootCaptureV2Error("split-retainer throat authority is stale")
        if self.installation_margin_mm != round(install, 12) or self.radial_escape_capture_margin_mm != round(capture, 12):
            raise StructuralFrameRetentionRootCaptureV2Error("split-retainer throat margins are stale")
        if len(self.retainers) != len(ROOT_IDS):
            raise StructuralFrameRetentionRootCaptureV2Error("bilateral corrected retainers are required")
        for retainer in self.retainers:
            _single(retainer, "positive-capture split retainer")
            bb = retainer.val().BoundingBox()
            if abs(float(bb.ylen) - CLIP_AXIAL_THICKNESS_MM) > 1e-6:
                raise StructuralFrameRetentionRootCaptureV2Error("split-retainer axial thickness is stale")
        payload = {
            "source_root_architecture_sha256": self.source_root_architecture_sha256,
            "source_capture_v1_sha256": self.source_capture_v1_sha256,
            "root_ids": list(ROOT_IDS),
            "throat_width_mm": self.throat_width_mm,
            "clip_axial_thickness_mm": CLIP_AXIAL_THICKNESS_MM,
            "axial_groove_clearance_mm": round(CLEVIS_PIN_GROOVE_WIDTH_MM - CLIP_AXIAL_THICKNESS_MM, 12),
            "installation_margin_mm": self.installation_margin_mm,
            "radial_escape_capture_margin_mm": self.radial_escape_capture_margin_mm,
        }
        digest = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        if self.evidence_sha256 != digest:
            raise StructuralFrameRetentionRootCaptureV2Error("capture V2 evidence digest is stale")
        if self.accidental_release_validated is not False or self.physical_validation_eligible is not False:
            raise StructuralFrameRetentionRootCaptureV2Error("digital throat geometry is not physical accidental-release evidence")
        return self

    def manifest(self) -> dict[str, object]:
        self.validate()
        return {
            "schema": SCHEMA,
            "source_root_architecture_sha256": self.source_root_architecture_sha256,
            "source_capture_v1_sha256": self.source_capture_v1_sha256,
            "throat_width_mm": self.throat_width_mm,
            "clip_axial_thickness_mm": CLIP_AXIAL_THICKNESS_MM,
            "axial_groove_clearance_mm": round(CLEVIS_PIN_GROOVE_WIDTH_MM - CLIP_AXIAL_THICKNESS_MM, 12),
            "installation_margin_mm": self.installation_margin_mm,
            "radial_escape_capture_margin_mm": self.radial_escape_capture_margin_mm,
            "capture_status": "CONTROLLED_C_CLIP_THROAT_WITH_POSITIVE_AXIAL_GROOVE_CLEARANCE",
            "evidence_sha256": self.evidence_sha256,
            "accidental_release_validated": self.accidental_release_validated,
            "physical_validation_eligible": self.physical_validation_eligible,
        }


def build_structural_frame_retention_root_capture_v2() -> StructuralFrameRetentionRootCaptureV2:
    roots: StructuralFrameRetentionRootArchitecture = build_structural_frame_retention_roots()
    v1 = capture_v1.build_structural_frame_retention_root_capture_v1()
    _, _, install, capture = _throat_metrics()
    retainers = []
    for root in roots.roots:
        bb = root.split_retainer.val().BoundingBox()
        groove_center_y = (float(bb.ymin) + float(bb.ymax)) / 2.0
        x, _, z = root.center_xyz_mm
        retainers.append(build_positive_capture_split_retainer(center_x=x, groove_center_y=groove_center_y, center_z=z))
    payload = {
        "source_root_architecture_sha256": roots.architecture_sha256,
        "source_capture_v1_sha256": v1.capture_evidence_sha256,
        "root_ids": list(ROOT_IDS),
        "throat_width_mm": CLIP_THROAT_WIDTH_MM,
        "clip_axial_thickness_mm": CLIP_AXIAL_THICKNESS_MM,
        "axial_groove_clearance_mm": round(CLEVIS_PIN_GROOVE_WIDTH_MM - CLIP_AXIAL_THICKNESS_MM, 12),
        "installation_margin_mm": round(install, 12),
        "radial_escape_capture_margin_mm": round(capture, 12),
    }
    digest = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    return StructuralFrameRetentionRootCaptureV2(
        roots.architecture_sha256,
        v1.capture_evidence_sha256,
        CLIP_THROAT_WIDTH_MM,
        round(install, 12),
        round(capture, 12),
        digest,
        tuple(retainers),
        False,
        False,
    ).validate()
