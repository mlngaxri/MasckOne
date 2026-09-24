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

SCHEMA = "MASCK_ONE_STRUCTURAL_FRAME_CARRIER_LANDING_V1"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"
ROOT_WIDTH_MM = 2.0
ROOT_LENGTH_MM = 0.9
ROOT_HEIGHT_MM = 0.70
ROOT_STOP_CAPTURE_MM = 0.20
TONGUE_WIDTH_MM = 2.0
TONGUE_LENGTH_MM = 2.2
TONGUE_HEIGHT_MM = 0.45
TONGUE_RISE_MM = 0.22
LANDING_PROBE_WIDTH_MM = 1.6
LANDING_PROBE_LENGTH_MM = 0.40
LANDING_PROBE_HEIGHT_MM = 0.45
NOMINAL_LANDING_GAP_MM = 0.12
HOSTILE_LANDING_OVERTRAVEL_MM = 0.30
_INTERSECTION_TOLERANCE_MM3 = 1e-7


class StructuralFrameCarrierLandingError(ValueError):
    pass


def _intersection_volume(a: cq.Workplane, b: cq.Workplane) -> float:
    try:
        return max(0.0, float(a.intersect(b).val().Volume()))
    except Exception:
        return 0.0


def _valid_single_solid(shape: cq.Workplane, label: str) -> None:
    value = shape.val()
    if not value.isValid() or len(value.Solids()) != 1 or float(value.Volume()) <= 0.0:
        raise StructuralFrameCarrierLandingError(f"{label} must be one valid positive-volume B-rep solid")


@dataclass(frozen=True, slots=True)
class CarrierLandingFeature:
    reaction_id: str
    center_xy_mm: tuple[float, float]
    landing_feature: cq.Workplane = field(repr=False, compare=False)
    source_interface_capture_mm3: float = 0.0
    nominal_probe_intersection_mm3: float = 0.0
    hostile_probe_intersection_mm3: float = 0.0

    def __post_init__(self) -> None:
        if self.reaction_id not in REACTION_IDS:
            raise StructuralFrameCarrierLandingError("unknown carrier landing feature")
        _valid_single_solid(self.landing_feature, self.reaction_id)
        if self.source_interface_capture_mm3 <= _INTERSECTION_TOLERANCE_MM3:
            raise StructuralFrameCarrierLandingError("landing tongue lacks positive frame-side capture")
        if self.nominal_probe_intersection_mm3 > _INTERSECTION_TOLERANCE_MM3:
            raise StructuralFrameCarrierLandingError("carrier landing has no nominal approach gap")
        if self.hostile_probe_intersection_mm3 <= _INTERSECTION_TOLERANCE_MM3:
            raise StructuralFrameCarrierLandingError("carrier landing lacks positive overtravel engagement")

    def manifest(self) -> dict[str, object]:
        return {
            "reaction_id": self.reaction_id,
            "coordinate_frame_id": WORLD_FRAME_ID,
            "center_xy_mm": list(self.center_xy_mm),
            "semantics": "FRAME_SIDE_CANTILEVER_LANDING_TONGUE_BEFORE_RIGID_END_STOP",
            "intended_compliance_axis": "Y",
            "dimensions_mm": {
                "root_width": ROOT_WIDTH_MM,
                "root_length": ROOT_LENGTH_MM,
                "root_height": ROOT_HEIGHT_MM,
                "root_stop_capture": ROOT_STOP_CAPTURE_MM,
                "tongue_width": TONGUE_WIDTH_MM,
                "tongue_length": TONGUE_LENGTH_MM,
                "tongue_height": TONGUE_HEIGHT_MM,
                "tongue_rise": TONGUE_RISE_MM,
                "nominal_landing_gap": NOMINAL_LANDING_GAP_MM,
                "hostile_landing_overtravel": HOSTILE_LANDING_OVERTRAVEL_MM,
            },
            "measured": {
                "positive_source_interface_capture_mm3": self.source_interface_capture_mm3,
                "nominal_probe_intersection_mm3": self.nominal_probe_intersection_mm3,
                "hostile_probe_intersection_mm3": self.hostile_probe_intersection_mm3,
                "landing_feature_volume_mm3": float(self.landing_feature.val().Volume()),
            },
            "force_stiffness_damping_fatigue_and_acoustic_performance": "PHYSICAL_VALIDATION_OPEN",
        }


@dataclass(frozen=True, slots=True)
class StructuralFrameCarrierLandingArchitecture:
    source_interface_architecture_sha256: str
    features: tuple[CarrierLandingFeature, ...]
    physical_validation_eligible: bool = False

    def __post_init__(self) -> None:
        if len(self.source_interface_architecture_sha256) != 64:
            raise StructuralFrameCarrierLandingError("source interface identity must be SHA-256")
        if tuple(item.reaction_id for item in self.features) != REACTION_IDS:
            raise StructuralFrameCarrierLandingError("all four carrier landing features must exist")
        if self.physical_validation_eligible:
            raise StructuralFrameCarrierLandingError("digital landing geometry is not physical evidence")

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
            "mechanical_status": "FRAME_SIDE_PROGRESSIVE_LANDING_GEOMETRY_REALIZED_CARRIER_COUNTERFACE_AND_PHYSICAL_RESPONSE_OPEN",
            "physical_validation_eligible": self.physical_validation_eligible,
        }
        if include_sha:
            payload["architecture_sha256"] = self.architecture_sha256
        return payload


def _feature_for_interface(interface) -> tuple[cq.Workplane, cq.Workplane]:
    bb = interface.interface.val().BoundingBox()
    cx, cy = interface.center_xy_mm
    stop_inner_y = cy - 3.0 + 0.8
    root_y = stop_inner_y - ROOT_STOP_CAPTURE_MM + ROOT_LENGTH_MM / 2.0
    z0 = float(bb.zmax) - ROOT_HEIGHT_MM
    root = cq.Workplane("XY").box(ROOT_WIDTH_MM, ROOT_LENGTH_MM, ROOT_HEIGHT_MM, centered=(True, True, False)).translate((cx, root_y, z0))
    tongue_y = root_y + ROOT_LENGTH_MM / 2.0 + TONGUE_LENGTH_MM / 2.0
    tongue = cq.Workplane("XY").box(TONGUE_WIDTH_MM, TONGUE_LENGTH_MM, TONGUE_HEIGHT_MM, centered=(True, True, False)).translate((cx, tongue_y, z0 + TONGUE_RISE_MM))
    feature = root.union(tongue)
    probe_center_y = tongue_y + TONGUE_LENGTH_MM / 2.0 + NOMINAL_LANDING_GAP_MM + LANDING_PROBE_LENGTH_MM / 2.0
    probe = cq.Workplane("XY").box(LANDING_PROBE_WIDTH_MM, LANDING_PROBE_LENGTH_MM, LANDING_PROBE_HEIGHT_MM, centered=(True, True, False)).translate((cx, probe_center_y, z0 + TONGUE_RISE_MM))
    return feature, probe


def build_structural_frame_carrier_landing(*, interfaces: StructuralFrameCarrierInterfaceArchitecture | None = None) -> StructuralFrameCarrierLandingArchitecture:
    interfaces = build_structural_frame_carrier_interfaces() if interfaces is None else interfaces
    built: list[CarrierLandingFeature] = []
    for source in interfaces.interfaces:
        feature, probe = _feature_for_interface(source)
        _valid_single_solid(feature, source.reaction_id)
        capture = _intersection_volume(feature, source.interface)
        nominal = _intersection_volume(feature, probe)
        hostile = _intersection_volume(feature, probe.translate((0.0, -HOSTILE_LANDING_OVERTRAVEL_MM, 0.0)))
        built.append(CarrierLandingFeature(source.reaction_id, source.center_xy_mm, feature, round(capture, 8), round(nominal, 8), round(hostile, 8)))
    result = StructuralFrameCarrierLandingArchitecture(interfaces.architecture_sha256, tuple(built), False)
    result.__post_init__()
    return result


def export_structural_frame_carrier_landing(output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    architecture = build_structural_frame_carrier_landing()
    for item in architecture.features:
        cq.exporters.export(item.landing_feature, str(output_dir / f"{item.reaction_id.lower()}_carrier_landing_tongue.step"))
    manifest = architecture.manifest()
    (output_dir / "structural_frame_carrier_landing_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest
