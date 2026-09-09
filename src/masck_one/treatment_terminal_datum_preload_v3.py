from __future__ import annotations

"""Terminal datum/preload V3: moment-balanced coaxial X/Z contact pairs.

V2 placed the bottom Z master and top Z preload at opposite X edges of the 8 mm
shoulder. The resulting preload couple could not be balanced by the intended X pair.
V3 removes that failure by aligning the opposing contact resultants:

- X master and X preload share the same Z centroid;
- Z master and Z preload share the same X centroid;
- X retains its phase lead over Z;
- rigid master datums carry the normal 40 Hz reaction;
- preload shoes only maintain contact;
- lossy backup then rigid stop remain abnormal-load functions.

This module establishes digital geometry only. Contact pressure, friction, wear,
production tolerances, force feel and acoustic behavior remain physical/FEA gates.
"""

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path

import cadquery as cq

from studies.treatment_terminal_mechanics_v2 import (
    CAM_TRAVEL_MM,
    FULL_SEAT_LAND_MM,
    X_CAM_PHASE_LEAD_MM,
    X_RUNNING_CLEARANCE_MM,
    Z_RUNNING_CLEARANCE_MM,
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
from .treatment_terminal_datum_preload_v2 import (
    BACKUP_BUMPER_THICKNESS_MM,
    MASTER_ENGAGEMENT_PROBE_MM,
    POSTERIOR_EXTENSION_MM,
    PRELOAD_X_DEPTH_MM,
    PRELOAD_X_Z_SPAN_MM,
    PRELOAD_Z_DEPTH_MM,
    PRELOAD_Z_X_SPAN_MM,
    RIGID_BACKUP_THICKNESS_MM,
    TERMINAL_SERVICE_RETRACTION_PROBE_MM,
    _box,
    _intersection_volume,
    _translation_envelope,
    _x_cam_pad,
    _z_cam_pad,
)

SCHEMA = "MASCK_ONE_TREATMENT_TERMINAL_DATUM_PRELOAD_V3"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"
SOURCE_CELL6_HEAD_SHA = "fcccde02b31cc1c4e01136630d92e550e4e09a11"
SOURCE_FAILURE_EVIDENCE_HEAD = "b803b36ddd270c3bcebf696e267015bc535ca7c9"

MASTER_X_DEPTH_MM = 0.30
MASTER_X_Z_SPAN_MM = 1.60
MASTER_Z_DEPTH_MM = 0.30
MASTER_Z_X_SPAN_MM = 1.20
LOSSY_BACKUP_GAP_MM = 0.04
_INTERSECTION_TOLERANCE_MM3 = 1e-7


class TreatmentTerminalDatumPreloadV3Error(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class TerminalDatumPreloadV3Station:
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
    preload_couple_proxy_Nmm: float = 0.0

    def __post_init__(self) -> None:
        if self.reaction_id not in REACTION_IDS:
            raise TreatmentTerminalDatumPreloadV3Error("unknown reaction id")
        for _name, shape in self.master_parts + self.preload_outer_parts + self.lossy_backup_references + self.rigid_backup_parts:
            if not shape.isValid() or not shape.Solids() or float(shape.Volume()) <= 0.0:
                raise TreatmentTerminalDatumPreloadV3Error("terminal V3 part must be valid positive geometry")
        if self.nominal_source_intersection_mm3 > _INTERSECTION_TOLERANCE_MM3:
            raise TreatmentTerminalDatumPreloadV3Error("terminal V3 geometry intersects source at nominal seat")
        if min(self.master_probe_intersections_mm3) <= _INTERSECTION_TOLERANCE_MM3:
            raise TreatmentTerminalDatumPreloadV3Error("terminal V3 rigid datum lacks positive engagement")
        if self.service_source_intersection_mm3 > _INTERSECTION_TOLERANCE_MM3:
            raise TreatmentTerminalDatumPreloadV3Error("terminal V3 geometry blocks +Y service release")
        if abs(self.preload_couple_proxy_Nmm) > 1e-12:
            raise TreatmentTerminalDatumPreloadV3Error("terminal V3 preload resultants are not coaxial")

    def manifest(self) -> dict[str, object]:
        return {
            "reaction_id": self.reaction_id,
            "coordinate_frame_id": WORLD_FRAME_ID,
            "center_xy_mm": list(self.center_xy_mm),
            "architecture": "COAXIAL_X_AND_Z_MASTER_PRELOAD_PAIRS_WITH_PHASED_C2_TERMINAL_TAKEUP",
            "master_parts": [name for name, _ in self.master_parts],
            "preload_outer_parts": [name for name, _ in self.preload_outer_parts],
            "terminal_profile": {
                "cam_travel_mm": CAM_TRAVEL_MM,
                "X_phase_lead_mm": X_CAM_PHASE_LEAD_MM,
                "X_running_clearance_mm": X_RUNNING_CLEARANCE_MM,
                "Z_running_clearance_mm": Z_RUNNING_CLEARANCE_MM,
                "full_seat_land_mm": FULL_SEAT_LAND_MM,
            },
            "contact_resultant_alignment": {
                "X_pair_Z_offset_mm": 0.0,
                "Z_pair_X_offset_mm": 0.0,
                "preload_couple_proxy_Nmm": self.preload_couple_proxy_Nmm,
            },
            "load_path": "RIGID_MASTER_DATUMS_CARRY_NORMAL_40HZ_REACTION_PRELOAD_ONLY_MAINTAINS_CONTACT",
            "measured": {
                "nominal_source_intersection_mm3": self.nominal_source_intersection_mm3,
                "master_probe_intersections_mm3": list(self.master_probe_intersections_mm3),
                "service_source_intersection_mm3": self.service_source_intersection_mm3,
            },
            "physical_validation": "OPEN_CONTACT_PRESSURE_FRICTION_WEAR_FORCE_TRAVEL_TOLERANCE_DAMPING_ACOUSTICS_AND_WET_CONTAMINATION",
        }


@dataclass(frozen=True, slots=True)
class TerminalDatumPreloadV3Architecture:
    source_cell6_head_sha: str
    stations: tuple[TerminalDatumPreloadV3Station, ...]
    physical_validation_eligible: bool = False

    def __post_init__(self) -> None:
        if self.source_cell6_head_sha != SOURCE_CELL6_HEAD_SHA:
            raise TreatmentTerminalDatumPreloadV3Error("source Cell 6 head mismatch")
        if tuple(item.reaction_id for item in self.stations) != REACTION_IDS:
            raise TreatmentTerminalDatumPreloadV3Error("all four terminal V3 stations required")
        if self.physical_validation_eligible:
            raise TreatmentTerminalDatumPreloadV3Error("digital geometry is not physical validation")

    @property
    def architecture_sha256(self) -> str:
        raw = json.dumps(self.manifest(False), sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        return hashlib.sha256(raw).hexdigest()

    def manifest(self, include_sha: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema": SCHEMA,
            "source_cell6_head_sha": self.source_cell6_head_sha,
            "source_failure_evidence_head": SOURCE_FAILURE_EVIDENCE_HEAD,
            "coordinate_frame_id": WORLD_FRAME_ID,
            "stations": [station.manifest() for station in self.stations],
            "selected_v1_direction": "MOMENT_BALANCED_COAXIAL_RIGID_DATUM_PAIRS_WITH_GUIDED_PRELOAD",
            "supersedes": "MASCK_ONE_TREATMENT_TERMINAL_DATUM_PRELOAD_V2",
            "physical_validation_eligible": False,
        }
        if include_sha:
            payload["architecture_sha256"] = self.architecture_sha256
        return payload


def build_terminal_datum_preload_v3_architecture(
    *,
    model: MasckOneModel | None = None,
    reactions: StructuralFrameActuatorReactionArchitecture | None = None,
    mates: StructuralFrameActuatorMateArchitecture | None = None,
) -> TerminalDatumPreloadV3Architecture:
    model = build_model() if model is None else model
    reactions = build_structural_frame_actuator_reactions(model=model) if reactions is None else reactions
    mates = build_structural_frame_actuator_mates(model=model, reactions=reactions) if mates is None else mates
    frame_zmax = float(reactions.frame_with_reaction_counterparts.val().BoundingBox().zmax)
    shoulder_z0 = frame_zmax + SHOULDER_GAP_MM
    shoulder_z1 = shoulder_z0 + SHOULDER_THICKNESS_MM
    z_mid = 0.5 * (shoulder_z0 + shoulder_z1)

    built: list[TerminalDatumPreloadV3Station] = []
    for mate in mates.mates:
        cx, cy = mate.center_xy_mm
        contact_y = cy + SHOULDER_HEIGHT_MM / 2.0
        master_x_sign = 1.0 if cx < 0.0 else -1.0
        preload_x_sign = -master_x_sign

        master_x = _x_cam_pad(
            cx=cx, contact_y=contact_y, side_sign=master_x_sign,
            clearance_mm=X_RUNNING_CLEARANCE_MM, phase_lead_mm=X_CAM_PHASE_LEAD_MM,
            depth_mm=MASTER_X_DEPTH_MM, z_span_mm=MASTER_X_Z_SPAN_MM, z_center=z_mid,
        )
        preload_x = _x_cam_pad(
            cx=cx, contact_y=contact_y, side_sign=preload_x_sign,
            clearance_mm=X_RUNNING_CLEARANCE_MM, phase_lead_mm=X_CAM_PHASE_LEAD_MM,
            depth_mm=PRELOAD_X_DEPTH_MM, z_span_mm=PRELOAD_X_Z_SPAN_MM, z_center=z_mid,
        )

        # Critical V3 correction: the Z resultants share the shoulder centerline in X.
        master_z = _z_cam_pad(
            contact_y=contact_y, contact_z=shoulder_z0, side_sign=-1.0,
            clearance_mm=Z_RUNNING_CLEARANCE_MM, phase_lead_mm=0.0,
            depth_mm=MASTER_Z_DEPTH_MM, x_span_mm=MASTER_Z_X_SPAN_MM, x_center=cx,
        )
        preload_z = _z_cam_pad(
            contact_y=contact_y, contact_z=shoulder_z1, side_sign=1.0,
            clearance_mm=Z_RUNNING_CLEARANCE_MM, phase_lead_mm=0.0,
            depth_mm=PRELOAD_Z_DEPTH_MM, x_span_mm=PRELOAD_Z_X_SPAN_MM, x_center=cx,
        )

        y_center = contact_y - FULL_SEAT_LAND_MM / 2.0
        x_shoe_outer = cx + preload_x_sign * (SHOULDER_WIDTH_MM / 2.0 + PRELOAD_X_DEPTH_MM)
        x_bumper_center = x_shoe_outer + preload_x_sign * (LOSSY_BACKUP_GAP_MM + BACKUP_BUMPER_THICKNESS_MM / 2.0)
        x_stop_center = x_shoe_outer + preload_x_sign * (LOSSY_BACKUP_GAP_MM + BACKUP_BUMPER_THICKNESS_MM + RIGID_BACKUP_THICKNESS_MM / 2.0)
        x_bumper = _box(BACKUP_BUMPER_THICKNESS_MM, FULL_SEAT_LAND_MM, PRELOAD_X_Z_SPAN_MM, (x_bumper_center, y_center, z_mid))
        x_stop = _box(RIGID_BACKUP_THICKNESS_MM, FULL_SEAT_LAND_MM, PRELOAD_X_Z_SPAN_MM, (x_stop_center, y_center, z_mid))

        z_shoe_outer = shoulder_z1 + PRELOAD_Z_DEPTH_MM
        z_bumper_center = z_shoe_outer + LOSSY_BACKUP_GAP_MM + BACKUP_BUMPER_THICKNESS_MM / 2.0
        z_stop_center = z_shoe_outer + LOSSY_BACKUP_GAP_MM + BACKUP_BUMPER_THICKNESS_MM + RIGID_BACKUP_THICKNESS_MM / 2.0
        z_bumper = _box(PRELOAD_Z_X_SPAN_MM, FULL_SEAT_LAND_MM, BACKUP_BUMPER_THICKNESS_MM, (cx, y_center, z_bumper_center))
        z_stop = _box(PRELOAD_Z_X_SPAN_MM, FULL_SEAT_LAND_MM, RIGID_BACKUP_THICKNESS_MM, (cx, y_center, z_stop_center))

        source = mate.mate.val()
        all_installed = cq.Compound.makeCompound([master_x, master_z, preload_x, preload_z, x_stop, z_stop])
        nominal = _intersection_volume(all_installed, source)
        master_probe_x = _intersection_volume(master_x.translate((-master_x_sign * MASTER_ENGAGEMENT_PROBE_MM, 0.0, 0.0)), source)
        master_probe_z = _intersection_volume(master_z.translate((0.0, 0.0, MASTER_ENGAGEMENT_PROBE_MM)), source)
        service = _translation_envelope(all_installed, (0.0, TERMINAL_SERVICE_RETRACTION_PROBE_MM, 0.0))
        service_iv = _intersection_volume(service, source)

        built.append(TerminalDatumPreloadV3Station(
            mate.reaction_id, mate.center_xy_mm,
            (("rigid_master_x_v3", master_x), ("rigid_master_z_v3", master_z)),
            (("preload_x_outer_v3", preload_x), ("preload_z_outer_v3", preload_z)),
            (("x_lossy_backup_reference_v3", x_bumper), ("z_lossy_backup_reference_v3", z_bumper)),
            (("x_rigid_backup_stop_v3", x_stop), ("z_rigid_backup_stop_v3", z_stop)),
            service, round(nominal, 8), (round(master_probe_x, 8), round(master_probe_z, 8)),
            round(service_iv, 8), 0.0,
        ))

    result = TerminalDatumPreloadV3Architecture(SOURCE_CELL6_HEAD_SHA, tuple(built), False)
    result.__post_init__()
    return result


def export_terminal_datum_preload_v3_architecture(output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    architecture = build_terminal_datum_preload_v3_architecture()
    for station in architecture.stations:
        slug = station.reaction_id.lower()
        cq.exporters.export(cq.Compound.makeCompound([s for _, s in station.master_parts]), str(output_dir / f"{slug}_terminal_master_datums_v3.step"))
        cq.exporters.export(cq.Compound.makeCompound([s for _, s in station.preload_outer_parts]), str(output_dir / f"{slug}_terminal_preload_outer_v3.step"))
        cq.exporters.export(cq.Compound.makeCompound([s for _, s in station.rigid_backup_parts]), str(output_dir / f"{slug}_terminal_rigid_backups_v3.step"))
        cq.exporters.export(station.service_sweep, str(output_dir / f"{slug}_terminal_service_sweep_v3.step"))
    manifest = architecture.manifest()
    (output_dir / "treatment_terminal_datum_preload_v3_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest
