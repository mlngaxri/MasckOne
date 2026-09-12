from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path

import cadquery as cq

from .structural_frame_carrier_interfaces import (
    REACTION_IDS,
    StructuralFrameCarrierInterfaceArchitecture,
    build_structural_frame_carrier_interfaces,
)

SCHEMA = "MASCK_ONE_STRUCTURAL_FRAME_CARRIER_DETENT_V1"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"
ROOT_WIDTH_MM = 1.40
ROOT_LENGTH_MM = 1.20
ROOT_HEIGHT_MM = 0.70
BEAM_WIDTH_MM = 0.70
BEAM_LENGTH_MM = 2.40
BEAM_HEIGHT_MM = 0.45
NOSE_WIDTH_MM = 1.10
NOSE_LENGTH_MM = 0.55
NOSE_HEIGHT_MM = 0.75
NOSE_RISE_MM = 0.30
NOMINAL_COUNTERFACE_GAP_MM = 0.12
HOSTILE_SEATING_OVERTRAVEL_MM = 0.30
_INTERSECTION_TOLERANCE_MM3 = 1e-7


class StructuralFrameCarrierDetentError(ValueError):
    pass


def _intersection_volume(a: cq.Workplane, b: cq.Workplane) -> float:
    try:
        return max(0.0, float(a.intersect(b).val().Volume()))
    except Exception:
        return 0.0


def _valid_single_solid(shape: cq.Workplane, label: str) -> None:
    value = shape.val()
    if not value.isValid() or len(value.Solids()) != 1 or float(value.Volume()) <= 0.0:
        raise StructuralFrameCarrierDetentError(f"{label} must be one valid positive-volume B-rep solid")


@dataclass(frozen=True, slots=True)
class CarrierDetentFeature:
    reaction_id: str
    center_xy_mm: tuple[float, float]
    detent_feature: cq.Workplane = field(repr=False, compare=False)
    source_interface_capture_mm3: float = 0.0
    nominal_counterface_intersection_mm3: float = 0.0
    hostile_counterface_intersection_mm3: float = 0.0

    def __post_init__(self) -> None:
        if self.reaction_id not in REACTION_IDS:
            raise StructuralFrameCarrierDetentError("unknown carrier detent feature")
        _valid_single_solid(self.detent_feature, self.reaction_id)
        if self.source_interface_capture_mm3 <= _INTERSECTION_TOLERANCE_MM3:
            raise StructuralFrameCarrierDetentError("carrier detent lacks positive frame-side capture")
        if self.nominal_counterface_intersection_mm3 > _INTERSECTION_TOLERANCE_MM3:
            raise StructuralFrameCarrierDetentError("carrier detent lacks nominal seating clearance")
        if self.hostile_counterface_intersection_mm3 <= _INTERSECTION_TOLERANCE_MM3:
            raise StructuralFrameCarrierDetentError("carrier detent lacks positive seating engagement")

    def manifest(self) -> dict[str, object]:
        return {
            "reaction_id": self.reaction_id,
            "coordinate_frame_id": WORLD_FRAME_ID,
            "center_xy_mm": list(self.center_xy_mm),
            "semantics": "FRAME_SIDE_COMPLIANT_AXIAL_CAPTURE_DETENT_COUNTERPART",
            "intended_capture_axis": "Y",
            "carrier_counterface_status": "CELL7_COUNTERFACE_REQUIRED_BEFORE_CAPTURE_DOF_CAN_BE_CLAIMED",
            "dimensions_mm": {
                "root_width": ROOT_WIDTH_MM,
                "root_length": ROOT_LENGTH_MM,
                "root_height": ROOT_HEIGHT_MM,
                "beam_width": BEAM_WIDTH_MM,
                "beam_length": BEAM_LENGTH_MM,
                "beam_height": BEAM_HEIGHT_MM,
                "nose_width": NOSE_WIDTH_MM,
                "nose_length": NOSE_LENGTH_MM,
                "nose_height": NOSE_HEIGHT_MM,
                "nose_rise": NOSE_RISE_MM,
                "nominal_counterface_gap": NOMINAL_COUNTERFACE_GAP_MM,
                "hostile_seating_overtravel": HOSTILE_SEATING_OVERTRAVEL_MM,
            },
            "measured": {
                "positive_source_interface_capture_mm3": self.source_interface_capture_mm3,
                "nominal_counterface_intersection_mm3": self.nominal_counterface_intersection_mm3,
                "hostile_counterface_intersection_mm3": self.hostile_counterface_intersection_mm3,
                "detent_feature_volume_mm3": float(self.detent_feature.val().Volume()),
            },
            "force_stiffness_fatigue_wear_release_force_and_acoustic_performance": "PHYSICAL_VALIDATION_OPEN",
        }


@dataclass(frozen=True, slots=True)
class StructuralFrameCarrierDetentArchitecture:
    source_interface_architecture_sha256: str
    features: tuple[CarrierDetentFeature, ...]
    physical_validation_eligible: bool = False

    def __post_init__(self) -> None:
        if len(self.source_interface_architecture_sha256) != 64:
            raise StructuralFrameCarrierDetentError("source interface identity must be SHA-256")
        if tuple(item.reaction_id for item in self.features) != REACTION_IDS:
            raise StructuralFrameCarrierDetentError("all four carrier detent counterparts must exist")
        if self.physical_validation_eligible:
            raise StructuralFrameCarrierDetentError("digital detent geometry is not physical evidence")

    @property
    def architecture_sha256(self) -> str:
        raw = json.dumps(self.manifest(include_sha=False), sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        return hashlib.sha256(raw).hexdigest()

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema": SCHEMA,
            "source_interface_architecture_sha256": self.source_interface_architecture_sha256,
            "coordinate_frame_id": WORLD_FRAME_ID,
            "features": [item.manifest() for item in self.features],
            "mechanical_status": "FRAME_SIDE_AXIAL_CAPTURE_DETENT_GEOMETRY_REALIZED_CELL7_COUNTERFACE_AND_PHYSICAL_RESPONSE_OPEN",
            "physical_validation_eligible": self.physical_validation_eligible,
        }
        if include_sha:
            payload["architecture_sha256"] = self.architecture_sha256
        return payload


def _feature_for_interface(interface) -> tuple[cq.Workplane, cq.Workplane]:
    bb = interface.interface.val().BoundingBox()
    cx, cy = interface.center_xy_mm
    z0 = float(bb.zmax) - ROOT_HEIGHT_MM
    stop_inner_y = cy - 3.0 + 0.8
    root_y = stop_inner_y + ROOT_LENGTH_MM / 2.0
    root = cq.Workplane("XY").box(ROOT_WIDTH_MM, ROOT_LENGTH_MM, ROOT_HEIGHT_MM, centered=(True, True, False)).translate((cx, root_y, z0))
    beam_y = root_y + ROOT_LENGTH_MM / 2.0 + BEAM_LENGTH_MM / 2.0
    beam = cq.Workplane("XY").box(BEAM_WIDTH_MM, BEAM_LENGTH_MM, BEAM_HEIGHT_MM, centered=(True, True, False)).translate((cx, beam_y, z0 + 0.10))
    nose_y = beam_y + BEAM_LENGTH_MM / 2.0 - NOSE_LENGTH_MM / 2.0
    nose = cq.Workplane("XY").box(NOSE_WIDTH_MM, NOSE_LENGTH_MM, NOSE_HEIGHT_MM, centered=(True, True, False)).translate((cx, nose_y, z0 + NOSE_RISE_MM))
    feature = root.union(beam).union(nose)
    counterface_y = nose_y + NOSE_LENGTH_MM / 2.0 + NOMINAL_COUNTERFACE_GAP_MM + NOSE_LENGTH_MM / 2.0
    counterface = cq.Workplane("XY").box(NOSE_WIDTH_MM, NOSE_LENGTH_MM, NOSE_HEIGHT_MM, centered=(True, True, False)).translate((cx, counterface_y, z0 + NOSE_RISE_MM))
    return feature, counterface


def build_structural_frame_carrier_detent(*, interfaces: StructuralFrameCarrierInterfaceArchitecture | None = None) -> StructuralFrameCarrierDetentArchitecture:
    interfaces = build_structural_frame_carrier_interfaces() if interfaces is None else interfaces
    built: list[CarrierDetentFeature] = []
    for source in interfaces.interfaces:
        feature, counterface = _feature_for_interface(source)
        _valid_single_solid(feature, source.reaction_id)
        capture = _intersection_volume(feature, source.interface)
        nominal = _intersection_volume(feature, counterface)
        hostile = _intersection_volume(feature, counterface.translate((0.0, -HOSTILE_SEATING_OVERTRAVEL_MM, 0.0)))
        built.append(CarrierDetentFeature(source.reaction_id, source.center_xy_mm, feature, round(capture, 8), round(nominal, 8), round(hostile, 8)))
    result = StructuralFrameCarrierDetentArchitecture(interfaces.architecture_sha256, tuple(built), False)
    result.__post_init__()
    return result


def export_structural_frame_carrier_detent(output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    architecture = build_structural_frame_carrier_detent()
    for item in architecture.features:
        cq.exporters.export(item.detent_feature, str(output_dir / f"{item.reaction_id.lower()}_carrier_detent.step"))
    manifest = architecture.manifest()
    (output_dir / "structural_frame_carrier_detent_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest
