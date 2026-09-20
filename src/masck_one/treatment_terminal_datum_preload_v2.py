from __future__ import annotations

"""Terminal datum/preload V2: robust phased C2 acquisition geometry.

This is the geometric embodiment of ``studies/treatment_buttery_terminal_profile_v2``.
It supersedes the V1 cubic, simultaneous X/Z terminal cam as the preferred digital
candidate while preserving the same separation of functions:

- the long Cell 6 rail keeps generous running clearance;
- rigid X/Z master datums define the seated coordinate and carry normal 40 Hz load;
- the opposite preload shoes only maintain contact against those datums;
- X play is removed slightly before Z so both spring/cam reactions do not peak at the
  same insertion coordinate;
- both axes reach a flat full-preload land before the axial landing/detent event;
- lossy backups precede rigid abnormal-load stops.

The terminal cam intent is quintic C2 smootherstep. CadQuery represents the contact
edge with a fitted spline through deterministic samples. Surface finish, friction,
contact pressure, force, sound and production tolerance capability remain physical/
manufacturing validation gates.
"""

from dataclasses import dataclass, field
import hashlib
import json
import math
from pathlib import Path

import cadquery as cq
from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism
from OCP.gp import gp_Vec

from studies.treatment_buttery_terminal_profile_v2 import (
    CAM_TRAVEL_MM,
    FULL_SEAT_LAND_MM,
    X_CAM_PHASE_LEAD_MM,
    X_CLEARANCE_MM,
    Z_CLEARANCE_MM,
    smootherstep,
)

from .model import MasckOneModel, build_model
from .structural_frame_actuator_mates import (
    REACTION_IDS,
    SHOULDER_GAP_MM,
    SHOULDER_HEIGHT_MM,
    SHOULDER_THICKNESS_MM,
    SHOULDER_WIDTH_MM,
    StructuralFrameActuatorMateArchitecture,
    build_structural_frame_actuator_mates,
)
from .structural_frame_actuator_reactions import (
    StructuralFrameActuatorReactionArchitecture,
    build_structural_frame_actuator_reactions,
)

SCHEMA = "MASCK_ONE_TREATMENT_TERMINAL_DATUM_PRELOAD_V2"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"
SOURCE_CELL6_HEAD_SHA = "fcccde02b31cc1c4e01136630d92e550e4e09a11"

POSTERIOR_EXTENSION_MM = 0.08
PROFILE_SAMPLES = 17

MASTER_X_DEPTH_MM = 0.30
MASTER_X_Z_SPAN_MM = 2.40
MASTER_Z_DEPTH_MM = 0.30
MASTER_Z_X_SPAN_MM = 1.00
PRELOAD_X_DEPTH_MM = 0.30
PRELOAD_X_Z_SPAN_MM = 1.60
PRELOAD_Z_DEPTH_MM = 0.30
PRELOAD_Z_X_SPAN_MM = 1.20

LOSSY_BACKUP_GAP_MM = 0.04
BACKUP_BUMPER_THICKNESS_MM = 0.05
RIGID_BACKUP_THICKNESS_MM = 0.30
TERMINAL_SERVICE_RETRACTION_PROBE_MM = 2.0
MASTER_ENGAGEMENT_PROBE_MM = 0.03
_INTERSECTION_TOLERANCE_MM3 = 1e-7


class TreatmentTerminalDatumPreloadV2Error(ValueError):
    pass


def _intersection_volume(a: cq.Shape, b: cq.Shape) -> float:
    aa, bb = a.BoundingBox(), b.BoundingBox()
    if (
        aa.xmax < bb.xmin
        or bb.xmax < aa.xmin
        or aa.ymax < bb.ymin
        or bb.ymax < aa.ymin
        or aa.zmax < bb.zmin
        or bb.zmax < aa.zmin
    ):
        return 0.0
    try:
        common = a.intersect(b)
    except Exception as exc:
        raise TreatmentTerminalDatumPreloadV2Error("intersection kernel failure") from exc
    if not common.isValid():
        raise TreatmentTerminalDatumPreloadV2Error("invalid intersection result")
    value = sum(max(0.0, float(s.Volume())) for s in common.Solids())
    if not math.isfinite(value):
        raise TreatmentTerminalDatumPreloadV2Error("nonfinite intersection result")
    return value


def _join(shapes: list[cq.Shape]) -> cq.Shape:
    if not shapes:
        raise TreatmentTerminalDatumPreloadV2Error("cannot join empty geometry")
    result = shapes[0]
    for shape in shapes[1:]:
        result = result.fuse(shape)
    result = result.clean()
    if not result.isValid() or not result.Solids():
        raise TreatmentTerminalDatumPreloadV2Error("joined geometry must remain valid positive material")
    return result


def _translation_envelope(shape: cq.Shape, travel: tuple[float, float, float]) -> cq.Shape:
    pieces: list[cq.Shape] = [shape, shape.translate(travel)]
    for face in shape.Faces():
        prism = cq.Shape.cast(BRepPrimAPI_MakePrism(face.wrapped, gp_Vec(*travel)).Shape())
        pieces.extend(prism.Solids())
    return _join(pieces)


def _box(x: float, y: float, z: float, center: tuple[float, float, float]) -> cq.Shape:
    if min(x, y, z) <= 0.0:
        raise TreatmentTerminalDatumPreloadV2Error("box dimensions must be positive")
    return cq.Workplane("XY").box(x, y, z).translate(center).val()


def _profile_y_points(
    *,
    contact_y: float,
    clearance_mm: float,
    phase_lead_mm: float,
) -> list[tuple[float, float]]:
    land_start = contact_y - FULL_SEAT_LAND_MM - phase_lead_mm
    start = land_start - CAM_TRAVEL_MM
    rows: list[tuple[float, float]] = []
    for index in range(PROFILE_SAMPLES):
        s = index / (PROFILE_SAMPLES - 1)
        y = start + CAM_TRAVEL_MM * s
        gap = clearance_mm * (1.0 - smootherstep(s))
        rows.append((y, gap))
    rows.append((contact_y + POSTERIOR_EXTENSION_MM, 0.0))
    return rows


def _x_cam_pad(
    *,
    cx: float,
    contact_y: float,
    side_sign: float,
    clearance_mm: float,
    phase_lead_mm: float,
    depth_mm: float,
    z_span_mm: float,
    z_center: float,
) -> cq.Shape:
    half = SHOULDER_WIDTH_MM / 2.0
    face = cx + side_sign * half
    profile = _profile_y_points(
        contact_y=contact_y,
        clearance_mm=clearance_mm,
        phase_lead_mm=phase_lead_mm,
    )
    inner = [(face + side_sign * gap, y) for y, gap in profile]
    outer_x = face + side_sign * (clearance_mm + depth_mm)
    wire = cq.Workplane("XY").moveTo(*inner[0]).spline(inner[1:])
    wire = wire.lineTo(outer_x, profile[-1][0]).lineTo(outer_x, profile[0][0]).close()
    return wire.extrude(z_span_mm).translate((0.0, 0.0, z_center - z_span_mm / 2.0)).val()


def _z_cam_pad(
    *,
    contact_y: float,
    contact_z: float,
    side_sign: float,
    clearance_mm: float,
    phase_lead_mm: float,
    depth_mm: float,
    x_span_mm: float,
    x_center: float,
) -> cq.Shape:
    profile = _profile_y_points(
        contact_y=contact_y,
        clearance_mm=clearance_mm,
        phase_lead_mm=phase_lead_mm,
    )
    inner = [(y, contact_z + side_sign * gap) for y, gap in profile]
    outer_z = contact_z + side_sign * (clearance_mm + depth_mm)
    wire = cq.Workplane("YZ", origin=(x_center, 0.0, 0.0)).moveTo(*inner[0]).spline(inner[1:])
    wire = wire.lineTo(profile[-1][0], outer_z).lineTo(profile[0][0], outer_z).close()
    return wire.extrude(x_span_mm / 2.0, both=True).val()


@dataclass(frozen=True, slots=True)
class TerminalDatumPreloadV2Station:
    reaction_id: str
    center_xy_mm: tuple[float, float]
    master_parts: tuple[tuple[str, cq.Shape], ...] = field(repr=False, compare=False)
    preload_outer_parts: tuple[tuple[str, cq.Shape], ...] = field(repr=False, compare=False)
    lossy_backup_references: tuple[tuple[str, cq.Shape], ...] = field(repr=False, compare=False)
    rigid_backup_parts: tuple[tuple[str, cq.Shape], ...] = field(repr=False, compare=False)
    service_sweep: cq.Shape = field(repr=False, compare=False)
    nominal_source_intersection_mm3: float = 0.0
    master_probe_intersections_mm3: tuple[float, float] = (0.0, 0.0)
    service_source_intersection_mm3: float = 0.0

    def __post_init__(self) -> None:
        if self.reaction_id not in REACTION_IDS:
            raise TreatmentTerminalDatumPreloadV2Error("unknown reaction id")
        for _name, shape in (
            self.master_parts
            + self.preload_outer_parts
            + self.lossy_backup_references
            + self.rigid_backup_parts
        ):
            if not shape.isValid() or not shape.Solids() or float(shape.Volume()) <= 0.0:
                raise TreatmentTerminalDatumPreloadV2Error("terminal V2 part must be valid positive geometry")
        if self.nominal_source_intersection_mm3 > _INTERSECTION_TOLERANCE_MM3:
            raise TreatmentTerminalDatumPreloadV2Error("terminal V2 geometry intersects source at nominal seat")
        if min(self.master_probe_intersections_mm3) <= _INTERSECTION_TOLERANCE_MM3:
            raise TreatmentTerminalDatumPreloadV2Error("terminal V2 rigid master datum lacks positive X/Z engagement")
        if self.service_source_intersection_mm3 > _INTERSECTION_TOLERANCE_MM3:
            raise TreatmentTerminalDatumPreloadV2Error("terminal V2 geometry blocks +Y service release")

    def manifest(self) -> dict[str, object]:
        return {
            "reaction_id": self.reaction_id,
            "coordinate_frame_id": WORLD_FRAME_ID,
            "center_xy_mm": list(self.center_xy_mm),
            "architecture": (
                "PHASED_QUINTIC_C2_TERMINAL_CAM_WITH_RIGID_X_Z_MASTER_DATUMS_AND_OPPOSED_PRELOAD_SHOES"
            ),
            "master_parts": [name for name, _shape in self.master_parts],
            "preload_outer_parts": [name for name, _shape in self.preload_outer_parts],
            "lossy_backup_references": [name for name, _shape in self.lossy_backup_references],
            "rigid_backup_parts": [name for name, _shape in self.rigid_backup_parts],
            "terminal_profile": {
                "profile": "QUINTIC_C2_SMOOTHERSTEP_SPLINE_FIT",
                "cam_travel_mm": CAM_TRAVEL_MM,
                "X_phase_lead_mm": X_CAM_PHASE_LEAD_MM,
                "Z_phase_lead_mm": 0.0,
                "flat_full_seat_land_mm": FULL_SEAT_LAND_MM,
                "profile_samples": PROFILE_SAMPLES,
                "entry_slope_intent": 0.0,
                "entry_curvature_intent": 0.0,
                "full_seat_slope_intent": 0.0,
                "full_seat_curvature_intent": 0.0,
            },
            "load_path": (
                "NORMAL_40HZ_REACTION_TO_RIGID_X_Z_MASTER_DATUMS; PRELOAD_SHOES_ONLY_MAINTAIN_CONTACT; "
                "LOSSY_BACKUP_THEN_RIGID_STOP_FOR_ABNORMAL_REVERSE_TRAVEL"
            ),
            "measured": {
                "nominal_source_intersection_mm3": self.nominal_source_intersection_mm3,
                "master_probe_intersections_mm3": list(self.master_probe_intersections_mm3),
                "service_source_intersection_mm3": self.service_source_intersection_mm3,
            },
            "physical_validation": (
                "OPEN_CAM_SURFACE_FINISH_FRICTION_CONTACT_PRESSURE_TOLERANCE_FORCE_TRAVEL_WEAR_"
                "DAMPING_ACOUSTICS_WET_CONTAMINATION_AND_PROCESS_CAPABILITY"
            ),
        }


@dataclass(frozen=True, slots=True)
class TerminalDatumPreloadV2Architecture:
    source_cell6_head_sha: str
    stations: tuple[TerminalDatumPreloadV2Station, ...]
    physical_validation_eligible: bool = False

    def __post_init__(self) -> None:
        if self.source_cell6_head_sha != SOURCE_CELL6_HEAD_SHA:
            raise TreatmentTerminalDatumPreloadV2Error("source Cell 6 head mismatch")
        if tuple(item.reaction_id for item in self.stations) != REACTION_IDS:
            raise TreatmentTerminalDatumPreloadV2Error("all four terminal V2 stations required")
        if self.physical_validation_eligible:
            raise TreatmentTerminalDatumPreloadV2Error("digital terminal V2 geometry is not physical validation")

    @property
    def architecture_sha256(self) -> str:
        raw = json.dumps(self.manifest(False), sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        return hashlib.sha256(raw).hexdigest()

    def manifest(self, include_sha: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema": SCHEMA,
            "source_cell6_head_sha": self.source_cell6_head_sha,
            "coordinate_frame_id": WORLD_FRAME_ID,
            "stations": [station.manifest() for station in self.stations],
            "selected_v1_direction": (
                "RIGID_MASTER_DATUMS_PLUS_PHASED_C2_PRELOAD_SHOES_WITH_SEPARATE_LOSSY_AND_RIGID_BACKUPS"
            ),
            "supersedes": "MASCK_ONE_TREATMENT_TERMINAL_DATUM_PRELOAD_V1",
            "physical_validation_eligible": self.physical_validation_eligible,
        }
        if include_sha:
            payload["architecture_sha256"] = self.architecture_sha256
        return payload


def build_terminal_datum_preload_v2_architecture(
    *,
    model: MasckOneModel | None = None,
    reactions: StructuralFrameActuatorReactionArchitecture | None = None,
    mates: StructuralFrameActuatorMateArchitecture | None = None,
) -> TerminalDatumPreloadV2Architecture:
    model = build_model() if model is None else model
    reactions = build_structural_frame_actuator_reactions(model=model) if reactions is None else reactions
    mates = build_structural_frame_actuator_mates(model=model, reactions=reactions) if mates is None else mates
    frame_zmax = float(reactions.frame_with_reaction_counterparts.val().BoundingBox().zmax)
    shoulder_z0 = frame_zmax + SHOULDER_GAP_MM
    shoulder_z1 = shoulder_z0 + SHOULDER_THICKNESS_MM
    z_mid = 0.5 * (shoulder_z0 + shoulder_z1)

    built: list[TerminalDatumPreloadV2Station] = []
    for mate in mates.mates:
        cx, cy = mate.center_xy_mm
        contact_y = cy + SHOULDER_HEIGHT_MM / 2.0
        master_x_sign = 1.0 if cx < 0.0 else -1.0
        preload_x_sign = -master_x_sign

        master_x = _x_cam_pad(
            cx=cx,
            contact_y=contact_y,
            side_sign=master_x_sign,
            clearance_mm=X_CLEARANCE_MM,
            phase_lead_mm=X_CAM_PHASE_LEAD_MM,
            depth_mm=MASTER_X_DEPTH_MM,
            z_span_mm=MASTER_X_Z_SPAN_MM,
            z_center=z_mid,
        )
        master_z_x = cx + master_x_sign * (SHOULDER_WIDTH_MM / 2.0 - MASTER_Z_X_SPAN_MM / 2.0)
        master_z = _z_cam_pad(
            contact_y=contact_y,
            contact_z=shoulder_z0,
            side_sign=-1.0,
            clearance_mm=Z_CLEARANCE_MM,
            phase_lead_mm=0.0,
            depth_mm=MASTER_Z_DEPTH_MM,
            x_span_mm=MASTER_Z_X_SPAN_MM,
            x_center=master_z_x,
        )

        preload_x = _x_cam_pad(
            cx=cx,
            contact_y=contact_y,
            side_sign=preload_x_sign,
            clearance_mm=X_CLEARANCE_MM,
            phase_lead_mm=X_CAM_PHASE_LEAD_MM,
            depth_mm=PRELOAD_X_DEPTH_MM,
            z_span_mm=PRELOAD_X_Z_SPAN_MM,
            z_center=z_mid,
        )
        preload_z_x = cx + preload_x_sign * (SHOULDER_WIDTH_MM / 2.0 - PRELOAD_Z_X_SPAN_MM / 2.0)
        preload_z = _z_cam_pad(
            contact_y=contact_y,
            contact_z=shoulder_z1,
            side_sign=1.0,
            clearance_mm=Z_CLEARANCE_MM,
            phase_lead_mm=0.0,
            depth_mm=PRELOAD_Z_DEPTH_MM,
            x_span_mm=PRELOAD_Z_X_SPAN_MM,
            x_center=preload_z_x,
        )

        y_center = contact_y - FULL_SEAT_LAND_MM / 2.0
        backup_y = FULL_SEAT_LAND_MM
        x_shoe_outer = cx + preload_x_sign * (SHOULDER_WIDTH_MM / 2.0 + PRELOAD_X_DEPTH_MM)
        x_bumper_center = x_shoe_outer + preload_x_sign * (
            LOSSY_BACKUP_GAP_MM + BACKUP_BUMPER_THICKNESS_MM / 2.0
        )
        x_stop_center = x_shoe_outer + preload_x_sign * (
            LOSSY_BACKUP_GAP_MM + BACKUP_BUMPER_THICKNESS_MM + RIGID_BACKUP_THICKNESS_MM / 2.0
        )
        x_bumper = _box(
            BACKUP_BUMPER_THICKNESS_MM,
            backup_y,
            PRELOAD_X_Z_SPAN_MM,
            (x_bumper_center, y_center, z_mid),
        )
        x_stop = _box(
            RIGID_BACKUP_THICKNESS_MM,
            backup_y,
            PRELOAD_X_Z_SPAN_MM,
            (x_stop_center, y_center, z_mid),
        )

        z_shoe_outer = shoulder_z1 + PRELOAD_Z_DEPTH_MM
        z_bumper_center = z_shoe_outer + LOSSY_BACKUP_GAP_MM + BACKUP_BUMPER_THICKNESS_MM / 2.0
        z_stop_center = z_shoe_outer + LOSSY_BACKUP_GAP_MM + BACKUP_BUMPER_THICKNESS_MM + RIGID_BACKUP_THICKNESS_MM / 2.0
        z_bumper = _box(
            PRELOAD_Z_X_SPAN_MM,
            backup_y,
            BACKUP_BUMPER_THICKNESS_MM,
            (preload_z_x, y_center, z_bumper_center),
        )
        z_stop = _box(
            PRELOAD_Z_X_SPAN_MM,
            backup_y,
            RIGID_BACKUP_THICKNESS_MM,
            (preload_z_x, y_center, z_stop_center),
        )

        source = mate.mate.val()
        all_installed = cq.Compound.makeCompound(
            [master_x, master_z, preload_x, preload_z, x_stop, z_stop]
        )
        nominal = _intersection_volume(all_installed, source)
        master_probe_x = _intersection_volume(
            master_x.translate((-master_x_sign * MASTER_ENGAGEMENT_PROBE_MM, 0.0, 0.0)),
            source,
        )
        master_probe_z = _intersection_volume(
            master_z.translate((0.0, 0.0, MASTER_ENGAGEMENT_PROBE_MM)),
            source,
        )
        service = _translation_envelope(
            all_installed,
            (0.0, TERMINAL_SERVICE_RETRACTION_PROBE_MM, 0.0),
        )
        service_iv = _intersection_volume(service, source)

        built.append(
            TerminalDatumPreloadV2Station(
                mate.reaction_id,
                mate.center_xy_mm,
                (("rigid_master_x_v2", master_x), ("rigid_master_z_v2", master_z)),
                (("preload_x_outer_v2", preload_x), ("preload_z_outer_v2", preload_z)),
                (("x_lossy_backup_reference_v2", x_bumper), ("z_lossy_backup_reference_v2", z_bumper)),
                (("x_rigid_backup_stop_v2", x_stop), ("z_rigid_backup_stop_v2", z_stop)),
                service,
                round(nominal, 8),
                (round(master_probe_x, 8), round(master_probe_z, 8)),
                round(service_iv, 8),
            )
        )

    result = TerminalDatumPreloadV2Architecture(SOURCE_CELL6_HEAD_SHA, tuple(built), False)
    result.__post_init__()
    return result


def export_terminal_datum_preload_v2_architecture(output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    architecture = build_terminal_datum_preload_v2_architecture()
    for station in architecture.stations:
        slug = station.reaction_id.lower()
        cq.exporters.export(
            cq.Compound.makeCompound([shape for _name, shape in station.master_parts]),
            str(output_dir / f"{slug}_terminal_master_datums_v2.step"),
        )
        cq.exporters.export(
            cq.Compound.makeCompound([shape for _name, shape in station.preload_outer_parts]),
            str(output_dir / f"{slug}_terminal_preload_outer_v2.step"),
        )
        cq.exporters.export(
            cq.Compound.makeCompound([shape for _name, shape in station.rigid_backup_parts]),
            str(output_dir / f"{slug}_terminal_rigid_backups_v2.step"),
        )
        cq.exporters.export(
            station.service_sweep,
            str(output_dir / f"{slug}_terminal_service_sweep_v2.step"),
        )
    manifest = architecture.manifest()
    (output_dir / "treatment_terminal_datum_preload_v2_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest
