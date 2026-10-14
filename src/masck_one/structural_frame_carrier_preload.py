from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import math
from pathlib import Path

import cadquery as cq

from .structural_frame_carrier_interfaces import (
    RAIL_HEIGHT_MM,
    REACTION_IDS,
    StructuralFrameCarrierInterfaceArchitecture,
    build_structural_frame_carrier_interfaces,
)

SCHEMA = "MASCK_ONE_STRUCTURAL_FRAME_CARRIER_PRELOAD_V1"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"
LEAF_ROOT_WIDTH_MM = 0.80
LEAF_ROOT_LENGTH_MM = 1.60
LEAF_ROOT_HEIGHT_MM = 0.45
LEAF_WIDTH_MM = 0.40
LEAF_LENGTH_MM = 2.40
LEAF_HEIGHT_MM = 0.80
LEAF_OUTBOARD_OFFSET_MM = 2.90
COUNTERFACE_WIDTH_MM = 0.30
COUNTERFACE_LENGTH_MM = 1.00
COUNTERFACE_HEIGHT_MM = 0.60
NOMINAL_LATERAL_GAP_MM = 0.15
HOSTILE_LATERAL_OVERTRAVEL_MM = 0.25
_INTERSECTION_TOLERANCE_MM3 = 1e-7


class StructuralFrameCarrierPreloadError(ValueError):
    pass


def _intersection_volume(a: cq.Workplane, b: cq.Workplane) -> float:
    try:
        common = a.intersect(b).val()
        if not common.isValid():
            raise StructuralFrameCarrierPreloadError("carrier preload intersection produced invalid B-rep evidence")
        volume = float(common.Volume())
    except StructuralFrameCarrierPreloadError:
        raise
    except Exception as exc:
        raise StructuralFrameCarrierPreloadError("carrier preload intersection kernel failed") from exc
    if not math.isfinite(volume) or volume < 0.0:
        raise StructuralFrameCarrierPreloadError("carrier preload intersection produced invalid volume evidence")
    return volume


def _valid_single_solid(shape: cq.Workplane, label: str) -> None:
    value = shape.val()
    volume = float(value.Volume())
    if not value.isValid() or len(value.Solids()) != 1 or not math.isfinite(volume) or volume <= 0.0:
        raise StructuralFrameCarrierPreloadError(f"{label} must be one valid positive-volume B-rep solid")


def _valid_evidence(value: float, label: str) -> None:
    if not math.isfinite(value) or value < 0.0:
        raise StructuralFrameCarrierPreloadError(f"{label} must be finite nonnegative geometric evidence")


@dataclass(frozen=True, slots=True)
class CarrierPreloadFeature:
    reaction_id: str
    center_xy_mm: tuple[float, float]
    preload_feature: cq.Workplane = field(repr=False, compare=False)
    source_interface_capture_mm3: float = 0.0
    nominal_counterface_intersection_mm3: float = 0.0
    hostile_counterface_intersection_mm3: float = 0.0

    def __post_init__(self) -> None:
        if self.reaction_id not in REACTION_IDS:
            raise StructuralFrameCarrierPreloadError("unknown carrier preload feature")
        _valid_single_solid(self.preload_feature, self.reaction_id)
        _valid_evidence(self.source_interface_capture_mm3, "source interface capture")
        _valid_evidence(self.nominal_counterface_intersection_mm3, "nominal counterface intersection")
        _valid_evidence(self.hostile_counterface_intersection_mm3, "hostile counterface intersection")
        if self.source_interface_capture_mm3 <= _INTERSECTION_TOLERANCE_MM3:
            raise StructuralFrameCarrierPreloadError("carrier preload feature lacks positive source-interface capture")
        if self.nominal_counterface_intersection_mm3 > _INTERSECTION_TOLERANCE_MM3:
            raise StructuralFrameCarrierPreloadError("carrier preload feature has no nominal lateral running gap")
        if self.hostile_counterface_intersection_mm3 <= _INTERSECTION_TOLERANCE_MM3:
            raise StructuralFrameCarrierPreloadError("carrier preload feature lacks positive hostile lateral engagement")

    def manifest(self) -> dict[str, object]:
        return {
            "reaction_id": self.reaction_id,
            "coordinate_frame_id": WORLD_FRAME_ID,
            "center_xy_mm": list(self.center_xy_mm),
            "semantics": "FRAME_SIDE_INTEGRAL_ANTI_RATTLE_PRELOAD_LEAF_GEOMETRY",
            "intended_compliance_axis": "X",
            "dimensions_mm": {
                "leaf_root_width": LEAF_ROOT_WIDTH_MM,
                "leaf_root_length": LEAF_ROOT_LENGTH_MM,
                "leaf_root_height": LEAF_ROOT_HEIGHT_MM,
                "leaf_width": LEAF_WIDTH_MM,
                "leaf_length": LEAF_LENGTH_MM,
                "leaf_height": LEAF_HEIGHT_MM,
                "nominal_lateral_gap": NOMINAL_LATERAL_GAP_MM,
                "hostile_lateral_overtravel": HOSTILE_LATERAL_OVERTRAVEL_MM,
            },
            "measured": {
                "positive_source_interface_capture_mm3": self.source_interface_capture_mm3,
                "nominal_counterface_intersection_mm3": self.nominal_counterface_intersection_mm3,
                "hostile_counterface_intersection_mm3": self.hostile_counterface_intersection_mm3,
                "preload_feature_volume_mm3": float(self.preload_feature.val().Volume()),
            },
            "force_preload_stiffness_and_acoustic_performance": "PHYSICAL_VALIDATION_OPEN",
        }


@dataclass(frozen=True, slots=True)
class StructuralFrameCarrierPreloadArchitecture:
    source_interface_architecture_sha256: str
    features: tuple[CarrierPreloadFeature, ...]
    physical_validation_eligible: bool = False

    def __post_init__(self) -> None:
        if len(self.source_interface_architecture_sha256) != 64 or any(c not in "0123456789abcdef" for c in self.source_interface_architecture_sha256):
            raise StructuralFrameCarrierPreloadError("source interface identity must be lowercase hexadecimal SHA-256")
        if tuple(f.reaction_id for f in self.features) != REACTION_IDS:
            raise StructuralFrameCarrierPreloadError("all four carrier preload features must exist in controlled order")
        if self.physical_validation_eligible is not False:
            raise StructuralFrameCarrierPreloadError("digital preload geometry is not physical evidence")

    @property
    def architecture_sha256(self) -> str:
        raw = json.dumps(self.manifest(include_sha=False), sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        return hashlib.sha256(raw).hexdigest()

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema": SCHEMA,
            "source_interface_architecture_sha256": self.source_interface_architecture_sha256,
            "coordinate_frame_id": WORLD_FRAME_ID,
            "features": [f.manifest() for f in self.features],
            "mechanical_status": "FRAME_SIDE_PRELOAD_GEOMETRY_REALIZED_CELL7_COUNTERFACE_AND_PHYSICAL_PRELOAD_VALIDATION_OPEN",
            "physical_validation_eligible": self.physical_validation_eligible,
        }
        if include_sha:
            payload["architecture_sha256"] = self.architecture_sha256
        return payload


def _feature_for_interface(interface) -> tuple[cq.Workplane, cq.Workplane]:
    bb = interface.interface.val().BoundingBox()
    cx, cy = interface.center_xy_mm
    z_top = float(bb.zmin) + RAIL_HEIGHT_MM
    sign = 1.0 if cx >= 0.0 else -1.0
    root_x = cx + sign * (LEAF_OUTBOARD_OFFSET_MM - LEAF_ROOT_WIDTH_MM / 2.0)
    root = cq.Workplane("XY").box(LEAF_ROOT_WIDTH_MM, LEAF_ROOT_LENGTH_MM, LEAF_ROOT_HEIGHT_MM, centered=(True, True, False)).translate((root_x, cy, z_top - LEAF_ROOT_HEIGHT_MM))
    leaf_x = cx + sign * LEAF_OUTBOARD_OFFSET_MM
    leaf = cq.Workplane("XY").box(LEAF_WIDTH_MM, LEAF_LENGTH_MM, LEAF_HEIGHT_MM, centered=(True, True, False)).translate((leaf_x, cy, z_top - LEAF_ROOT_HEIGHT_MM))
    feature = root.union(leaf)
    counterface_x = leaf_x + sign * (LEAF_WIDTH_MM / 2.0 + NOMINAL_LATERAL_GAP_MM + COUNTERFACE_WIDTH_MM / 2.0)
    counterface = cq.Workplane("XY").box(COUNTERFACE_WIDTH_MM, COUNTERFACE_LENGTH_MM, COUNTERFACE_HEIGHT_MM, centered=(True, True, False)).translate((counterface_x, cy, z_top - LEAF_ROOT_HEIGHT_MM))
    return feature, counterface


def build_structural_frame_carrier_preload(*, interfaces: StructuralFrameCarrierInterfaceArchitecture | None = None) -> StructuralFrameCarrierPreloadArchitecture:
    interfaces = build_structural_frame_carrier_interfaces() if interfaces is None else interfaces
    built: list[CarrierPreloadFeature] = []
    for source in interfaces.interfaces:
        feature, counterface = _feature_for_interface(source)
        _valid_single_solid(feature, source.reaction_id)
        capture = _intersection_volume(feature, source.interface)
        nominal = _intersection_volume(feature, counterface)
        sign = 1.0 if source.center_xy_mm[0] >= 0.0 else -1.0
        hostile = _intersection_volume(feature, counterface.translate((-sign * HOSTILE_LATERAL_OVERTRAVEL_MM, 0.0, 0.0)))
        built.append(CarrierPreloadFeature(source.reaction_id, source.center_xy_mm, feature, round(capture, 8), round(nominal, 8), round(hostile, 8)))
    result = StructuralFrameCarrierPreloadArchitecture(interfaces.architecture_sha256, tuple(built), False)
    result.__post_init__()
    return result


def export_structural_frame_carrier_preload(output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    architecture = build_structural_frame_carrier_preload()
    for item in architecture.features:
        cq.exporters.export(item.preload_feature, str(output_dir / f"{item.reaction_id.lower()}_carrier_preload_feature.step"))
    manifest = architecture.manifest()
    (output_dir / "structural_frame_carrier_preload_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    return manifest
