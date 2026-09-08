from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import math
from pathlib import Path

import cadquery as cq

from .model import MasckOneModel, build_model
from .structural_frame_actuator_reactions import (
    KEY_DEPTH_MM,
    KEY_WIDTH_MM,
    REACTION_IDS,
    SOCKET_DEPTH_MM,
    SOCKET_HEIGHT_MM,
    SOCKET_WIDTH_MM,
    StructuralFrameActuatorReactionArchitecture,
    build_structural_frame_actuator_reactions,
)
from .structural_frame_realization import _protected_zone_solid

SCHEMA = "MASCK_ONE_STRUCTURAL_FRAME_ACTUATOR_MATES_V1"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"

# Digital MVP geometry seeds only. They establish a real keyed counterpart and
# compliant bridge B-rep. They are not production tolerances or stiffness evidence.
RADIAL_CLEARANCE_MM = 0.15
AXIAL_CLEARANCE_MM = 0.10
SHOULDER_GAP_MM = 0.10
SHOULDER_WIDTH_MM = 8.0
SHOULDER_HEIGHT_MM = 8.0
SHOULDER_THICKNESS_MM = 0.80
FLEXURE_WIDTH_MM = 3.0
FLEXURE_HEIGHT_MM = 6.0
FLEXURE_THICKNESS_MM = 0.60
FLEXURE_SPAN_MM = 2.40
CARRIER_PAD_WIDTH_MM = 8.0
CARRIER_PAD_HEIGHT_MM = 8.0
CARRIER_PAD_THICKNESS_MM = 1.00
OVERTRAVEL_PROBE_MM = 0.25
_INTERSECTION_TOLERANCE_MM3 = 1e-7


class StructuralFrameActuatorMateError(ValueError):
    pass


def _intersection_volume(a: cq.Workplane, b: cq.Workplane) -> float:
    try:
        return max(0.0, float(a.intersect(b).val().Volume()))
    except Exception:
        return 0.0


def _valid_single_solid(shape: cq.Workplane, label: str) -> None:
    value = shape.val()
    if not value.isValid() or len(value.Solids()) != 1 or float(value.Volume()) <= 0.0:
        raise StructuralFrameActuatorMateError(f"{label} must be one valid positive-volume B-rep solid")


@dataclass(frozen=True, slots=True)
class ActuatorReactionMate:
    reaction_id: str
    center_xy_mm: tuple[float, float]
    nominal_frame_intersection_mm3: float
    protected_intersection_mm3: float
    overtravel_stop_intersection_mm3: float
    mate: cq.Workplane = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.reaction_id not in REACTION_IDS:
            raise StructuralFrameActuatorMateError("unknown actuator reaction mate")
        if len(self.center_xy_mm) != 2 or not all(math.isfinite(float(v)) for v in self.center_xy_mm):
            raise StructuralFrameActuatorMateError("mate center must be finite XY")
        _valid_single_solid(self.mate, self.reaction_id)
        if self.nominal_frame_intersection_mm3 > _INTERSECTION_TOLERANCE_MM3:
            raise StructuralFrameActuatorMateError("nominal actuator mate intersects frame material")
        if self.protected_intersection_mm3 > _INTERSECTION_TOLERANCE_MM3:
            raise StructuralFrameActuatorMateError("actuator mate intersects a hard protected envelope")
        if self.overtravel_stop_intersection_mm3 <= _INTERSECTION_TOLERANCE_MM3:
            raise StructuralFrameActuatorMateError("actuator mate lacks a positive axial shoulder stop")

    def manifest(self) -> dict[str, object]:
        return {
            "reaction_id": self.reaction_id,
            "coordinate_frame_id": WORLD_FRAME_ID,
            "center_xy_mm": list(self.center_xy_mm),
            "interface_semantics": "KEYED_MALE_REACTION_SHOE_WITH_SHOULDER_STOP_AND_COMPLIANT_BRIDGE",
            "dimensions_mm": {
                "radial_clearance_seed": RADIAL_CLEARANCE_MM,
                "axial_clearance_seed": AXIAL_CLEARANCE_MM,
                "shoulder_gap_seed": SHOULDER_GAP_MM,
                "shoulder_width": SHOULDER_WIDTH_MM,
                "shoulder_height": SHOULDER_HEIGHT_MM,
                "shoulder_thickness": SHOULDER_THICKNESS_MM,
                "flexure_width": FLEXURE_WIDTH_MM,
                "flexure_height": FLEXURE_HEIGHT_MM,
                "flexure_thickness": FLEXURE_THICKNESS_MM,
                "flexure_span": FLEXURE_SPAN_MM,
                "carrier_pad_width": CARRIER_PAD_WIDTH_MM,
                "carrier_pad_height": CARRIER_PAD_HEIGHT_MM,
                "carrier_pad_thickness": CARRIER_PAD_THICKNESS_MM,
            },
            "measured": {
                "nominal_frame_intersection_mm3": self.nominal_frame_intersection_mm3,
                "protected_intersection_mm3": self.protected_intersection_mm3,
                "overtravel_stop_intersection_mm3": self.overtravel_stop_intersection_mm3,
            },
        }


@dataclass(frozen=True, slots=True)
class StructuralFrameActuatorMateArchitecture:
    source_reaction_architecture_sha256: str
    mates: tuple[ActuatorReactionMate, ...]
    physical_validation_eligible: bool = False

    def __post_init__(self) -> None:
        if len(self.source_reaction_architecture_sha256) != 64:
            raise StructuralFrameActuatorMateError("source reaction identity must be SHA-256")
        if tuple(m.reaction_id for m in self.mates) != REACTION_IDS:
            raise StructuralFrameActuatorMateError("all four reaction mates must exist in controlled order")
        if self.physical_validation_eligible is not False:
            raise StructuralFrameActuatorMateError("digital mate geometry is not physical validation evidence")

    @property
    def architecture_sha256(self) -> str:
        raw = json.dumps(self.manifest(include_sha=False), sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def manifest(self, *, include_sha: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema": SCHEMA,
            "source_reaction_architecture_sha256": self.source_reaction_architecture_sha256,
            "coordinate_frame_id": WORLD_FRAME_ID,
            "mates": [m.manifest() for m in self.mates],
            "coupling_status": "FOUR_KEYED_REACTION_MATES_AND_COMPLIANT_BRIDGES_REALIZED_CARRIER_BODY_MATING_OPEN",
            "production_tolerance_status": "NOMINAL_DIGITAL_CLEARANCE_SEEDS_ONLY",
            "physical_validation_eligible": self.physical_validation_eligible,
        }
        if include_sha:
            payload["architecture_sha256"] = self.architecture_sha256
        return payload


def _build_mate(cx: float, cy: float, z_max: float) -> cq.Workplane:
    key_w = SOCKET_WIDTH_MM - 2.0 * RADIAL_CLEARANCE_MM
    key_h = SOCKET_HEIGHT_MM - 2.0 * RADIAL_CLEARANCE_MM
    key_depth = SOCKET_DEPTH_MM - AXIAL_CLEARANCE_MM
    key = (
        cq.Workplane("XY")
        .box(key_w, key_h, key_depth, centered=(True, True, True))
        .translate((cx, cy, z_max - key_depth / 2.0))
    )
    tooth_w = max(0.20, KEY_WIDTH_MM - 2.0 * RADIAL_CLEARANCE_MM)
    tooth_h = SOCKET_HEIGHT_MM / 2.0 - 2.0 * RADIAL_CLEARANCE_MM
    tooth_depth = max(0.20, KEY_DEPTH_MM - AXIAL_CLEARANCE_MM)
    tooth = (
        cq.Workplane("XY")
        .box(tooth_w, tooth_h, tooth_depth, centered=(True, True, True))
        .translate((cx + SOCKET_WIDTH_MM / 2.0 - KEY_WIDTH_MM / 2.0, cy, z_max - tooth_depth / 2.0))
    )
    shoulder_z0 = z_max + SHOULDER_GAP_MM
    shoulder = (
        cq.Workplane("XY")
        .box(SHOULDER_WIDTH_MM, SHOULDER_HEIGHT_MM, SHOULDER_THICKNESS_MM, centered=(True, True, False))
        .translate((cx, cy, shoulder_z0))
    )
    bridge_z0 = shoulder_z0 + SHOULDER_THICKNESS_MM
    bridge = (
        cq.Workplane("XY")
        .box(FLEXURE_WIDTH_MM, FLEXURE_HEIGHT_MM, FLEXURE_SPAN_MM, centered=(True, True, False))
        .translate((cx, cy, bridge_z0))
    )
    pad_z0 = bridge_z0 + FLEXURE_SPAN_MM
    pad = (
        cq.Workplane("XY")
        .box(CARRIER_PAD_WIDTH_MM, CARRIER_PAD_HEIGHT_MM, CARRIER_PAD_THICKNESS_MM, centered=(True, True, False))
        .translate((cx, cy, pad_z0))
    )
    return key.union(tooth).union(shoulder).union(bridge).union(pad)


def build_structural_frame_actuator_mates(
    *,
    model: MasckOneModel | None = None,
    reactions: StructuralFrameActuatorReactionArchitecture | None = None,
) -> StructuralFrameActuatorMateArchitecture:
    model = build_model() if model is None else model
    reactions = build_structural_frame_actuator_reactions(model=model) if reactions is None else reactions
    frame = reactions.frame_with_reaction_counterparts
    z_max = float(frame.val().BoundingBox().zmax)
    z_min = float(frame.val().BoundingBox().zmin)

    mates: list[ActuatorReactionMate] = []
    for reaction in reactions.reactions:
        cx, cy = reaction.center_xy_mm
        mate = _build_mate(cx, cy, z_max)
        _valid_single_solid(mate, reaction.reaction_id)
        nominal = _intersection_volume(mate, frame)

        protected = 0.0
        for item in model.protected_volumes.all:
            zone = item.zone
            keepout = _protected_zone_solid(
                center_x_mm=zone.center.x,
                center_y_mm=zone.center.y,
                envelope_width_mm=zone.envelope_width_mm,
                envelope_height_mm=zone.envelope_height_mm,
                angle_deg=zone.angle_deg,
                z_min_mm=z_min - 1.0,
                z_max_mm=float(mate.val().BoundingBox().zmax) + 1.0,
            )
            protected += _intersection_volume(mate, keepout)

        overtravel = _intersection_volume(mate.translate((0.0, 0.0, -OVERTRAVEL_PROBE_MM)), frame)
        mates.append(
            ActuatorReactionMate(
                reaction_id=reaction.reaction_id,
                center_xy_mm=reaction.center_xy_mm,
                nominal_frame_intersection_mm3=round(nominal, 8),
                protected_intersection_mm3=round(protected, 8),
                overtravel_stop_intersection_mm3=round(overtravel, 8),
                mate=mate,
            )
        )

    result = StructuralFrameActuatorMateArchitecture(
        source_reaction_architecture_sha256=reactions.architecture_sha256,
        mates=tuple(mates),
        physical_validation_eligible=False,
    )
    result.__post_init__()
    return result


def export_structural_frame_actuator_mates(output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    architecture = build_structural_frame_actuator_mates()
    for mate in architecture.mates:
        path = output_dir / f"{mate.reaction_id.lower()}_reaction_mate.step"
        cq.exporters.export(mate.mate, str(path))
    manifest = architecture.manifest()
    (output_dir / "structural_frame_actuator_mates_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest
