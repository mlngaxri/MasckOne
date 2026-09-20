from __future__ import annotations

"""Deterministic terminal datum/preload geometry for the treatment carrier.

This supersedes the fully rigid four-face taper as the preferred V1 mount direction.
The long Cell 6 rail remains loose enough for low-drag service motion. Precision is
created only in the terminal ~1 mm by two independent axis systems:

X: one rigid master datum + one independently compliant preload shoe
Z: one rigid master datum + one independently compliant preload shoe

Each master/shoe uses a zero-slope S-curve lead-in followed by a short flat seating
land. That removes the abrupt wedge slope change from the previous V3 taper and gives
the preloader a progressive acquisition phase before the rigid datum becomes the
normal 40 Hz reaction path. A lossy backup and rigid overload stop sit behind each
preload shoe. The spring-root attachment is intentionally still an explicit open
interface; floating shoe/reference geometry is not promoted to production material.

Digital B-reps and analytical seeds only. Force, friction, material grade, contact
pressure, spring-root retention, wear, fatigue, sound and wet contamination remain
physical/manufacturing validation gates.
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
    SHOULDER_GAP_MM,
    SHOULDER_HEIGHT_MM,
    SHOULDER_THICKNESS_MM,
    SHOULDER_WIDTH_MM,
    StructuralFrameActuatorMateArchitecture,
    build_structural_frame_actuator_mates,
)
from .structural_frame_actuator_reactions import (
    REACTION_IDS,
    StructuralFrameActuatorReactionArchitecture,
    build_structural_frame_actuator_reactions,
)

SCHEMA = "MASCK_ONE_TREATMENT_TERMINAL_DATUM_PRELOAD_V1"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"
SOURCE_CELL6_HEAD_SHA = "fcccde02b31cc1c4e01136630d92e550e4e09a11"

RUNNING_X_CLEARANCE_MM = 0.16
RUNNING_Z_CLEARANCE_MM = 0.12
CAM_TRANSITION_TRAVEL_MM = 0.65
FULL_SEAT_LAND_MM = 0.16
POSTERIOR_EXTENSION_MM = 0.08
PROFILE_SAMPLES = 9

MASTER_X_DEPTH_MM = 0.30
MASTER_X_Z_SPAN_MM = 2.40
MASTER_Z_DEPTH_MM = 0.30
MASTER_Z_X_SPAN_MM = 1.00
PRELOAD_X_DEPTH_MM = 0.30
PRELOAD_X_Z_SPAN_MM = 1.60
PRELOAD_Z_DEPTH_MM = 0.30
PRELOAD_Z_X_SPAN_MM = 1.20

SPRING_MODULUS_STUDY_MPA = 190000.0
SPRING_LEAF_WIDTH_MM = 1.00
SPRING_LEAF_THICKNESS_MM = 0.17
SPRING_LEAF_LENGTH_MM = 5.00
AXIS_PRELOAD_TARGET_N = 0.30

LOSSY_BACKUP_GAP_MM = 0.04
LOSSY_BACKUP_COMPRESSION_MM = 0.05
BACKUP_BUMPER_THICKNESS_MM = 0.05
RIGID_BACKUP_THICKNESS_MM = 0.30

ENGAGEMENT_PROBE_MM = 0.03
SERVICE_RETRACTION_PROBE_MM = 2.0
_INTERSECTION_TOLERANCE_MM3 = 1e-7


class TreatmentTerminalDatumPreloadError(ValueError):
    pass


def _smoothstep(s: float) -> float:
    s = min(1.0, max(0.0, float(s)))
    return 3.0 * s**2 - 2.0 * s**3


def spring_leaf_screen() -> dict[str, float]:
    b = SPRING_LEAF_WIDTH_MM
    t = SPRING_LEAF_THICKNESS_MM
    length = SPRING_LEAF_LENGTH_MM
    inertia = b * t**3 / 12.0
    stiffness = 3.0 * SPRING_MODULUS_STUDY_MPA * inertia / length**3
    deflection = AXIS_PRELOAD_TARGET_N / stiffness
    return {
        "second_moment_mm4": inertia,
        "linear_tip_stiffness_N_per_mm": stiffness,
        "preload_target_N": AXIS_PRELOAD_TARGET_N,
        "preload_deflection_seed_mm": deflection,
        "preload_root_stress_proxy_MPa": 6.0 * AXIS_PRELOAD_TARGET_N * length / (b * t**2),
    }


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
        raise TreatmentTerminalDatumPreloadError("intersection kernel failure") from exc
    if not common.isValid():
        raise TreatmentTerminalDatumPreloadError("invalid intersection result")
    value = sum(max(0.0, float(s.Volume())) for s in common.Solids())
    if not math.isfinite(value):
        raise TreatmentTerminalDatumPreloadError("nonfinite intersection result")
    return value


def _join(shapes: list[cq.Shape]) -> cq.Shape:
    if not shapes:
        raise TreatmentTerminalDatumPreloadError("cannot join empty geometry")
    result = shapes[0]
    for shape in shapes[1:]:
        result = result.fuse(shape)
    result = result.clean()
    if not result.isValid() or not result.Solids():
        raise TreatmentTerminalDatumPreloadError("joined geometry must remain valid positive material")
    return result


def _translation_envelope(shape: cq.Shape, travel: tuple[float, float, float]) -> cq.Shape:
    pieces: list[cq.Shape] = [shape, shape.translate(travel)]
    for face in shape.Faces():
        prism = cq.Shape.cast(BRepPrimAPI_MakePrism(face.wrapped, gp_Vec(*travel)).Shape())
        pieces.extend(prism.Solids())
    return _join(pieces)


def _profile_y_points(contact_y: float, clearance_mm: float) -> list[tuple[float, float]]:
    land_start = contact_y - FULL_SEAT_LAND_MM
    start = land_start - CAM_TRANSITION_TRAVEL_MM
    rows: list[tuple[float, float]] = []
    for i in range(PROFILE_SAMPLES):
        s = i / (PROFILE_SAMPLES - 1)
        y = start + CAM_TRANSITION_TRAVEL_MM * s
        gap = clearance_mm * (1.0 - _smoothstep(s))
        rows.append((y, gap))
    rows.append((contact_y + POSTERIOR_EXTENSION_MM, 0.0))
    return rows


def _x_cam_pad(
    *,
    cx: float,
    contact_y: float,
    shoulder_z0: float,
    side_sign: float,
    clearance_mm: float,
    depth_mm: float,
    z_span_mm: float,
    z_center: float,
) -> cq.Shape:
    half = SHOULDER_WIDTH_MM / 2.0
    face = cx + side_sign * half
    profile = _profile_y_points(contact_y, clearance_mm)
    inner = [(face + side_sign * gap, y) for y, gap in profile]
    outer_x = face + side_sign * (clearance_mm + depth_mm)
    if side_sign > 0.0:
        outline = inner + [(outer_x, profile[-1][0]), (outer_x, profile[0][0])]
    else:
        outline = [(outer_x, profile[0][0]), (outer_x, profile[-1][0])] + list(reversed(inner))
    return (
        cq.Workplane("XY")
        .polyline(outline)
        .close()
        .extrude(z_span_mm)
        .translate((0.0, 0.0, z_center - z_span_mm / 2.0))
        .val()
    )


def _z_cam_pad(
    *,
    cx: float,
    contact_y: float,
    contact_z: float,
    side_sign: float,
    clearance_mm: float,
    depth_mm: float,
    x_span_mm: float,
    x_center: float,
) -> cq.Shape:
    profile = _profile_y_points(contact_y, clearance_mm)
    inner = [(y, contact_z + side_sign * gap) for y, gap in profile]
    outer_z = contact_z + side_sign * (clearance_mm + depth_mm)
    if side_sign > 0.0:
        outline = inner + [(profile[-1][0], outer_z), (profile[0][0], outer_z)]
    else:
        outline = [(profile[0][0], outer_z), (profile[-1][0], outer_z)] + list(reversed(inner))
    return (
        cq.Workplane("YZ", origin=(x_center, 0.0, 0.0))
        .polyline(outline)
        .close()
        .extrude(x_span_mm / 2.0, both=True)
        .val()
    )


def _box(x: float, y: float, z: float, center: tuple[float, float, float]) -> cq.Shape:
    if min(x, y, z) <= 0.0:
        raise TreatmentTerminalDatumPreloadError("box dimensions must be positive")
    return cq.Workplane("XY").box(x, y, z).translate(center).val()


@dataclass(frozen=True, slots=True)
class TerminalDatumPreloadStation:
    reaction_id: str
    center_xy_mm: tuple[float, float]
    master_parts: tuple[tuple[str, cq.Shape], ...] = field(repr=False, compare=False)
    preload_installed_parts: tuple[tuple[str, cq.Shape], ...] = field(repr=False, compare=False)
    preload_free_references: tuple[tuple[str, cq.Shape], ...] = field(repr=False, compare=False)
    lossy_backup_references: tuple[tuple[str, cq.Shape], ...] = field(repr=False, compare=False)
    rigid_backup_parts: tuple[tuple[str, cq.Shape], ...] = field(repr=False, compare=False)
    service_sweep: cq.Shape = field(repr=False, compare=False)
    nominal_source_intersection_mm3: float = 0.0
    master_probe_intersections_mm3: tuple[float, float] = (0.0, 0.0)
    free_preload_intersections_mm3: tuple[float, float] = (0.0, 0.0)
    service_source_intersection_mm3: float = 0.0

    def __post_init__(self) -> None:
        if self.reaction_id not in REACTION_IDS:
            raise TreatmentTerminalDatumPreloadError("unknown reaction id")
        for _name, shape in (
            self.master_parts + self.preload_installed_parts + self.lossy_backup_references + self.rigid_backup_parts
        ):
            if not shape.isValid() or not shape.Solids() or shape.Volume() <= 0.0:
                raise TreatmentTerminalDatumPreloadError("terminal datum/preload part must be valid positive geometry")
        if self.nominal_source_intersection_mm3 > _INTERSECTION_TOLERANCE_MM3:
            raise TreatmentTerminalDatumPreloadError("terminal datum/preload geometry intersects source at nominal seat")
        if min(self.master_probe_intersections_mm3) <= _INTERSECTION_TOLERANCE_MM3:
            raise TreatmentTerminalDatumPreloadError("rigid master datum lacks positive X/Z engagement")
        if min(self.free_preload_intersections_mm3) <= _INTERSECTION_TOLERANCE_MM3:
            raise TreatmentTerminalDatumPreloadError("preload free-state reference does not require spring deflection")
        if self.service_source_intersection_mm3 > _INTERSECTION_TOLERANCE_MM3:
            raise TreatmentTerminalDatumPreloadError("terminal datum/preload geometry blocks +Y service release")

    def manifest(self) -> dict[str, object]:
        spring = spring_leaf_screen()
        return {
            "reaction_id": self.reaction_id,
            "coordinate_frame_id": WORLD_FRAME_ID,
            "center_xy_mm": list(self.center_xy_mm),
            "architecture": (
                "LOW_DRAG_RAIL_PLUS_INDEPENDENT_X_Z_S_CURVE_PRELOAD_SHOES_AGAINST_RIGID_MASTER_DATUMS"
            ),
            "master_parts": [name for name, _ in self.master_parts],
            "preload_installed_parts": [name for name, _ in self.preload_installed_parts],
            "preload_free_references": [name for name, _ in self.preload_free_references],
            "lossy_backup_references": [name for name, _ in self.lossy_backup_references],
            "rigid_backup_parts": [name for name, _ in self.rigid_backup_parts],
            "terminal_profile": {
                "cam_transition_travel_mm": CAM_TRANSITION_TRAVEL_MM,
                "flat_full_seat_land_mm": FULL_SEAT_LAND_MM,
                "profile_samples": PROFILE_SAMPLES,
                "entry_slope": 0.0,
                "full_seat_slope": 0.0,
            },
            "spring_leaf_screen": spring,
            "load_path": (
                "NORMAL_40HZ_REACTION_TO_RIGID_X_Z_MASTER_DATUMS; PRELOAD_SHOES_ONLY_KEEP_CONTACT_CLOSED; "
                "LOSSY_BACKUP_THEN_RIGID_STOP_FOR_ABNORMAL_REVERSE_TRAVEL"
            ),
            "measured": {
                "nominal_source_intersection_mm3": self.nominal_source_intersection_mm3,
                "master_probe_intersections_mm3": list(self.master_probe_intersections_mm3),
                "free_preload_intersections_mm3": list(self.free_preload_intersections_mm3),
                "service_source_intersection_mm3": self.service_source_intersection_mm3,
            },
            "spring_root_attachment_status": (
                "OPEN_EXPLICIT_CAPTURE_REQUIRED_BEFORE_PRELOAD_SHOES_CAN_BECOME_PRODUCTION_MATERIAL"
            ),
            "physical_validation": (
                "OPEN_FORCE_FRICTION_CONTACT_PRESSURE_SPRING_GRADE_ROOT_RETENTION_FATIGUE_WEAR_"
                "CREEP_DAMPING_ACOUSTICS_WET_CONTAMINATION_AND_PROCESS_CAPABILITY"
            ),
        }


@dataclass(frozen=True, slots=True)
class TerminalDatumPreloadArchitecture:
    source_cell6_head_sha: str
    stations: tuple[TerminalDatumPreloadStation, ...]
    physical_validation_eligible: bool = False

    def __post_init__(self) -> None:
        if self.source_cell6_head_sha != SOURCE_CELL6_HEAD_SHA:
            raise TreatmentTerminalDatumPreloadError("source Cell 6 head mismatch")
        if tuple(item.reaction_id for item in self.stations) != REACTION_IDS:
            raise TreatmentTerminalDatumPreloadError("all four terminal datum/preload stations required")
        if self.physical_validation_eligible:
            raise TreatmentTerminalDatumPreloadError("digital datum/preload geometry is not physical validation")

    @property
    def architecture_sha256(self) -> str:
        raw = json.dumps(self.manifest(False), sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        return hashlib.sha256(raw).hexdigest()

    def manifest(self, include_sha: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema": SCHEMA,
            "source_cell6_head_sha": self.source_cell6_head_sha,
            "coordinate_frame_id": WORLD_FRAME_ID,
            "stations": [item.manifest() for item in self.stations],
            "selected_v1_direction": (
                "RIGID_MASTER_X_Z_DATUMS_PLUS_INDEPENDENT_PRELOAD_SHOES_WITH_ZERO_SLOPE_TERMINAL_CAMS"
            ),
            "supersedes_as_production_baseline": "FULLY_RIGID_FOUR_FACE_MATCHED_TAPER_V3",
            "physical_validation_eligible": self.physical_validation_eligible,
        }
        if include_sha:
            payload["architecture_sha256"] = self.architecture_sha256
        return payload


def build_terminal_datum_preload_architecture(
    *,
    model: MasckOneModel | None = None,
    reactions: StructuralFrameActuatorReactionArchitecture | None = None,
    mates: StructuralFrameActuatorMateArchitecture | None = None,
) -> TerminalDatumPreloadArchitecture:
    model = build_model() if model is None else model
    reactions = build_structural_frame_actuator_reactions(model=model) if reactions is None else reactions
    mates = build_structural_frame_actuator_mates(model=model, reactions=reactions) if mates is None else mates
    frame_zmax = float(reactions.frame_with_reaction_counterparts.val().BoundingBox().zmax)
    shoulder_z0 = frame_zmax + SHOULDER_GAP_MM
    shoulder_z1 = shoulder_z0 + SHOULDER_THICKNESS_MM
    z_mid = 0.5 * (shoulder_z0 + shoulder_z1)
    spring_deflection = spring_leaf_screen()["preload_deflection_seed_mm"]

    built: list[TerminalDatumPreloadStation] = []
    for mate in mates.mates:
        cx, cy = mate.center_xy_mm
        contact_y = cy + SHOULDER_HEIGHT_MM / 2.0
        # Master X datum is always inboard; opposite X shoe pushes toward it.
        master_x_sign = 1.0 if cx < 0.0 else -1.0
        preload_x_sign = -master_x_sign

        master_x = _x_cam_pad(
            cx=cx,
            contact_y=contact_y,
            shoulder_z0=shoulder_z0,
            side_sign=master_x_sign,
            clearance_mm=RUNNING_X_CLEARANCE_MM,
            depth_mm=MASTER_X_DEPTH_MM,
            z_span_mm=MASTER_X_Z_SPAN_MM,
            z_center=z_mid,
        )
        master_z_x = cx + master_x_sign * (SHOULDER_WIDTH_MM / 2.0 - MASTER_Z_X_SPAN_MM / 2.0)
        master_z = _z_cam_pad(
            cx=cx,
            contact_y=contact_y,
            contact_z=shoulder_z0,
            side_sign=-1.0,
            clearance_mm=RUNNING_Z_CLEARANCE_MM,
            depth_mm=MASTER_Z_DEPTH_MM,
            x_span_mm=MASTER_Z_X_SPAN_MM,
            x_center=master_z_x,
        )

        preload_x = _x_cam_pad(
            cx=cx,
            contact_y=contact_y,
            shoulder_z0=shoulder_z0,
            side_sign=preload_x_sign,
            clearance_mm=RUNNING_X_CLEARANCE_MM,
            depth_mm=PRELOAD_X_DEPTH_MM,
            z_span_mm=PRELOAD_X_Z_SPAN_MM,
            z_center=z_mid,
        )
        preload_z_x = cx + preload_x_sign * (SHOULDER_WIDTH_MM / 2.0 - PRELOAD_Z_X_SPAN_MM / 2.0)
        preload_z = _z_cam_pad(
            cx=cx,
            contact_y=contact_y,
            contact_z=shoulder_z1,
            side_sign=1.0,
            clearance_mm=RUNNING_Z_CLEARANCE_MM,
            depth_mm=PRELOAD_Z_DEPTH_MM,
            x_span_mm=PRELOAD_Z_X_SPAN_MM,
            x_center=preload_z_x,
        )

        free_x = preload_x.translate((master_x_sign * spring_deflection, 0.0, 0.0))
        free_z = preload_z.translate((0.0, 0.0, -spring_deflection))

        y_center = contact_y - FULL_SEAT_LAND_MM / 2.0
        backup_y = FULL_SEAT_LAND_MM
        x_shoe_outer = cx + preload_x_sign * (SHOULDER_WIDTH_MM / 2.0 + PRELOAD_X_DEPTH_MM)
        x_bumper_center = x_shoe_outer + preload_x_sign * (
            LOSSY_BACKUP_GAP_MM + BACKUP_BUMPER_THICKNESS_MM / 2.0
        )
        x_stop_center = x_shoe_outer + preload_x_sign * (
            LOSSY_BACKUP_GAP_MM + BACKUP_BUMPER_THICKNESS_MM + RIGID_BACKUP_THICKNESS_MM / 2.0
        )
        x_bumper = _box(BACKUP_BUMPER_THICKNESS_MM, backup_y, PRELOAD_X_Z_SPAN_MM, (x_bumper_center, y_center, z_mid))
        x_stop = _box(RIGID_BACKUP_THICKNESS_MM, backup_y, PRELOAD_X_Z_SPAN_MM, (x_stop_center, y_center, z_mid))

        z_shoe_outer = shoulder_z1 + PRELOAD_Z_DEPTH_MM
        z_bumper_center = z_shoe_outer + LOSSY_BACKUP_GAP_MM + BACKUP_BUMPER_THICKNESS_MM / 2.0
        z_stop_center = z_shoe_outer + LOSSY_BACKUP_GAP_MM + BACKUP_BUMPER_THICKNESS_MM + RIGID_BACKUP_THICKNESS_MM / 2.0
        z_bumper = _box(PRELOAD_Z_X_SPAN_MM, backup_y, BACKUP_BUMPER_THICKNESS_MM, (preload_z_x, y_center, z_bumper_center))
        z_stop = _box(PRELOAD_Z_X_SPAN_MM, backup_y, RIGID_BACKUP_THICKNESS_MM, (preload_z_x, y_center, z_stop_center))

        source = mate.mate.val()
        all_installed = cq.Compound.makeCompound([master_x, master_z, preload_x, preload_z, x_stop, z_stop])
        nominal = _intersection_volume(all_installed, source)
        master_probe_x = _intersection_volume(master_x.translate((-master_x_sign * ENGAGEMENT_PROBE_MM, 0.0, 0.0)), source)
        master_probe_z = _intersection_volume(master_z.translate((0.0, 0.0, ENGAGEMENT_PROBE_MM)), source)
        free_x_iv = _intersection_volume(free_x, source)
        free_z_iv = _intersection_volume(free_z, source)
        service = _translation_envelope(all_installed, (0.0, SERVICE_RETRACTION_PROBE_MM, 0.0))
        service_iv = _intersection_volume(service, source)

        built.append(
            TerminalDatumPreloadStation(
                mate.reaction_id,
                mate.center_xy_mm,
                (("rigid_master_x", master_x), ("rigid_master_z", master_z)),
                (("preload_x_installed", preload_x), ("preload_z_installed", preload_z)),
                (("preload_x_free_reference", free_x), ("preload_z_free_reference", free_z)),
                (("x_lossy_backup_reference", x_bumper), ("z_lossy_backup_reference", z_bumper)),
                (("x_rigid_backup_stop", x_stop), ("z_rigid_backup_stop", z_stop)),
                service,
                round(nominal, 8),
                (round(master_probe_x, 8), round(master_probe_z, 8)),
                (round(free_x_iv, 8), round(free_z_iv, 8)),
                round(service_iv, 8),
            )
        )

    result = TerminalDatumPreloadArchitecture(SOURCE_CELL6_HEAD_SHA, tuple(built), False)
    result.__post_init__()
    return result


def export_terminal_datum_preload_architecture(output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    architecture = build_terminal_datum_preload_architecture()
    for station in architecture.stations:
        slug = station.reaction_id.lower()
        cq.exporters.export(
            cq.Compound.makeCompound([shape for _name, shape in station.master_parts]),
            str(output_dir / f"{slug}_terminal_master_datums.step"),
        )
        cq.exporters.export(
            cq.Compound.makeCompound([shape for _name, shape in station.preload_installed_parts]),
            str(output_dir / f"{slug}_terminal_preload_shoes_installed.step"),
        )
        cq.exporters.export(
            cq.Compound.makeCompound([shape for _name, shape in station.rigid_backup_parts]),
            str(output_dir / f"{slug}_terminal_rigid_backups.step"),
        )
        cq.exporters.export(station.service_sweep, str(output_dir / f"{slug}_terminal_service_sweep.step"))
    manifest = architecture.manifest()
    (output_dir / "treatment_terminal_datum_preload_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest
