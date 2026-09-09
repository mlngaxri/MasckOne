from __future__ import annotations

"""Axis-specific fixed-guided spring-insert package for terminal treatment datum preload.

This module packages the analytical parallel-leaf solution as real reference B-reps.
It deliberately does NOT promote the inserts to released carrier material yet. The
intent is insert-mold / captured spring architecture:

carrier polymer anchor capture -> two parallel spring leaves -> tip bridge embedded
in the terminal polymer cam shoe.

The leaves provide preload only. Rigid master datums remain the normal 40 Hz working
reaction path. A polymer/engineering shoe, not bare spring metal, remains the datum
contact surface. Exact capture pockets, insert-molding process, grade, damping and
fatigue remain open.
"""

from dataclasses import dataclass, field
import hashlib
import json
import math
from pathlib import Path

import cadquery as cq
from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism
from OCP.gp import gp_Vec

from .model import MasckOneModel, build_model
from .structural_frame_actuator_mates import (
    StructuralFrameActuatorMateArchitecture,
    build_structural_frame_actuator_mates,
)
from .structural_frame_actuator_reactions import (
    REACTION_IDS,
    StructuralFrameActuatorReactionArchitecture,
    build_structural_frame_actuator_reactions,
)
from .treatment_mounted_four_zone_v2 import build_mounted_four_zone_architecture_v2
from .treatment_terminal_datum_preload import (
    TerminalDatumPreloadArchitecture,
    build_terminal_datum_preload_architecture,
)

SCHEMA = "MASCK_ONE_TREATMENT_TERMINAL_PARALLEL_PRELOAD_INSERT_V1"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"
SOURCE_TREATMENT_PARALLEL_STUDY_SHA = "83c22492fa4ab63d501b74c6680c46712c1582c2"

E_STUDY_MPA = 190000.0
SHEET_THICKNESS_MM = 0.12
LEAF_WIDTH_MM = 0.65
FULL_SEAT_PRELOAD_N = 0.30
ENTRY_OVERCLOSURE_MM = 0.005
AXIS_CLEARANCE_MM = {"X": 0.16, "Z": 0.12}

LEAF_SEPARATION_MM = 0.45
ANCHOR_BRIDGE_Y_MM = 0.50
TIP_BRIDGE_Y_MM = 0.42
TIP_EMBED_Y_MM = 0.16
ANCHOR_CAPTURE_Y_MM = 0.18
SERVICE_RETRACTION_PROBE_MM = 2.0
_INTERSECTION_TOLERANCE_MM3 = 1e-7


class TreatmentTerminalParallelPreloadInsertError(ValueError):
    pass


def _required_length(axis: str) -> float:
    clearance = AXIS_CLEARANCE_MM[axis]
    delta = clearance + ENTRY_OVERCLOSURE_MM
    k = FULL_SEAT_PRELOAD_N / delta
    numerator = 2.0 * E_STUDY_MPA * LEAF_WIDTH_MM * SHEET_THICKNESS_MM**3
    return (numerator / k) ** (1.0 / 3.0)


def _box(x: float, y: float, z: float, center: tuple[float, float, float]) -> cq.Shape:
    if min(x, y, z) <= 0.0:
        raise TreatmentTerminalParallelPreloadInsertError("box dimensions must be positive")
    return cq.Workplane("XY").box(x, y, z).translate(center).val()


def _join(shapes: list[cq.Shape]) -> cq.Shape:
    if not shapes:
        raise TreatmentTerminalParallelPreloadInsertError("empty spring insert")
    result = shapes[0]
    for shape in shapes[1:]:
        result = result.fuse(shape)
    result = result.clean()
    if not result.isValid() or len(result.Solids()) != 1 or result.Volume() <= 0.0:
        raise TreatmentTerminalParallelPreloadInsertError("spring insert must be one valid solid")
    return result


def _iv(a: cq.Shape, b: cq.Shape) -> float:
    aa, bb = a.BoundingBox(), b.BoundingBox()
    if (
        aa.xmax < bb.xmin or bb.xmax < aa.xmin
        or aa.ymax < bb.ymin or bb.ymax < aa.ymin
        or aa.zmax < bb.zmin or bb.zmax < aa.zmin
    ):
        return 0.0
    try:
        common = a.intersect(b)
    except Exception as exc:
        raise TreatmentTerminalParallelPreloadInsertError("intersection kernel failure") from exc
    if not common.isValid():
        raise TreatmentTerminalParallelPreloadInsertError("invalid intersection result")
    value = sum(max(0.0, float(s.Volume())) for s in common.Solids())
    if not math.isfinite(value):
        raise TreatmentTerminalParallelPreloadInsertError("nonfinite intersection")
    return value


def _translation_envelope(shape: cq.Shape, travel: tuple[float, float, float]) -> cq.Shape:
    pieces: list[cq.Shape] = [shape, shape.translate(travel)]
    for face in shape.Faces():
        prism = cq.Shape.cast(BRepPrimAPI_MakePrism(face.wrapped, gp_Vec(*travel)).Shape())
        pieces.extend(prism.Solids())
    compound = cq.Compound.makeCompound(pieces)
    if not compound.isValid():
        raise TreatmentTerminalParallelPreloadInsertError("invalid service envelope")
    return compound


def _x_insert(preload_shoe: cq.Shape) -> cq.Shape:
    bb = preload_shoe.BoundingBox()
    length = _required_length("X")
    x = 0.5 * (bb.xmin + bb.xmax)
    z_mid = 0.5 * (bb.zmin + bb.zmax)
    tip_y = bb.ymin + TIP_EMBED_Y_MM
    anchor_y = tip_y - length
    z_sep = 0.5 * (LEAF_WIDTH_MM + LEAF_SEPARATION_MM)
    leaves = [
        _box(
            SHEET_THICKNESS_MM,
            length,
            LEAF_WIDTH_MM,
            (x, 0.5 * (anchor_y + tip_y), z_mid - z_sep),
        ),
        _box(
            SHEET_THICKNESS_MM,
            length,
            LEAF_WIDTH_MM,
            (x, 0.5 * (anchor_y + tip_y), z_mid + z_sep),
        ),
    ]
    total_z = 2.0 * LEAF_WIDTH_MM + LEAF_SEPARATION_MM
    anchor = _box(
        SHEET_THICKNESS_MM,
        ANCHOR_BRIDGE_Y_MM,
        total_z,
        (x, anchor_y + ANCHOR_BRIDGE_Y_MM / 2.0, z_mid),
    )
    tip = _box(
        SHEET_THICKNESS_MM,
        TIP_BRIDGE_Y_MM,
        total_z,
        (x, tip_y - TIP_BRIDGE_Y_MM / 2.0, z_mid),
    )
    return _join([anchor, *leaves, tip])


def _z_insert(preload_shoe: cq.Shape) -> cq.Shape:
    bb = preload_shoe.BoundingBox()
    length = _required_length("Z")
    x_mid = 0.5 * (bb.xmin + bb.xmax)
    z = 0.5 * (bb.zmin + bb.zmax)
    tip_y = bb.ymin + TIP_EMBED_Y_MM
    anchor_y = tip_y - length
    x_sep = 0.5 * (LEAF_WIDTH_MM + LEAF_SEPARATION_MM)
    leaves = [
        _box(
            LEAF_WIDTH_MM,
            length,
            SHEET_THICKNESS_MM,
            (x_mid - x_sep, 0.5 * (anchor_y + tip_y), z),
        ),
        _box(
            LEAF_WIDTH_MM,
            length,
            SHEET_THICKNESS_MM,
            (x_mid + x_sep, 0.5 * (anchor_y + tip_y), z),
        ),
    ]
    total_x = 2.0 * LEAF_WIDTH_MM + LEAF_SEPARATION_MM
    anchor = _box(
        total_x,
        ANCHOR_BRIDGE_Y_MM,
        SHEET_THICKNESS_MM,
        (x_mid, anchor_y + ANCHOR_BRIDGE_Y_MM / 2.0, z),
    )
    tip = _box(
        total_x,
        TIP_BRIDGE_Y_MM,
        SHEET_THICKNESS_MM,
        (x_mid, tip_y - TIP_BRIDGE_Y_MM / 2.0, z),
    )
    return _join([anchor, *leaves, tip])


@dataclass(frozen=True, slots=True)
class ParallelPreloadInsertStation:
    reaction_id: str
    center_xy_mm: tuple[float, float]
    x_insert: cq.Shape = field(repr=False, compare=False)
    z_insert: cq.Shape = field(repr=False, compare=False)
    service_sweep: cq.Shape = field(repr=False, compare=False)
    x_tip_shoe_capture_overlap_mm3: float
    z_tip_shoe_capture_overlap_mm3: float
    x_anchor_backbone_overlap_mm3: float
    z_anchor_backbone_overlap_mm3: float
    source_intersection_mm3: float
    service_source_intersection_mm3: float

    def __post_init__(self) -> None:
        if self.reaction_id not in REACTION_IDS:
            raise TreatmentTerminalParallelPreloadInsertError("unknown reaction id")
        for shape in (self.x_insert, self.z_insert):
            if not shape.isValid() or len(shape.Solids()) != 1 or shape.Volume() <= 0.0:
                raise TreatmentTerminalParallelPreloadInsertError("invalid spring insert solid")
        if self.x_tip_shoe_capture_overlap_mm3 <= _INTERSECTION_TOLERANCE_MM3:
            raise TreatmentTerminalParallelPreloadInsertError("X insert lacks positive tip capture reference")
        if self.z_tip_shoe_capture_overlap_mm3 <= _INTERSECTION_TOLERANCE_MM3:
            raise TreatmentTerminalParallelPreloadInsertError("Z insert lacks positive tip capture reference")
        if self.x_anchor_backbone_overlap_mm3 <= _INTERSECTION_TOLERANCE_MM3:
            raise TreatmentTerminalParallelPreloadInsertError("X insert lacks positive carrier anchor capture reference")
        if self.z_anchor_backbone_overlap_mm3 <= _INTERSECTION_TOLERANCE_MM3:
            raise TreatmentTerminalParallelPreloadInsertError("Z insert lacks positive carrier anchor capture reference")
        if self.source_intersection_mm3 > _INTERSECTION_TOLERANCE_MM3:
            raise TreatmentTerminalParallelPreloadInsertError("spring insert intersects Cell 6 source material")
        if self.service_source_intersection_mm3 > _INTERSECTION_TOLERANCE_MM3:
            raise TreatmentTerminalParallelPreloadInsertError("spring insert blocks +Y service retraction")

    def manifest(self) -> dict[str, object]:
        return {
            "reaction_id": self.reaction_id,
            "coordinate_frame_id": WORLD_FRAME_ID,
            "architecture": "TWO_AXIS_SPECIFIC_FIXED_GUIDED_PARALLEL_LEAF_INSERTS_WITH_POLYMER_SHOE_TIP_CAPTURE",
            "working_load_rule": "INSERTS_PRELOAD_ONLY; RIGID_MASTER_DATUMS_CARRY_NORMAL_40HZ_REACTION",
            "x_leaf_length_mm": _required_length("X"),
            "z_leaf_length_mm": _required_length("Z"),
            "sheet_thickness_mm": SHEET_THICKNESS_MM,
            "leaf_width_mm": LEAF_WIDTH_MM,
            "leaf_separation_mm": LEAF_SEPARATION_MM,
            "measured": {
                "x_tip_shoe_capture_overlap_mm3": self.x_tip_shoe_capture_overlap_mm3,
                "z_tip_shoe_capture_overlap_mm3": self.z_tip_shoe_capture_overlap_mm3,
                "x_anchor_backbone_overlap_mm3": self.x_anchor_backbone_overlap_mm3,
                "z_anchor_backbone_overlap_mm3": self.z_anchor_backbone_overlap_mm3,
                "source_intersection_mm3": self.source_intersection_mm3,
                "service_source_intersection_mm3": self.service_source_intersection_mm3,
            },
            "capture_semantics": (
                "OVERLAPS_ARE_INSERT_MOLD_OR_CAPTURE_POCKET_REFERENCES_ONLY; FINAL MULTIMATERIAL_VOLUMES_MUST_NOT_OVERLAP"
            ),
            "damping_semantics": (
                "NONFLEXING_ANCHOR_BORDER_REQUIRES_LOSSY_POLYMER_CAPTURE; FREE LEAF SPANS MUST NOT BE BONDED_OR_RUB"
            ),
            "physical_validation": (
                "OPEN_SPRING_GRADE_FORMING_INSERT_CAPTURE_DAMPING_FATIGUE_FORCE_TRAVEL_FRICTION_WEAR_"
                "ACOUSTICS_WET_CONTAMINATION_AND_PROCESS_CAPABILITY"
            ),
        }


@dataclass(frozen=True, slots=True)
class ParallelPreloadInsertArchitecture:
    stations: tuple[ParallelPreloadInsertStation, ...]
    physical_validation_eligible: bool = False

    def __post_init__(self) -> None:
        if tuple(item.reaction_id for item in self.stations) != REACTION_IDS:
            raise TreatmentTerminalParallelPreloadInsertError("all four station insert packages required")
        if self.physical_validation_eligible:
            raise TreatmentTerminalParallelPreloadInsertError("digital insert package is not physical validation")

    @property
    def architecture_sha256(self) -> str:
        raw = json.dumps(self.manifest(False), sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        return hashlib.sha256(raw).hexdigest()

    def manifest(self, include_sha: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema": SCHEMA,
            "source_treatment_parallel_study_sha": SOURCE_TREATMENT_PARALLEL_STUDY_SHA,
            "coordinate_frame_id": WORLD_FRAME_ID,
            "stations": [item.manifest() for item in self.stations],
            "material_status": "REFERENCE_PACKAGE_NOT_YET_PROMOTED_TO_MULTIMATERIAL_CARRIER_BREP",
            "physical_validation_eligible": self.physical_validation_eligible,
        }
        if include_sha:
            payload["architecture_sha256"] = self.architecture_sha256
        return payload


def build_parallel_preload_insert_architecture(
    *,
    model: MasckOneModel | None = None,
    reactions: StructuralFrameActuatorReactionArchitecture | None = None,
    mates: StructuralFrameActuatorMateArchitecture | None = None,
    terminal_datums: TerminalDatumPreloadArchitecture | None = None,
) -> ParallelPreloadInsertArchitecture:
    model = build_model() if model is None else model
    reactions = build_structural_frame_actuator_reactions(model=model) if reactions is None else reactions
    mates = build_structural_frame_actuator_mates(model=model, reactions=reactions) if mates is None else mates
    terminal_datums = (
        build_terminal_datum_preload_architecture(model=model, reactions=reactions, mates=mates)
        if terminal_datums is None
        else terminal_datums
    )
    mounted_v2 = build_mounted_four_zone_architecture_v2(model=model, reactions=reactions, mates=mates)
    backbone_map = {item.reaction_id: dict(item.material_parts)["fixed_backbone"] for item in mounted_v2.stations}
    mate_map = {item.reaction_id: item.mate.val() for item in mates.mates}

    built: list[ParallelPreloadInsertStation] = []
    for datum in terminal_datums.stations:
        preload = dict(datum.preload_installed_parts)
        x_shoe = preload["preload_x_installed"]
        z_shoe = preload["preload_z_installed"]
        x_insert = _x_insert(x_shoe)
        z_insert = _z_insert(z_shoe)
        backbone = backbone_map[datum.reaction_id]
        source = mate_map[datum.reaction_id]

        # Only a small front strip of each insert is intended to be embedded in the
        # polymer follower shoe; the remainder must be free flexure material.
        x_tip_capture = _iv(x_insert, x_shoe)
        z_tip_capture = _iv(z_insert, z_shoe)
        x_anchor_capture = _iv(x_insert, backbone)
        z_anchor_capture = _iv(z_insert, backbone)
        insert_compound = cq.Compound.makeCompound([x_insert, z_insert])
        source_iv = _iv(insert_compound, source)
        service = _translation_envelope(insert_compound, (0.0, SERVICE_RETRACTION_PROBE_MM, 0.0))
        service_iv = _iv(service, source)
        built.append(
            ParallelPreloadInsertStation(
                datum.reaction_id,
                datum.center_xy_mm,
                x_insert,
                z_insert,
                service,
                round(x_tip_capture, 8),
                round(z_tip_capture, 8),
                round(x_anchor_capture, 8),
                round(z_anchor_capture, 8),
                round(source_iv, 8),
                round(service_iv, 8),
            )
        )

    result = ParallelPreloadInsertArchitecture(tuple(built), False)
    result.__post_init__()
    return result


def export_parallel_preload_insert_architecture(output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    architecture = build_parallel_preload_insert_architecture()
    for station in architecture.stations:
        slug = station.reaction_id.lower()
        cq.exporters.export(station.x_insert, str(output_dir / f"{slug}_x_parallel_preload_insert.step"))
        cq.exporters.export(station.z_insert, str(output_dir / f"{slug}_z_parallel_preload_insert.step"))
        cq.exporters.export(station.service_sweep, str(output_dir / f"{slug}_parallel_preload_service_sweep.step"))
    manifest = architecture.manifest()
    (output_dir / "treatment_terminal_parallel_preload_insert_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest
