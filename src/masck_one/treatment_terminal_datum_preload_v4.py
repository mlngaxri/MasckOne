from __future__ import annotations

"""Terminal datum/preload V4: exact C2 cam, bridge-clear seat and staged service.

V4 preserves the selected moment-balanced V3 load-path intent while closing three
separate geometry defects found by strict exact-head verification.

First, the opposed Z master/preload pair is moved together 2.4 mm inboard on each
station. The Cell 6 compliant bridge is 3.0 mm wide in X and the previous 1.2 mm-wide
Z contact pair was centered directly over it. Moving both Z contacts together
preserves coaxial opposing resultants and the complete smooth take-up ramp while
creating a positive 0.30 mm nominal X gap to the bridge. The lossy backup and rigid
abnormal-load stop move with the same Z preload line.

Second, the terminal take-up profile is no longer an interpolating spline through
samples of smootherstep. Exact-head diagnostics found symmetric spline overshoot of
about 4.6e-5 mm in X and 2.6e-5 mm in Z at the nominal rigid seat. Smootherstep is
exactly a degree-5 Bezier with scalar control values [0,0,0,1,1,1], so V4 constructs
that exact Bezier ramp and then an exact flat seating land. The intended zero entry
slope/curvature and zero full-seat slope/curvature are preserved without penetration.

Third, service withdrawal no longer starts by prism-sweeping an exactly seated or
tangent datum. The nominal seated state is checked independently, then every terminal
part translates +Y by a small positive unseat distance before the remaining
Boolean-free continuous service reference is constructed.

No collision threshold is weakened. Manufactured seated geometry, positive master
engagement, positive-unseat state and remaining service motion all fail closed on
positive volumetric interference. Force, friction, fatigue, acoustics and subjective
feel remain physical-validation work.
"""

from dataclasses import dataclass
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
    FLEXURE_WIDTH_MM,
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
    POSTERIOR_EXTENSION_MM,
    PRELOAD_X_DEPTH_MM,
    PRELOAD_X_Z_SPAN_MM,
    PRELOAD_Z_DEPTH_MM,
    PRELOAD_Z_X_SPAN_MM,
    RIGID_BACKUP_THICKNESS_MM,
    TERMINAL_SERVICE_RETRACTION_PROBE_MM,
    _box,
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

# Exact degree-5 Bezier representation of smootherstep. For S(s), controls are
# [0,0,0,1,1,1]. Gap is clearance * (1-S), hence [c,c,c,0,0,0].
_EXACT_SMOOTHERSTEP_BEZIER_CONTROL_VALUES = (0.0, 0.0, 0.0, 1.0, 1.0, 1.0)

# Both Z contacts move together toward product center. Their relative X offset remains
# exactly zero, so the V3 no-preload-couple condition is preserved.
Z_DATUM_INBOARD_OFFSET_MM = 2.40
Z_DATUM_TO_BRIDGE_NOMINAL_X_GAP_MM = (
    Z_DATUM_INBOARD_OFFSET_MM
    - FLEXURE_WIDTH_MM / 2.0
    - max(MASTER_Z_X_SPAN_MM, PRELOAD_Z_X_SPAN_MM) / 2.0
)
Z_DATUM_TO_SHOULDER_EDGE_NOMINAL_X_MARGIN_MM = (
    SHOULDER_WIDTH_MM / 2.0
    - Z_DATUM_INBOARD_OFFSET_MM
    - max(MASTER_Z_X_SPAN_MM, PRELOAD_Z_X_SPAN_MM) / 2.0
)

if Z_DATUM_TO_BRIDGE_NOMINAL_X_GAP_MM <= 0.0:
    raise ValueError("Z datum relocation must positively clear the Cell 6 bridge")
if Z_DATUM_TO_SHOULDER_EDGE_NOMINAL_X_MARGIN_MM <= 0.0:
    raise ValueError("Z datum relocation must remain inside the rigid shoulder footprint")

SERVICE_UNSEAT_MM = 0.05
SERVICE_REMAINING_RETRACTION_MM = (
    TERMINAL_SERVICE_RETRACTION_PROBE_MM - SERVICE_UNSEAT_MM
)
if not (0.0 < SERVICE_UNSEAT_MM < TERMINAL_SERVICE_RETRACTION_PROBE_MM):
    raise ValueError("service unseat must be positive and smaller than full retraction")


class TreatmentTerminalDatumPreloadV4Error(ValueError):
    pass


def _exact_gap_bezier_controls(
    *,
    contact_y: float,
    clearance_mm: float,
    phase_lead_mm: float,
) -> tuple[tuple[float, float], ...]:
    """Return exact (y,gap) Bezier controls for the quintic C2 take-up ramp."""
    land_start = contact_y - FULL_SEAT_LAND_MM - phase_lead_mm
    start = land_start - CAM_TRAVEL_MM
    controls: list[tuple[float, float]] = []
    for index, smootherstep_control in enumerate(
        _EXACT_SMOOTHERSTEP_BEZIER_CONTROL_VALUES
    ):
        y = start + CAM_TRAVEL_MM * index / 5.0
        gap = clearance_mm * (1.0 - smootherstep_control)
        controls.append((y, gap))
    return tuple(controls)


def _exact_x_cam_pad(
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
    face_x = cx + side_sign * half
    controls = _exact_gap_bezier_controls(
        contact_y=contact_y,
        clearance_mm=clearance_mm,
        phase_lead_mm=phase_lead_mm,
    )
    inner_controls = tuple(
        (face_x + side_sign * gap, y) for y, gap in controls
    )
    start_y = controls[0][0]
    land_start_y = controls[-1][0]
    land_end_y = contact_y + POSTERIOR_EXTENSION_MM
    outer_x = face_x + side_sign * (clearance_mm + depth_mm)

    profile = (
        cq.Workplane("XY")
        .moveTo(*inner_controls[0])
        .bezier(inner_controls[1:], includeCurrent=True)
        .lineTo(face_x, land_end_y)
        .lineTo(outer_x, land_end_y)
        .lineTo(outer_x, start_y)
        .close()
    )
    shape = profile.extrude(z_span_mm).translate(
        (0.0, 0.0, z_center - z_span_mm / 2.0)
    ).val()
    if not shape.isValid() or len(shape.Solids()) != 1 or shape.Volume() <= 0.0:
        raise TreatmentTerminalDatumPreloadV4Error("exact X cam pad is invalid")
    bb = shape.BoundingBox()
    if side_sign > 0.0 and bb.xmin < face_x - 1e-9:
        raise TreatmentTerminalDatumPreloadV4Error("exact X cam crosses positive-side datum plane")
    if side_sign < 0.0 and bb.xmax > face_x + 1e-9:
        raise TreatmentTerminalDatumPreloadV4Error("exact X cam crosses negative-side datum plane")
    if bb.ymin > start_y + 1e-9 or bb.ymax < land_end_y - 1e-9:
        raise TreatmentTerminalDatumPreloadV4Error("exact X cam lost complete take-up/land span")
    if not land_start_y < land_end_y:
        raise TreatmentTerminalDatumPreloadV4Error("exact X cam requires positive flat land")
    return shape


def _exact_z_cam_pad(
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
    controls = _exact_gap_bezier_controls(
        contact_y=contact_y,
        clearance_mm=clearance_mm,
        phase_lead_mm=phase_lead_mm,
    )
    inner_controls = tuple(
        (y, contact_z + side_sign * gap) for y, gap in controls
    )
    start_y = controls[0][0]
    land_start_y = controls[-1][0]
    land_end_y = contact_y + POSTERIOR_EXTENSION_MM
    outer_z = contact_z + side_sign * (clearance_mm + depth_mm)

    profile = (
        cq.Workplane("YZ", origin=(x_center, 0.0, 0.0))
        .moveTo(*inner_controls[0])
        .bezier(inner_controls[1:], includeCurrent=True)
        .lineTo(land_end_y, contact_z)
        .lineTo(land_end_y, outer_z)
        .lineTo(start_y, outer_z)
        .close()
    )
    shape = profile.extrude(x_span_mm / 2.0, both=True).val()
    if not shape.isValid() or len(shape.Solids()) != 1 or shape.Volume() <= 0.0:
        raise TreatmentTerminalDatumPreloadV4Error("exact Z cam pad is invalid")
    bb = shape.BoundingBox()
    if side_sign > 0.0 and bb.zmin < contact_z - 1e-9:
        raise TreatmentTerminalDatumPreloadV4Error("exact Z cam crosses positive-side datum plane")
    if side_sign < 0.0 and bb.zmax > contact_z + 1e-9:
        raise TreatmentTerminalDatumPreloadV4Error("exact Z cam crosses negative-side datum plane")
    if bb.ymin > start_y + 1e-9 or bb.ymax < land_end_y - 1e-9:
        raise TreatmentTerminalDatumPreloadV4Error("exact Z cam lost complete take-up/land span")
    if not land_start_y < land_end_y:
        raise TreatmentTerminalDatumPreloadV4Error("exact Z cam requires positive flat land")
    return shape


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
            self.manifest(False), sort_keys=True, separators=(",", ":"), allow_nan=False
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
            "terminal_cam": {
                "profile": "EXACT_DEGREE_5_BEZIER_SMOOTHERSTEP_PLUS_EXACT_FLAT_LAND",
                "bezier_scalar_controls": list(
                    _EXACT_SMOOTHERSTEP_BEZIER_CONTROL_VALUES
                ),
                "cam_travel_mm": CAM_TRAVEL_MM,
                "full_seat_land_mm": FULL_SEAT_LAND_MM,
                "posterior_extension_mm": POSTERIOR_EXTENSION_MM,
                "entry_slope_intent": 0.0,
                "entry_curvature_intent": 0.0,
                "full_seat_slope_intent": 0.0,
                "full_seat_curvature_intent": 0.0,
                "interpolating_spline_removed": True,
                "collision_threshold_weakened": False,
            },
            "verification_revision": (
                "EXACT_C2_BEZIER_CAM_PLUS_BRIDGE_CLEAR_COAXIAL_Z_DATUM_PAIR_PLUS_"
                "BOOLEAN_FREE_REFERENCE_SWEEPS_AFTER_EXPLICIT_POSITIVE_DATUM_UNSEAT_"
                "WITH_SOLID_PAIR_VOLUMETRIC_COLLISION"
            ),
            "Z_datum_relocation": {
                "direction": "INBOARD_TOWARD_PRODUCT_CENTER_MIRRORED_BY_STATION",
                "pair_center_offset_mm": Z_DATUM_INBOARD_OFFSET_MM,
                "master_to_preload_relative_X_offset_mm": 0.0,
                "bridge_width_mm": FLEXURE_WIDTH_MM,
                "widest_Z_contact_span_mm": max(MASTER_Z_X_SPAN_MM, PRELOAD_Z_X_SPAN_MM),
                "nominal_bridge_X_gap_mm": Z_DATUM_TO_BRIDGE_NOMINAL_X_GAP_MM,
                "nominal_shoulder_edge_X_margin_mm": Z_DATUM_TO_SHOULDER_EDGE_NOMINAL_X_MARGIN_MM,
                "full_cam_travel_preserved": True,
                "collision_threshold_weakened": False,
            },
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


def _bbox_tuple(shape: cq.Shape) -> tuple[float, float, float, float, float, float]:
    bb = shape.BoundingBox()
    return (bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax)


def _service_reference_after_unseat(
    shape: cq.Shape,
    source: cq.Shape,
) -> tuple[cq.Compound, float]:
    unseated = shape.translate((0.0, SERVICE_UNSEAT_MM, 0.0))
    unseated_iv = intersection_volume_mm3(unseated, source)
    if unseated_iv > _INTERSECTION_TOLERANCE_MM3:
        raise TreatmentTerminalDatumPreloadV4Error(
            "positive-unseat service pose intersects source material: "
            f"intersection_mm3={unseated_iv:.12g}, "
            f"part_bbox={_bbox_tuple(shape)}, source_bbox={_bbox_tuple(source)}"
        )
    sweep = translation_reference_compound(
        unseated, (0.0, SERVICE_REMAINING_RETRACTION_MM, 0.0)
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
    frame_zmax = float(
        reactions.frame_with_reaction_counterparts.val().BoundingBox().zmax
    )
    shoulder_z0 = frame_zmax + SHOULDER_GAP_MM
    shoulder_z1 = shoulder_z0 + SHOULDER_THICKNESS_MM
    z_mid = 0.5 * (shoulder_z0 + shoulder_z1)

    built: list[TerminalDatumPreloadV3Station] = []
    for mate in mates.mates:
        cx, cy = mate.center_xy_mm
        contact_y = cy + SHOULDER_HEIGHT_MM / 2.0
        master_x_sign = 1.0 if cx < 0.0 else -1.0
        preload_x_sign = -master_x_sign
        z_contact_x = cx + master_x_sign * Z_DATUM_INBOARD_OFFSET_MM

        master_x = _exact_x_cam_pad(
            cx=cx,
            contact_y=contact_y,
            side_sign=master_x_sign,
            clearance_mm=X_RUNNING_CLEARANCE_MM,
            phase_lead_mm=X_CAM_PHASE_LEAD_MM,
            depth_mm=MASTER_X_DEPTH_MM,
            z_span_mm=MASTER_X_Z_SPAN_MM,
            z_center=z_mid,
        )
        preload_x = _exact_x_cam_pad(
            cx=cx,
            contact_y=contact_y,
            side_sign=preload_x_sign,
            clearance_mm=X_RUNNING_CLEARANCE_MM,
            phase_lead_mm=X_CAM_PHASE_LEAD_MM,
            depth_mm=PRELOAD_X_DEPTH_MM,
            z_span_mm=PRELOAD_X_Z_SPAN_MM,
            z_center=z_mid,
        )
        master_z = _exact_z_cam_pad(
            contact_y=contact_y,
            contact_z=shoulder_z0,
            side_sign=-1.0,
            clearance_mm=Z_RUNNING_CLEARANCE_MM,
            phase_lead_mm=0.0,
            depth_mm=MASTER_Z_DEPTH_MM,
            x_span_mm=MASTER_Z_X_SPAN_MM,
            x_center=z_contact_x,
        )
        preload_z = _exact_z_cam_pad(
            contact_y=contact_y,
            contact_z=shoulder_z1,
            side_sign=1.0,
            clearance_mm=Z_RUNNING_CLEARANCE_MM,
            phase_lead_mm=0.0,
            depth_mm=PRELOAD_Z_DEPTH_MM,
            x_span_mm=PRELOAD_Z_X_SPAN_MM,
            x_center=z_contact_x,
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
            (z_contact_x, y_center, z_bumper_center),
        )
        z_stop = _box(
            PRELOAD_Z_X_SPAN_MM,
            FULL_SEAT_LAND_MM,
            RIGID_BACKUP_THICKNESS_MM,
            (z_contact_x, y_center, z_stop_center),
        )

        source = mate.mate.val()
        named_installed_parts = (
            ("rigid_master_x_v3", master_x),
            ("rigid_master_z_v3", master_z),
            ("preload_x_outer_v3", preload_x),
            ("preload_z_outer_v3", preload_z),
            ("x_rigid_backup_stop_v3", x_stop),
            ("z_rigid_backup_stop_v3", z_stop),
        )
        nominal_by_part = {
            name: intersection_volume_mm3(shape, source)
            for name, shape in named_installed_parts
        }
        offending = {
            name: value
            for name, value in nominal_by_part.items()
            if value > _INTERSECTION_TOLERANCE_MM3
        }
        if offending:
            part_map = dict(named_installed_parts)
            detail = {
                name: {
                    "intersection_mm3": value,
                    "bbox": _bbox_tuple(part_map[name]),
                }
                for name, value in offending.items()
            }
            raise TreatmentTerminalDatumPreloadV4Error(
                f"{mate.reaction_id} nominal seated terminal interference: "
                f"{detail}; source_bbox={_bbox_tuple(source)}"
            )
        nominal = sum(nominal_by_part.values())

        master_probe_x = intersection_volume_mm3(
            master_x.translate(
                (-master_x_sign * MASTER_ENGAGEMENT_PROBE_MM, 0.0, 0.0)
            ),
            source,
        )
        master_probe_z = intersection_volume_mm3(
            master_z.translate((0.0, 0.0, MASTER_ENGAGEMENT_PROBE_MM)), source
        )

        service_parts: list[cq.Shape] = []
        unseat_intersections: dict[str, float] = {}
        for name, shape in named_installed_parts:
            sweep, unseat_iv = _service_reference_after_unseat(shape, source)
            service_parts.append(sweep)
            unseat_intersections[name] = unseat_iv
        offending_unseat = {
            name: value
            for name, value in unseat_intersections.items()
            if value > _INTERSECTION_TOLERANCE_MM3
        }
        if offending_unseat:
            raise TreatmentTerminalDatumPreloadV4Error(
                f"{mate.reaction_id} service unseat does not clear all parts: "
                f"{offending_unseat}"
            )

        service = cq.Compound.makeCompound(service_parts)
        service_iv = intersection_volume_mm3(service, source)
        if service_iv > _INTERSECTION_TOLERANCE_MM3:
            raise TreatmentTerminalDatumPreloadV4Error(
                f"{mate.reaction_id} post-unseat service withdrawal intersects source: "
                f"intersection_mm3={service_iv:.12g}"
            )

        built.append(
            TerminalDatumPreloadV3Station(
                mate.reaction_id,
                mate.center_xy_mm,
                (("rigid_master_x_v3", master_x), ("rigid_master_z_v3", master_z)),
                (("preload_x_outer_v3", preload_x), ("preload_z_outer_v3", preload_z)),
                (("x_lossy_backup_reference_v3", x_bumper), ("z_lossy_backup_reference_v3", z_bumper)),
                (("x_rigid_backup_stop_v3", x_stop), ("z_rigid_backup_stop_v3", z_stop)),
                service,
                round(nominal, 8),
                (round(master_probe_x, 8), round(master_probe_z, 8)),
                round(service_iv, 8),
                0.0,
            )
        )

    result = TerminalDatumPreloadV4Architecture(
        SOURCE_CELL6_HEAD_SHA, tuple(built), False
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
            cq.Compound.makeCompound([shape for _name, shape in station.preload_outer_parts]),
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
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest
