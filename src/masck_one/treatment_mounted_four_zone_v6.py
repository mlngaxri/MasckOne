from __future__ import annotations

"""Mounted four-zone V6: captured parallel-leaf terminal preload cassettes.

V5 explored integral polymer tongues to remove insert part count, but the terminal
preload is what prevents normal 40 Hz reaction from opening a microscopic gap at the
rigid master datum. Long-term preload relaxation therefore directly threatens rattle.

V6 keeps the deterministic V4 rigid master datums/backups and realizes a second V1
candidate that decouples those jobs:

- two parallel spring leaves per X/Z axis limit preload-shoe pitch/rock;
- X and Z stiffness are independently tuned to their 0.16/0.12 mm clearances;
- a dog-bone spring root is mechanically trapped by a treatment-owned carrier cage;
- the cage neck is narrower than the root head, so capture is geometric rather than
  overlap-as-attachment;
- the spring cassette remains clearance-relieved from the carrier over its flexing
  span and only maintains master-datum contact;
- rigid master datums carry normal working reaction;
- lossy backup then rigid stop remain the abnormal reverse-load hierarchy.

The spring cassette is a production-intent topology study, not a selected alloy or
manufacturing process. Forming, root encapsulation, friction, fatigue, corrosion,
wet chemistry, contact pressure, damping and acoustics remain physical/DFM gates.
"""

import json
import math
from pathlib import Path

import cadquery as cq

from studies.treatment_parallel_preload_flexure import (
    ENTRY_OVERCLOSURE_MM,
    LEAF_WIDTH_MM,
    SHEET_THICKNESS_MM,
    build_axis,
)

from .model import MasckOneModel, build_model
from .structural_frame_actuator_mates import (
    StructuralFrameActuatorMateArchitecture,
    build_structural_frame_actuator_mates,
)
from .structural_frame_actuator_reactions import (
    StructuralFrameActuatorReactionArchitecture,
    build_structural_frame_actuator_reactions,
)
from .treatment_carrier_counterpart import TreatmentCarrierCounterpartArchitecture
from .treatment_mounted_four_zone import (
    SERVICE_WITHDRAWAL_MM,
    MountedFourZoneArchitecture,
    MountedTreatmentStation,
    TreatmentMountedFourZoneError,
    _iv,
    _protected_targets,
    _source_targets,
    _translation_envelope,
)
from .treatment_mounted_four_zone_v4 import build_mounted_four_zone_architecture_v4
from .treatment_terminal_datum_preload import TerminalDatumPreloadArchitecture

SCHEMA_V6 = "MASCK_ONE_TREATMENT_MOUNTED_FOUR_ZONE_V6"
SOURCE_MAIN_SHA = "42fa11818184cde998c6df25d7c46d4fb0e4c3eb"
SOURCE_CELL6_HEAD_SHA = "fcccde02b31cc1c4e01136630d92e550e4e09a11"
SOURCE_TREATMENT_V4_HEAD_SHA = "7246c0c1787d28e9e5cb99c9fbcb0d6fbf7da7db"

LEAF_PAIR_GAP_MM = 0.20
ROOT_HEAD_TRANSVERSE_MM = 1.90
ROOT_HEAD_LENGTH_Y_MM = 0.80
ROOT_HEAD_THICKNESS_MM = 0.18
ROOT_TO_LEAF_OVERLAP_MM = 0.06
LEAF_TO_SHOE_OVERLAP_MM = 0.08

CAPTURE_BOSS_TRANSVERSE_MM = 2.40
CAPTURE_BOSS_LENGTH_Y_MM = 1.15
CAPTURE_BOSS_DEPTH_MM = 0.90
CAPTURE_CLEARANCE_SEED_MM = 0.01
CAPTURE_NECK_SIDE_CLEARANCE_MM = 0.02
ROOT_PULL_OUT_PROBE_MM = 0.18

FLEXURE_RELIEF_SIDE_CLEARANCE_MM = 0.05
FLEXURE_RELIEF_DEPTH_MM = 0.80
_INTERSECTION_TOLERANCE_MM3 = 1e-7


class TreatmentMountedFourZoneV6Error(TreatmentMountedFourZoneError):
    pass


def _box(x: float, y: float, z: float, center: tuple[float, float, float]) -> cq.Shape:
    if min(x, y, z) <= 0.0:
        raise TreatmentMountedFourZoneV6Error("V6 box dimensions must be positive")
    return cq.Workplane("XY").box(x, y, z).translate(center).val()


def _join(shapes: list[cq.Shape]) -> cq.Shape:
    if not shapes:
        raise TreatmentMountedFourZoneV6Error("cannot join empty V6 shape list")
    result = shapes[0]
    for shape in shapes[1:]:
        result = result.fuse(shape)
    result = result.clean()
    if not result.isValid() or not result.Solids():
        raise TreatmentMountedFourZoneV6Error("V6 joined geometry must remain valid")
    return result


def _x_leaf(
    *,
    root_x: float,
    tip_x: float,
    root_y: float,
    tip_y: float,
    z_center: float,
) -> cq.Shape:
    dx = tip_x - root_x
    dy = tip_y - root_y
    length = math.hypot(dx, dy)
    if length <= 0.0:
        raise TreatmentMountedFourZoneV6Error("X leaf span must be positive")
    angle = -math.degrees(math.atan2(dx, dy))
    shape = cq.Workplane("XY").box(SHEET_THICKNESS_MM, length, LEAF_WIDTH_MM).val()
    shape = shape.rotate((0.0, 0.0, 0.0), (0.0, 0.0, 1.0), angle)
    return shape.translate(((root_x + tip_x) / 2.0, (root_y + tip_y) / 2.0, z_center))


def _z_leaf(
    *,
    root_z: float,
    tip_z: float,
    root_y: float,
    tip_y: float,
    x_center: float,
) -> cq.Shape:
    dz = tip_z - root_z
    dy = tip_y - root_y
    length = math.hypot(dz, dy)
    if length <= 0.0:
        raise TreatmentMountedFourZoneV6Error("Z leaf span must be positive")
    angle = math.degrees(math.atan2(dz, dy))
    shape = cq.Workplane("XY").box(LEAF_WIDTH_MM, length, SHEET_THICKNESS_MM).val()
    shape = shape.rotate((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), angle)
    return shape.translate((x_center, (root_y + tip_y) / 2.0, (root_z + tip_z) / 2.0))


def _pair_offset() -> float:
    return LEAF_PAIR_GAP_MM / 2.0 + LEAF_WIDTH_MM / 2.0


def _build_x_cassette(datum_station) -> tuple[cq.Shape, cq.Shape, cq.Shape, cq.Shape, dict[str, float]]:
    shoe = dict(datum_station.preload_installed_parts)["preload_x_installed"]
    bb = shoe.BoundingBox()
    axis = build_axis("X")
    cx, _cy = datum_station.center_xy_mm
    sign = 1.0 if cx > 0.0 else -1.0
    installed_tip_x = (bb.xmax - SHEET_THICKNESS_MM / 2.0) if sign > 0.0 else (bb.xmin + SHEET_THICKNESS_MM / 2.0)
    root_x = installed_tip_x - sign * axis.target_deflection_mm
    tip_y = bb.ymin + LEAF_TO_SHOE_OVERLAP_MM
    root_y = bb.ymin - axis.selected_leaf_length_mm
    z_mid = 0.5 * (bb.zmin + bb.zmax)
    dz = _pair_offset()
    leaves = [
        _x_leaf(root_x=root_x, tip_x=installed_tip_x, root_y=root_y, tip_y=tip_y, z_center=z_mid - dz),
        _x_leaf(root_x=root_x, tip_x=installed_tip_x, root_y=root_y, tip_y=tip_y, z_center=z_mid + dz),
    ]
    head_y = root_y - ROOT_HEAD_LENGTH_Y_MM / 2.0 + ROOT_TO_LEAF_OVERLAP_MM
    head = _box(
        ROOT_HEAD_THICKNESS_MM,
        ROOT_HEAD_LENGTH_Y_MM,
        ROOT_HEAD_TRANSVERSE_MM,
        (root_x, head_y, z_mid),
    )
    cassette = _join([head, *leaves, shoe])

    boss = _box(
        CAPTURE_BOSS_DEPTH_MM,
        CAPTURE_BOSS_LENGTH_Y_MM,
        CAPTURE_BOSS_TRANSVERSE_MM,
        (root_x, head_y, z_mid),
    )
    cavity = _box(
        ROOT_HEAD_THICKNESS_MM + 2.0 * CAPTURE_CLEARANCE_SEED_MM,
        ROOT_HEAD_LENGTH_Y_MM + 2.0 * CAPTURE_CLEARANCE_SEED_MM,
        ROOT_HEAD_TRANSVERSE_MM + 2.0 * CAPTURE_CLEARANCE_SEED_MM,
        (root_x, head_y, z_mid),
    )
    neck_span = 2.0 * _pair_offset() + LEAF_WIDTH_MM + 2.0 * CAPTURE_NECK_SIDE_CLEARANCE_MM
    neck_y0 = head_y + ROOT_HEAD_LENGTH_Y_MM / 2.0 - CAPTURE_CLEARANCE_SEED_MM
    neck_y1 = root_y + ROOT_TO_LEAF_OVERLAP_MM + 0.10
    neck = _box(
        SHEET_THICKNESS_MM + 2.0 * CAPTURE_NECK_SIDE_CLEARANCE_MM,
        max(0.10, neck_y1 - neck_y0),
        neck_span,
        (root_x, 0.5 * (neck_y0 + neck_y1), z_mid),
    )
    relief_y0 = root_y + ROOT_TO_LEAF_OVERLAP_MM
    relief_y1 = bb.ymin + LEAF_TO_SHOE_OVERLAP_MM
    relief = _box(
        FLEXURE_RELIEF_DEPTH_MM,
        relief_y1 - relief_y0,
        neck_span + 2.0 * FLEXURE_RELIEF_SIDE_CLEARANCE_MM,
        (root_x, 0.5 * (relief_y0 + relief_y1), z_mid),
    )

    free_ref = cassette.translate((-sign * axis.target_deflection_mm, 0.0, 0.0))
    return cassette, free_ref, boss, _join([cavity, neck, relief]), head, {
        "axis_target_deflection_mm": axis.target_deflection_mm,
        "effective_leaf_length_mm": axis.selected_leaf_length_mm,
        "entry_force_N": axis.entry_force_N,
        "seated_preload_N": axis.seated_preload_N,
        "continuous_contact_margin_N": axis.continuous_contact_margin_N,
        "backup_first_engagement_force_N": axis.backup_first_engagement_force_N,
    }


def _build_z_cassette(datum_station) -> tuple[cq.Shape, cq.Shape, cq.Shape, cq.Shape, cq.Shape, dict[str, float]]:
    shoe = dict(datum_station.preload_installed_parts)["preload_z_installed"]
    bb = shoe.BoundingBox()
    axis = build_axis("Z")
    installed_tip_z = bb.zmax - SHEET_THICKNESS_MM / 2.0
    root_z = installed_tip_z - axis.target_deflection_mm
    tip_y = bb.ymin + LEAF_TO_SHOE_OVERLAP_MM
    root_y = bb.ymin - axis.selected_leaf_length_mm
    x_mid = 0.5 * (bb.xmin + bb.xmax)
    dx = _pair_offset()
    leaves = [
        _z_leaf(root_z=root_z, tip_z=installed_tip_z, root_y=root_y, tip_y=tip_y, x_center=x_mid - dx),
        _z_leaf(root_z=root_z, tip_z=installed_tip_z, root_y=root_y, tip_y=tip_y, x_center=x_mid + dx),
    ]
    head_y = root_y - ROOT_HEAD_LENGTH_Y_MM / 2.0 + ROOT_TO_LEAF_OVERLAP_MM
    head = _box(
        ROOT_HEAD_TRANSVERSE_MM,
        ROOT_HEAD_LENGTH_Y_MM,
        ROOT_HEAD_THICKNESS_MM,
        (x_mid, head_y, root_z),
    )
    cassette = _join([head, *leaves, shoe])

    boss = _box(
        CAPTURE_BOSS_TRANSVERSE_MM,
        CAPTURE_BOSS_LENGTH_Y_MM,
        CAPTURE_BOSS_DEPTH_MM,
        (x_mid, head_y, root_z),
    )
    cavity = _box(
        ROOT_HEAD_TRANSVERSE_MM + 2.0 * CAPTURE_CLEARANCE_SEED_MM,
        ROOT_HEAD_LENGTH_Y_MM + 2.0 * CAPTURE_CLEARANCE_SEED_MM,
        ROOT_HEAD_THICKNESS_MM + 2.0 * CAPTURE_CLEARANCE_SEED_MM,
        (x_mid, head_y, root_z),
    )
    neck_span = 2.0 * _pair_offset() + LEAF_WIDTH_MM + 2.0 * CAPTURE_NECK_SIDE_CLEARANCE_MM
    neck_y0 = head_y + ROOT_HEAD_LENGTH_Y_MM / 2.0 - CAPTURE_CLEARANCE_SEED_MM
    neck_y1 = root_y + ROOT_TO_LEAF_OVERLAP_MM + 0.10
    neck = _box(
        neck_span,
        max(0.10, neck_y1 - neck_y0),
        SHEET_THICKNESS_MM + 2.0 * CAPTURE_NECK_SIDE_CLEARANCE_MM,
        (x_mid, 0.5 * (neck_y0 + neck_y1), root_z),
    )
    relief_y0 = root_y + ROOT_TO_LEAF_OVERLAP_MM
    relief_y1 = bb.ymin + LEAF_TO_SHOE_OVERLAP_MM
    relief = _box(
        neck_span + 2.0 * FLEXURE_RELIEF_SIDE_CLEARANCE_MM,
        relief_y1 - relief_y0,
        FLEXURE_RELIEF_DEPTH_MM,
        (x_mid, 0.5 * (relief_y0 + relief_y1), root_z),
    )

    free_ref = cassette.translate((0.0, 0.0, -axis.target_deflection_mm))
    return cassette, free_ref, boss, _join([cavity, neck, relief]), head, {
        "axis_target_deflection_mm": axis.target_deflection_mm,
        "effective_leaf_length_mm": axis.selected_leaf_length_mm,
        "entry_force_N": axis.entry_force_N,
        "seated_preload_N": axis.seated_preload_N,
        "continuous_contact_margin_N": axis.continuous_contact_margin_N,
        "backup_first_engagement_force_N": axis.backup_first_engagement_force_N,
    }


def build_mounted_four_zone_architecture_v6(
    *,
    model: MasckOneModel | None = None,
    reactions: StructuralFrameActuatorReactionArchitecture | None = None,
    mates: StructuralFrameActuatorMateArchitecture | None = None,
    counterparts: TreatmentCarrierCounterpartArchitecture | None = None,
) -> tuple[MountedFourZoneArchitecture, TerminalDatumPreloadArchitecture]:
    model = build_model() if model is None else model
    reactions = build_structural_frame_actuator_reactions(model=model) if reactions is None else reactions
    mates = build_structural_frame_actuator_mates(model=model, reactions=reactions) if mates is None else mates
    base, datums = build_mounted_four_zone_architecture_v4(
        model=model,
        reactions=reactions,
        mates=mates,
        counterparts=counterparts,
    )
    datum_map = {item.reaction_id: item for item in datums.stations}
    _interfaces, _preload, _landing, _detent, source_targets = _source_targets(reactions, mates)

    built: list[MountedTreatmentStation] = []
    for station in base.stations:
        datum = datum_map[station.reaction_id]
        material = dict(station.material_parts)
        reference = {
            name: shape
            for name, shape in station.reference_parts
            if not name.startswith("terminal_preload_")
        }
        backbone = material["fixed_backbone"]

        x_cassette, x_free, x_boss, x_cut, x_head, x_screen = _build_x_cassette(datum)
        z_cassette, z_free, z_boss, z_cut, z_head, z_screen = _build_z_cassette(datum)

        backbone = backbone.fuse(x_boss).fuse(z_boss).cut(x_cut).cut(z_cut).clean()
        if not backbone.isValid() or len(backbone.Solids()) != 1:
            raise TreatmentMountedFourZoneV6Error(
                f"{station.reaction_id} capture-cage backbone is not one valid solid"
            )
        if _iv(x_cassette, backbone) > _INTERSECTION_TOLERANCE_MM3:
            raise TreatmentMountedFourZoneV6Error(f"{station.reaction_id} X cassette overlaps carrier cage")
        if _iv(z_cassette, backbone) > _INTERSECTION_TOLERANCE_MM3:
            raise TreatmentMountedFourZoneV6Error(f"{station.reaction_id} Z cassette overlaps carrier cage")
        x_pullout = _iv(x_head.translate((0.0, ROOT_PULL_OUT_PROBE_MM, 0.0)), backbone)
        z_pullout = _iv(z_head.translate((0.0, ROOT_PULL_OUT_PROBE_MM, 0.0)), backbone)
        if min(x_pullout, z_pullout) <= _INTERSECTION_TOLERANCE_MM3:
            raise TreatmentMountedFourZoneV6Error(
                f"{station.reaction_id} spring root lacks positive +Y dog-bone capture"
            )

        material["fixed_backbone"] = backbone
        material["terminal_x_parallel_preload_cassette"] = x_cassette
        material["terminal_z_parallel_preload_cassette"] = z_cassette
        reference["terminal_x_parallel_preload_free_reference"] = x_free
        reference["terminal_z_parallel_preload_free_reference"] = z_free

        z_values = [
            value
            for shape in material.values()
            for value in (shape.BoundingBox().zmin, shape.BoundingBox().zmax)
        ]
        protected_targets = _protected_targets(model, min(z_values) - 1.0, max(z_values) + 1.0)
        material_compound = cq.Compound.makeCompound(list(material.values()))
        nominal_source = {name: round(_iv(material_compound, target), 8) for name, target in source_targets}
        nominal_protected = {name: round(_iv(material_compound, target), 8) for name, target in protected_targets}
        nominal_shell = round(_iv(material_compound, model.shell.solid.val()), 8)

        operational = station.operational_sweep
        moving_names = {"moving_cup", "moving_rear_clamp", "moving_front_clamp", "moving_output_linkage"}
        fixed_targets = cq.Compound.makeCompound(
            [shape for name, shape in material.items() if name not in moving_names]
        )
        operational_fixed = round(_iv(operational, fixed_targets), 8)
        operational_source = round(sum(_iv(operational, target) for _name, target in source_targets), 8)
        operational_protected = round(sum(_iv(operational, target) for _name, target in protected_targets), 8)
        operational_shell = round(_iv(operational, model.shell.solid.val()), 8)

        service = cq.Compound.makeCompound(
            [_translation_envelope(shape, (0.0, SERVICE_WITHDRAWAL_MM, 0.0)) for shape in material.values()]
        )
        service_source = round(sum(_iv(service, target) for _name, target in source_targets), 8)
        service_protected = round(sum(_iv(service, target) for _name, target in protected_targets), 8)
        service_shell = round(_iv(service, model.shell.solid.val()), 8)

        truss_screen = dict(station.truss_screen)
        truss_screen["parallel_preload_cassette"] = {
            "X": x_screen,
            "Z": z_screen,
            "root_pullout_probe_mm": ROOT_PULL_OUT_PROBE_MM,
            "root_pullout_intersections_mm3": {"X": round(x_pullout, 8), "Z": round(z_pullout, 8)},
            "capture": (
                "DOG_BONE_ROOT_IN_NARROW_NECK_CAGE; NOMINAL_NO_MATERIAL_OVERLAP; "
                "POLYMER_OR_OTHER_LOSSY_CARRIER_SURROUND_CAN_DAMP_ROOT"
            ),
            "working_rule": (
                "PARALLEL_LEAVES_MAINTAIN_DATUM_CONTACT_AND_LIMIT_SHOE_TIP; "
                "RIGID_MASTER_DATUMS_CARRY_NORMAL_40HZ_REACTION"
            ),
            "physical_validation": (
                "OPEN_SPRING_GRADE_FORMING_ROOT_ENCAPSULATION_FATIGUE_CORROSION_CONTACT_FRICTION_"
                "WEAR_DAMPING_ACOUSTICS_WET_CHEMICAL_TOLERANCE_AND_PROCESS_CAPABILITY"
            ),
        }
        built.append(
            MountedTreatmentStation(
                station.reaction_id,
                station.treatment_center_mm,
                station.axis_angle_deg,
                tuple(material.items()),
                tuple(reference.items()),
                operational,
                service,
                nominal_source,
                nominal_protected,
                nominal_shell,
                operational_fixed,
                operational_source,
                operational_protected,
                operational_shell,
                service_source,
                service_protected,
                service_shell,
                truss_screen,
            )
        )

    architecture = MountedFourZoneArchitecture(
        base.source_counterpart_sha256,
        reactions.architecture_sha256,
        mates.architecture_sha256,
        tuple(built),
        False,
    )
    architecture.__post_init__()
    return architecture, datums


def manifest_v6(
    architecture: MountedFourZoneArchitecture,
    datums: TerminalDatumPreloadArchitecture,
) -> dict[str, object]:
    payload = architecture.manifest()
    payload["schema"] = SCHEMA_V6
    payload["source_main_sha"] = SOURCE_MAIN_SHA
    payload["source_cell6_head_sha"] = SOURCE_CELL6_HEAD_SHA
    payload["source_treatment_v4_head_sha"] = SOURCE_TREATMENT_V4_HEAD_SHA
    payload["terminal_datum_preload_architecture_sha256"] = datums.architecture_sha256
    payload["selected_buttery_candidate"] = (
        "CLEARANCE_RAIL -> ZERO_SLOPE_TERMINAL_CAM -> AXIS_TUNED_PARALLEL_PRELOAD_CASSETTES -> "
        "RIGID_MASTER_DATUMS -> MUTED_AXIAL_EVENT -> LOSSY_BACKUP -> RIGID_OVERLOAD_STOP"
    )
    payload["why_parallel_leaves"] = (
        "LIMIT_PRELOAD_SHOE_PITCH_AND_EDGE_LOADING_WHILE_KEEPING_COMPLIANCE_OFF_THE_NORMAL_WORKING_REACTION_PATH"
    )
    payload["why_captured_spring_candidate"] = (
        "REDUCES_LONG_TERM_PRELOAD_RELAXATION_RISK_VERSUS_UNQUALIFIED_INTEGRAL_POLYMER_WHILE_"
        "DOG_BONE_CAPTURE_AND_LOSSY_CARRIER_SURROUND_AVOID_A_LOOSE_HIGH_Q_ROOT"
    )
    payload["entry_overclosure_mm"] = ENTRY_OVERCLOSURE_MM
    payload["physical_validation_eligible"] = False
    payload["physical_validation"] = (
        "OPEN_NONLINEAR_FEA_SPRING_GRADE_FORMING_FATIGUE_ROOT_CAPTURE_WEAR_FRICTION_DAMPING_"
        "ACOUSTICS_CORROSION_WET_CHEMICAL_TOLERANCE_ASSEMBLY_AND_FORCE_TRAVEL"
    )
    return payload


def export_mounted_four_zone_architecture_v6(output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    architecture, datums = build_mounted_four_zone_architecture_v6()
    for station in architecture.stations:
        slug = station.reaction_id.lower()
        cq.exporters.export(
            cq.Compound.makeCompound([shape for _name, shape in station.material_parts]),
            str(output_dir / f"{slug}_mounted_station_v6_material.step"),
        )
        cq.exporters.export(
            cq.Compound.makeCompound([shape for _name, shape in station.reference_parts]),
            str(output_dir / f"{slug}_mounted_station_v6_reference.step"),
        )
        cq.exporters.export(station.service_sweep, str(output_dir / f"{slug}_service_v6_sweep.step"))
    manifest = manifest_v6(architecture, datums)
    (output_dir / "treatment_mounted_four_zone_v6_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest
