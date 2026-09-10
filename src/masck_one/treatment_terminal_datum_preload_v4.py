from __future__ import annotations

"""Terminal datum/preload V4: robust staged-unseat service verification.

V4 preserves the selected V3 contact geometry and load path. The verification model
keeps manufactured seated contact separate from service reference motion. A service
withdrawal no longer starts by prism-sweeping an exactly seated/tangent datum, because
that creates an OpenCascade sliver common at t=0 even when the seated state has zero
positive material interference.

The service sequence is therefore explicit and mechanically meaningful:

1. verify the nominal seated state independently;
2. translate every terminal part +Y by a small positive unseat distance;
3. verify the unseated state has zero positive source intersection;
4. build the remaining Boolean-free continuous withdrawal reference from that
   positively separated state to the original 2.0 mm service endpoint.

This is not a tolerance waiver. Any positive volumetric collision in the seated state,
positive-unseat state or remaining service sweep still fails closed. Force, friction,
fatigue, acoustic behavior and subjective feel remain physical-validation work.
"""

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

import cadquery as cq

from studies.treatment_terminal_mechanics_v2 import (
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
from .treatment_reference_geometry import (
    intersection_volume_mm3,
    translation_reference_compound,
)
from .treatment_terminal_datum_preload_v2 import (
    BACKUP_BUMPER_THICKNESS_MM,
    MASTER_ENGAGEMENT_PROBE_MM,
    PRELOAD_X_DEPTH_MM,
    PRELOAD_X_Z_SPAN_MM,
    PRELOAD_Z_DEPTH_MM,
    PRELOAD_Z_X_SPAN_MM,
    RIGID_BACKUP_THICKNESS_MM,
    TERMINAL_SERVICE_RETRACTION_PROBE_MM,
    _box,
    _x_cam_pad,
    _z_cam_pad,
)
from .treatment_terminal_datum_preload_v3 import (
    LOSSY_BACKUP_GAP_MM,
    MASTER_X_DEPTH_MM,
    MASTER_X_Z_SPAN_MM,
    MASTER_Z_DEPTH_MM,
    MASTER_Z_X_SPAN_MM,
    SOURCE_FAILURE_EVIDENCE_HEAD,
    TerminalDatumPreloadV3Station,
)

SCHEMA = "MASCK_ONE_TREATMENT_TERMINAL_DATUM_PRELOAD_V4"
WORLD_FRAME_ID = "MASCK_ONE_AUTHORITY_WORLD_MM"
SOURCE_CELL6_HEAD_SHA = "2d5ace19e2f87a8bd92f4620d8e6b225ba3826be"
_INTERSECTION_TOLERANCE_MM3 = 1e-7

# Service removal must first unload and positively separate the rigid datum stack.
# This is intentionally larger than kernel contact fuzz while remaining a tiny
# fraction of the complete 2.0 mm service retraction reference.
SERVICE_UNSEAT_MM = 0.05
SERVICE_REMAINING_RETRACTION_MM = TERMINAL_SERVICE_RETRACTION_PROBE_MM - SERVICE_UNSEAT_MM

if not (0.0 < SERVICE_UNSEAT_MM < TERMINAL_SERVICE_RETRACTION_PROBE_MM):
    raise ValueError("service unseat must be positive and smaller than full retraction")


class TreatmentTerminalDatumPreloadV4Error(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class TerminalDatumPreloadV4Architecture:
    source_cell6_head_sha: str
    stations: tuple[TerminalDatumPreloadV3Station, ...]
    physical_validation_eligible: bool = False

    def __post_init__(self) -> None:
        if self.source_cell6_head_sha != SOURCE_CELL6_HEAD_SHA:
            raise TreatmentTerminalDatumPreloadV4Error("source Cell 6 head mismatch")
        if tuple(item.reaction_id for item in self.stations) != REACTION_IDS:
            raise TreatmentTerminalDatumPreloadV4Error("all four terminal V4 stations required")
        if self.physical_validation_eligible:
            raise TreatmentTerminalDatumPreloadV4Error("digital geometry is not physical validation")

    @property
    def architecture_sha256(self) -> str:
        raw = json.dumps(
            self.manifest(False),
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode()
        return hashlib.sha256(raw).hexdigest()

    def manifest(self, include_sha: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "schema": SCHEMA,
            "source_cell6_head_sha": self.source_cell6_head_sha,
            "source_failure_evidence_head": SOURCE_FAILURE_EVIDENCE_HEAD,
            "coordinate_frame_id": WORLD_FRAME_ID,
            "stations": [station.manifest() for station in self.stations],
            "selected_v1_direction": "MOMENT_BALANCED_COAXIAL_RIGID_DATUM_PAIRS_WITH_GUIDED_PRELOAD",
            "verification_revision": (
                "BOOLEAN_FREE_REFERENCE_SWEEPS_AFTER_EXPLICIT_POSITIVE_DATUM_UNSEAT_"
                "WITH_SOLID_PAIR_VOLUMETRIC_COLLISION"
            ),
            "service_motion": {
                "sequence": [
                    "CHECK_SEATED_CONTACT_SEPARATELY",
                    "UNLOAD_AND_UNSEAT_PLUS_Y",
                    "LOW_DRAG_WITHDRAWAL_PLUS_Y",
                ],
                "unseat_mm": SERVICE_UNSEAT_MM,
                "remaining_reference_retraction_mm": SERVICE_REMAINING_RETRACTION_MM,
                "full_reference_endpoint_mm": TERMINAL_SERVICE_RETRACTION_PROBE_MM,
                "tangent_t0_prism_sweep_prohibited": True,
                "collision_threshold_weakened": False,
            },
            "supersedes": "MASCK_ONE_TREATMENT_TERMINAL_DATUM_PRELOAD_V3",
            "physical_validation_eligible": False,
        }
        if include_sha:
            payload["architecture_sha256"] = self.architecture_sha256
        return payload


def _service_reference_after_unseat(
    shape: cq.Shape,
    source: cq.Shape,
) -> tuple[cq.Compound, float]:
    """Return service motion only after positive datum separation.

    The seated state is checked independently by the caller. The first service pose is
    a rigid +Y translation from that exact manufactured geometry. We require that pose
    to be clear before constructing the remaining continuous reference sweep.
    """
    unseated = shape.translate((0.0, SERVICE_UNSEAT_MM, 0.0))
    unseated_iv = intersection_volume_mm3(unseated, source)
    if unseated_iv > _INTERSECTION_TOLERANCE_MM3:
        raise TreatmentTerminalDatumPreloadV4Error(
            "positive-unseat service pose intersects source material"
        )
    sweep = translation_reference_compound(
        unseated,
        (0.0, SERVICE_REMAINING_RETRACTION_MM, 0.0),
    )
    return sweep, unseated_iv


def build_terminal_datum_preload_v4_architecture(
    *,
    model: MasckOneModel | None = None,
    reactions: StructuralFrameActuatorReactionArchitecture | None = None,
    mates: StructuralFrameActuatorMateArchitecture | None = None,
) -> TerminalDatumPreloadV4Architecture:
    model = build_model() if model is None else model
    reactions = (
        build_structural_frame_actuator_reactions(model=model)
        if reactions is None
        else reactions
    )
    mates = (
        build_structural_frame_actuator_mates(model=model, reactions=reactions)
        if mates is None
        else mates
    )
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
            cx=cx,
            contact_y=contact_y,
            side_sign=master_x_sign,
            clearance_mm=X_RUNNING_CLEARANCE_MM,
            phase_lead_mm=X_CAM_PHASE_LEAD_MM,
            depth_mm=MASTER_X_DEPTH_MM,
            z_span_mm=MASTER_X_Z_SPAN_MM,
            z_center=z_mid,
        )
        preload_x = _x_cam_pad(
            cx=cx,
            contact_y=contact_y,
            side_sign=preload_x_sign,
            clearance_mm=X_RUNNING_CLEARANCE_MM,
            phase_lead_mm=X_CAM_PHASE_LEAD_MM,
            depth_mm=PRELOAD_X_DEPTH_MM,
            z_span_mm=PRELOAD_X_Z_SPAN_MM,
            z_center=z_mid,
        )
        master_z = _z_cam_pad(
            contact_y=contact_y,
            contact_z=shoulder_z0,
            side_sign=-1.0,
            clearance_mm=Z_RUNNING_CLEARANCE_MM,
            phase_lead_mm=0.0,
            depth_mm=MASTER_Z_DEPTH_MM,
            x_span_mm=MASTER_Z_X_SPAN_MM,
            x_center=cx,
        )
        preload_z = _z_cam_pad(
            contact_y=contact_y,
            contact_z=shoulder_z1,
            side_sign=1.0,
            clearance_mm=Z_RUNNING_CLEARANCE_MM,
            phase_lead_mm=0.0,
            depth_mm=PRELOAD_Z_DEPTH_MM,
            x_span_mm=PRELOAD_Z_X_SPAN_MM,
            x_center=cx,
        )

        y_center = contact_y - FULL_SEAT_LAND_MM / 2.0
        x_shoe_outer = cx + preload_x_sign * (
            SHOULDER_WIDTH_MM / 2.0 + PRELOAD_X_DEPTH_MM
        )
        x_bumper_center = x_shoe_outer + preload_x_sign * (
            LOSSY_BACKUP_GAP_MM + BACKUP_BUMPER_THICKNESS_MM / 2.0
        )
        x_stop_center = x_shoe_outer + preload_x_sign * (
            LOSSY_BACKUP_GAP_MM
            + BACKUP_BUMPER_THICKNESS_MM
            + RIGID_BACKUP_THICKNESS_MM / 2.0
        )
        x_bumper = _box(
            BACKUP_BUMPER_THICKNESS_MM,
            FULL_SEAT_LAND_MM,
            PRELOAD_X_Z_SPAN_MM,
            (x_bumper_center, y_center, z_mid),
        )
        x_stop = _box(
            RIGID_BACKUP_THICKNESS_MM,
            FULL_SEAT_LAND_MM,
            PRELOAD_X_Z_SPAN_MM,
            (x_stop_center, y_center, z_mid),
        )

        z_shoe_outer = shoulder_z1 + PRELOAD_Z_DEPTH_MM
        z_bumper_center = (
            z_shoe_outer + LOSSY_BACKUP_GAP_MM + BACKUP_BUMPER_THICKNESS_MM / 2.0
        )
        z_stop_center = (
            z_shoe_outer
            + LOSSY_BACKUP_GAP_MM
            + BACKUP_BUMPER_THICKNESS_MM
            + RIGID_BACKUP_THICKNESS_MM / 2.0
        )
        z_bumper = _box(
            PRELOAD_Z_X_SPAN_MM,
            FULL_SEAT_LAND_MM,
            BACKUP_BUMPER_THICKNESS_MM,
            (cx, y_center, z_bumper_center),
        )
        z_stop = _box(
            PRELOAD_Z_X_SPAN_MM,
            FULL_SEAT_LAND_MM,
            RIGID_BACKUP_THICKNESS_MM,
            (cx, y_center, z_stop_center),
        )

        source = mate.mate.val()
        installed_parts = [master_x, master_z, preload_x, preload_z, x_stop, z_stop]
        installed = cq.Compound.makeCompound(installed_parts)
        nominal = intersection_volume_mm3(installed, source)
        if nominal > _INTERSECTION_TOLERANCE_MM3:
            raise TreatmentTerminalDatumPreloadV4Error(
                "nominal seated terminal geometry has positive source interference"
            )

        master_probe_x = intersection_volume_mm3(
            master_x.translate(
                (-master_x_sign * MASTER_ENGAGEMENT_PROBE_MM, 0.0, 0.0)
            ),
            source,
        )
        master_probe_z = intersection_volume_mm3(
            master_z.translate((0.0, 0.0, MASTER_ENGAGEMENT_PROBE_MM)),
            source,
        )

        service_parts: list[cq.Shape] = []
        unseat_intersections: list[float] = []
        for shape in installed_parts:
            sweep, unseat_iv = _service_reference_after_unseat(shape, source)
            service_parts.append(sweep)
            unseat_intersections.append(unseat_iv)
        if any(value > _INTERSECTION_TOLERANCE_MM3 for value in unseat_intersections):
            raise TreatmentTerminalDatumPreloadV4Error(
                "service unseat must clear every installed terminal part"
            )

        service = cq.Compound.makeCompound(service_parts)
        service_iv = intersection_volume_mm3(service, source)
        if service_iv > _INTERSECTION_TOLERANCE_MM3:
            raise TreatmentTerminalDatumPreloadV4Error(
                "post-unseat service withdrawal intersects source material"
            )

        built.append(
            TerminalDatumPreloadV3Station(
                mate.reaction_id,
                mate.center_xy_mm,
                (("rigid_master_x_v3", master_x), ("rigid_master_z_v3", master_z)),
                (("preload_x_outer_v3", preload_x), ("preload_z_outer_v3", preload_z)),
                (
                    ("x_lossy_backup_reference_v3", x_bumper),
                    ("z_lossy_backup_reference_v3", z_bumper),
                ),
                (
                    ("x_rigid_backup_stop_v3", x_stop),
                    ("z_rigid_backup_stop_v3", z_stop),
                ),
                service,
                round(nominal, 8),
                (round(master_probe_x, 8), round(master_probe_z, 8)),
                round(service_iv, 8),
                0.0,
            )
        )

    result = TerminalDatumPreloadV4Architecture(
        SOURCE_CELL6_HEAD_SHA,
        tuple(built),
        False,
    )
    result.__post_init__()
    return result


def export_terminal_datum_preload_v4_architecture(output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    architecture = build_terminal_datum_preload_v4_architecture()
    for station in architecture.stations:
        slug = station.reaction_id.lower()
        cq.exporters.export(
            cq.Compound.makeCompound([shape for _name, shape in station.master_parts]),
            str(output_dir / f"{slug}_terminal_master_datums_v4.step"),
        )
        cq.exporters.export(
            cq.Compound.makeCompound(
                [shape for _name, shape in station.preload_outer_parts]
            ),
            str(output_dir / f"{slug}_terminal_preload_outer_v4.step"),
        )
        cq.exporters.export(
            cq.Compound.makeCompound([shape for _name, shape in station.rigid_backup_parts]),
            str(output_dir / f"{slug}_terminal_rigid_backups_v4.step"),
        )
        cq.exporters.export(
            station.service_sweep,
            str(output_dir / f"{slug}_terminal_service_sweep_v4_REFERENCE.step"),
        )
    manifest = architecture.manifest()
    (output_dir / "treatment_terminal_datum_preload_v4_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest
