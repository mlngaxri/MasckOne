from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path

import cadquery as cq

from .structural_frame_actuator_mates import (
    REACTION_IDS,
    StructuralFrameActuatorMateArchitecture,
    build_structural_frame_actuator_mates,
)

SCHEMA = "MASCK_ONE_STRUCTURAL_FRAME_CARRIER_INTERFACES_V1"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"
RAIL_LENGTH_MM = 6.0
RAIL_ROOT_WIDTH_MM = 5.0
RAIL_CROWN_WIDTH_MM = 6.0
RAIL_HEIGHT_MM = 1.8
ENTRY_RELIEF_MM = 0.8
END_STOP_THICKNESS_MM = 0.8
END_STOP_HEIGHT_MM = 2.4
SERVICE_PROBE_MM = 0.5
SERVICE_PROBE_WIDTH_MM = 4.0
SERVICE_PROBE_LENGTH_MM = 0.30
SERVICE_PROBE_HEIGHT_MM = 1.0
SERVICE_PROBE_NOMINAL_GAP_MM = 0.10
_INTERSECTION_TOLERANCE_MM3 = 1e-7


class StructuralFrameCarrierInterfaceError(ValueError):
    pass


def _intersection_volume(a: cq.Workplane, b: cq.Workplane) -> float:
    try:
        return max(0.0, float(a.intersect(b).val().Volume()))
    except Exception:
        return 0.0


def _valid_single_solid(shape: cq.Workplane, label: str) -> None:
    value = shape.val()
    if not value.isValid() or len(value.Solids()) != 1 or float(value.Volume()) <= 0.0:
        raise StructuralFrameCarrierInterfaceError(f"{label} must be one valid positive-volume B-rep solid")


@dataclass(frozen=True, slots=True)
class CarrierInterface:
    reaction_id: str
    center_xy_mm: tuple[float, float]
    interface: cq.Workplane = field(repr=False, compare=False)
    source_mate_intersection_mm3: float = 0.0
    nominal_service_probe_intersection_mm3: float = 0.0
    hostile_stop_intersection_mm3: float = 0.0

    def __post_init__(self) -> None:
        if self.reaction_id not in REACTION_IDS:
            raise StructuralFrameCarrierInterfaceError("unknown carrier interface")
        _valid_single_solid(self.interface, self.reaction_id)
        if self.source_mate_intersection_mm3 <= _INTERSECTION_TOLERANCE_MM3:
            raise StructuralFrameCarrierInterfaceError("carrier interface lacks positive source-mate capture")
        if self.nominal_service_probe_intersection_mm3 > _INTERSECTION_TOLERANCE_MM3:
            raise StructuralFrameCarrierInterfaceError("carrier service entry is obstructed before the positive stop")
        if self.hostile_stop_intersection_mm3 <= _INTERSECTION_TOLERANCE_MM3:
            raise StructuralFrameCarrierInterfaceError("carrier interface lacks positive service end stop")

    def manifest(self) -> dict[str, object]:
        return {
            "reaction_id": self.reaction_id,
            "coordinate_frame_id": WORLD_FRAME_ID,
            "center_xy_mm": list(self.center_xy_mm),
            "interface_semantics": "POSITIVE_TAPERED_CARRIER_RAIL_WITH_OPEN_SERVICE_ENTRY_AND_END_STOP",
            "service_insertion_axis": "+Y",
            "constrained_dofs_when_future_carrier_counterpart_is_seated": ["X", "Z", "RY", "RZ"],
            "intentionally_unclaimed_dofs": ["Y", "RX"],
            "dimensions_mm": {
                "rail_length": RAIL_LENGTH_MM,
                "rail_root_width": RAIL_ROOT_WIDTH_MM,
                "rail_crown_width": RAIL_CROWN_WIDTH_MM,
                "rail_height": RAIL_HEIGHT_MM,
                "entry_relief": ENTRY_RELIEF_MM,
                "end_stop_thickness": END_STOP_THICKNESS_MM,
                "end_stop_height": END_STOP_HEIGHT_MM,
                "service_probe_width": SERVICE_PROBE_WIDTH_MM,
                "service_probe_length": SERVICE_PROBE_LENGTH_MM,
                "service_probe_height": SERVICE_PROBE_HEIGHT_MM,
                "service_probe_nominal_gap": SERVICE_PROBE_NOMINAL_GAP_MM,
                "service_probe_hostile_overtravel": SERVICE_PROBE_MM,
            },
            "measured": {
                "positive_source_mate_capture_mm3": self.source_mate_intersection_mm3,
                "nominal_service_probe_intersection_mm3": self.nominal_service_probe_intersection_mm3,
                "hostile_service_stop_intersection_mm3": self.hostile_stop_intersection_mm3,
            },
        }


@dataclass(frozen=True, slots=True)
class StructuralFrameCarrierInterfaceArchitecture:
    source_mate_architecture_sha256: str
    interfaces: tuple[CarrierInterface, ...]
    physical_validation_eligible: bool = False

    def __post_init__(self) -> None:
        if len(self.source_mate_architecture_sha256) != 64:
            raise StructuralFrameCarrierInterfaceError("source mate identity must be SHA-256")
        if tuple(i.reaction_id for i in self.interfaces) != REACTION_IDS:
            raise StructuralFrameCarrierInterfaceError("all four carrier interfaces must exist in controlled order")
        if self.physical_validation_eligible is not False:
            raise StructuralFrameCarrierInterfaceError("digital carrier interface geometry is not physical evidence")

    @property
    def architecture_sha256(self) -> str:
        raw = json.dumps(self.manifest(include_sha=False), sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        return hashlib.sha256(raw).hexdigest()

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema": SCHEMA,
            "source_mate_architecture_sha256": self.source_mate_architecture_sha256,
            "coordinate_frame_id": WORLD_FRAME_ID,
            "interfaces": [i.manifest() for i in self.interfaces],
            "carrier_counterpart_status": "EXPLICIT_FRAME_SIDE_RAILS_REALIZED_CELL7_FEMALE_COUNTERPART_OPEN",
            "service_status": "OPEN_ENTRY_AND_INDEPENDENT_POSITIVE_END_STOP_PROBE_REALIZED_CONTINUOUS_WHOLE_CARRIER_SWEEP_OPEN",
            "physical_validation_eligible": self.physical_validation_eligible,
        }
        if include_sha:
            payload["architecture_sha256"] = self.architecture_sha256
        return payload


def _rail_components(cx: float, cy: float, z0: float) -> tuple[cq.Workplane, cq.Workplane]:
    root = cq.Workplane("XY").box(RAIL_ROOT_WIDTH_MM, RAIL_LENGTH_MM, RAIL_HEIGHT_MM * 0.55, centered=(True, True, False)).translate((cx, cy, z0))
    crown = cq.Workplane("XY").box(RAIL_CROWN_WIDTH_MM, RAIL_LENGTH_MM - ENTRY_RELIEF_MM, RAIL_HEIGHT_MM * 0.45, centered=(True, True, False)).translate((cx, cy - ENTRY_RELIEF_MM / 2.0, z0 + RAIL_HEIGHT_MM * 0.55))
    stop = cq.Workplane("XY").box(RAIL_CROWN_WIDTH_MM, END_STOP_THICKNESS_MM, END_STOP_HEIGHT_MM, centered=(True, True, False)).translate((cx, cy - RAIL_LENGTH_MM / 2.0 + END_STOP_THICKNESS_MM / 2.0, z0))
    return root.union(crown).union(stop), stop


def _service_stop_probe(cx: float, cy: float, z0: float) -> cq.Workplane:
    stop_inner_y = cy - RAIL_LENGTH_MM / 2.0 + END_STOP_THICKNESS_MM
    probe_center_y = stop_inner_y + SERVICE_PROBE_NOMINAL_GAP_MM + SERVICE_PROBE_LENGTH_MM / 2.0
    return cq.Workplane("XY").box(
        SERVICE_PROBE_WIDTH_MM,
        SERVICE_PROBE_LENGTH_MM,
        SERVICE_PROBE_HEIGHT_MM,
        centered=(True, True, False),
    ).translate((cx, probe_center_y, z0 + RAIL_HEIGHT_MM))


def build_structural_frame_carrier_interfaces(*, mates: StructuralFrameActuatorMateArchitecture | None = None) -> StructuralFrameCarrierInterfaceArchitecture:
    mates = build_structural_frame_actuator_mates() if mates is None else mates
    built: list[CarrierInterface] = []
    for source in mates.mates:
        bb = source.mate.val().BoundingBox()
        cx, cy = source.center_xy_mm
        z0 = float(bb.zmax) - 0.20
        interface, stop = _rail_components(cx, cy, z0)
        _valid_single_solid(interface, source.reaction_id)
        capture = _intersection_volume(interface, source.mate)
        probe = _service_stop_probe(cx, cy, z0)
        nominal_probe_intersection = _intersection_volume(probe, stop)
        hostile_probe_intersection = _intersection_volume(probe.translate((0.0, -SERVICE_PROBE_MM, 0.0)), stop)
        built.append(CarrierInterface(
            source.reaction_id,
            source.center_xy_mm,
            interface,
            round(capture, 8),
            round(nominal_probe_intersection, 8),
            round(hostile_probe_intersection, 8),
        ))
    result = StructuralFrameCarrierInterfaceArchitecture(mates.architecture_sha256, tuple(built), False)
    result.__post_init__()
    return result


def export_structural_frame_carrier_interfaces(output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    architecture = build_structural_frame_carrier_interfaces()
    for item in architecture.interfaces:
        cq.exporters.export(item.interface, str(output_dir / f"{item.reaction_id.lower()}_carrier_interface.step"))
    manifest = architecture.manifest()
    (output_dir / "structural_frame_carrier_interfaces_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest
