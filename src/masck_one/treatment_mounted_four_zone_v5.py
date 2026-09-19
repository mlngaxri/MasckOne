from __future__ import annotations

"""Mounted four-zone V5: integral terminal preload flexures.

V4 established deterministic rigid X/Z master datums and kept the preload shoes as
references because their spring-root capture was unresolved. V5 removes that extra
part/interface by cutting two local relief windows into the treatment-owned yoke and
reinstating the material as integral cantilever tongues:

- X tongue lives in the outboard side wall and bends in X;
- Z tongue lives in the outboard top lip and bends in Z;
- each tongue fuses directly into its zero-slope terminal cam shoe;
- one rigid master datum on the opposite side carries normal working reaction;
- rigid backups remain material; lossy bumper inserts remain references pending
  material/retention selection.

The flexures use a generic 2.5 GPa polymer study modulus only. This is not a material
selection and does not prove creep, fatigue, chemical compatibility or force.
"""

import json
from pathlib import Path

import cadquery as cq

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
    StructuralFrameActuatorReactionArchitecture,
    build_structural_frame_actuator_reactions,
)
from .treatment_carrier_counterpart import TreatmentCarrierCounterpartArchitecture
from .treatment_mounted_four_zone import (
    SERVICE_WITHDRAWAL_MM,
    YOKE_LIP_INSET_MM,
    YOKE_WALL_MM,
    YOKE_X_CLEARANCE_MM,
    YOKE_Z_CLEARANCE_MM,
    MountedFourZoneArchitecture,
    MountedTreatmentStation,
    TreatmentMountedFourZoneError,
    _iv,
    _protected_targets,
    _source_targets,
    _translation_envelope,
)
from .treatment_mounted_four_zone_v2 import build_mounted_four_zone_architecture_v2
from .treatment_terminal_datum_preload import (
    CAM_TRANSITION_TRAVEL_MM,
    FULL_SEAT_LAND_MM,
    SOURCE_CELL6_HEAD_SHA,
    TerminalDatumPreloadArchitecture,
    build_terminal_datum_preload_architecture,
)

SCHEMA_V5 = "MASCK_ONE_TREATMENT_MOUNTED_FOUR_ZONE_V5"
SOURCE_MAIN_SHA = "42fa11818184cde998c6df25d7c46d4fb0e4c3eb"
SOURCE_TREATMENT_HEAD_SHA = "7246c0c1787d28e9e5cb99c9fbcb0d6fbf7da7db"

POLYMER_MODULUS_STUDY_MPA = 2500.0
PRELOAD_TARGET_N = 0.30

X_FLEXURE_WIDTH_Z_MM = 1.40
X_FLEXURE_THICKNESS_X_MM = 0.45
X_FLEXURE_LENGTH_Y_MM = 3.50
Z_FLEXURE_WIDTH_X_MM = 1.00
Z_FLEXURE_THICKNESS_Z_MM = 0.45
Z_FLEXURE_LENGTH_Y_MM = 3.10
ROOT_OVERLAP_Y_MM = 0.45
RELIEF_SIDE_MARGIN_MM = 0.14
RELIEF_THROUGH_MARGIN_MM = 0.10
TIP_OVERLAP_INTO_CAM_MM = 0.20


def _box(x: float, y: float, z: float, center: tuple[float, float, float]) -> cq.Shape:
    if min(x, y, z) <= 0.0:
        raise TreatmentMountedFourZoneError("V5 box dimensions must be positive")
    return cq.Workplane("XY").box(x, y, z).translate(center).val()


def _cantilever_screen(*, width_mm: float, thickness_mm: float, length_mm: float) -> dict[str, float]:
    inertia = width_mm * thickness_mm**3 / 12.0
    stiffness = 3.0 * POLYMER_MODULUS_STUDY_MPA * inertia / length_mm**3
    deflection = PRELOAD_TARGET_N / stiffness
    stress = 6.0 * PRELOAD_TARGET_N * length_mm / (width_mm * thickness_mm**2)
    return {
        "modulus_study_MPa": POLYMER_MODULUS_STUDY_MPA,
        "width_mm": width_mm,
        "thickness_mm": thickness_mm,
        "length_mm": length_mm,
        "linear_tip_stiffness_N_per_mm": stiffness,
        "preload_target_N": PRELOAD_TARGET_N,
        "preload_deflection_seed_mm": deflection,
        "preload_root_stress_proxy_MPa": stress,
    }


def integral_flexure_screen() -> dict[str, object]:
    return {
        "x_flexure": _cantilever_screen(
            width_mm=X_FLEXURE_WIDTH_Z_MM,
            thickness_mm=X_FLEXURE_THICKNESS_X_MM,
            length_mm=X_FLEXURE_LENGTH_Y_MM,
        ),
        "z_flexure": _cantilever_screen(
            width_mm=Z_FLEXURE_WIDTH_X_MM,
            thickness_mm=Z_FLEXURE_THICKNESS_Z_MM,
            length_mm=Z_FLEXURE_LENGTH_Y_MM,
        ),
        "architecture_rule": (
            "FLEXURES_ONLY_MAINTAIN_DATUM_CONTACT; RIGID_MASTER_DATUMS_CARRY_NORMAL_40HZ_REACTION"
        ),
        "physical_validation": (
            "OPEN_EXACT_POLYMER_GRADE_CREEP_RELAXATION_NONLINEAR_STRESS_FATIGUE_MOLD_FLOW_"
            "WELD_LINES_ROOT_RADIUS_FORCE_TRAVEL_WEAR_WET_CHEMICAL_AND_TEMPERATURE"
        ),
    }


def _integral_flexures_for_station(
    *,
    reaction_id: str,
    center_xy_mm: tuple[float, float],
    frame_zmax: float,
    backbone: cq.Shape,
    datum_station,
) -> tuple[cq.Shape, dict[str, cq.Shape], dict[str, object]]:
    cx, cy = center_xy_mm
    shoulder_z0 = frame_zmax + SHOULDER_GAP_MM
    shoulder_z1 = shoulder_z0 + SHOULDER_THICKNESS_MM
    z_mid = 0.5 * (shoulder_z0 + shoulder_z1)
    contact_y = cy + SHOULDER_HEIGHT_MM / 2.0
    cam_start_y = contact_y - FULL_SEAT_LAND_MM - CAM_TRANSITION_TRAVEL_MM
    tip_y = cam_start_y + TIP_OVERLAP_INTO_CAM_MM

    master_x_sign = 1.0 if cx < 0.0 else -1.0
    preload_sign = -master_x_sign
    side_center_x = cx + preload_sign * (
        SHOULDER_WIDTH_MM / 2.0 + YOKE_X_CLEARANCE_MM + YOKE_WALL_MM / 2.0
    )

    # X preload tongue: relieve the local side wall around a narrow beam, leaving
    # ROOT_OVERLAP_Y_MM uncut so the beam is one-piece carrier material.
    x_start_y = tip_y - X_FLEXURE_LENGTH_Y_MM
    x_beam = _box(
        X_FLEXURE_THICKNESS_X_MM,
        X_FLEXURE_LENGTH_Y_MM,
        X_FLEXURE_WIDTH_Z_MM,
        (side_center_x, 0.5 * (x_start_y + tip_y), z_mid),
    )
    x_relief_start = x_start_y + ROOT_OVERLAP_Y_MM
    x_relief = _box(
        YOKE_WALL_MM + 2.0 * RELIEF_THROUGH_MARGIN_MM,
        tip_y - x_relief_start + RELIEF_SIDE_MARGIN_MM,
        X_FLEXURE_WIDTH_Z_MM + 2.0 * RELIEF_SIDE_MARGIN_MM,
        (
            side_center_x,
            0.5 * (x_relief_start + tip_y + RELIEF_SIDE_MARGIN_MM),
            z_mid,
        ),
    )

    # Z preload tongue: same principle inside the outboard top lip.
    top_lip_x = cx + preload_sign * (SHOULDER_WIDTH_MM / 2.0 - YOKE_LIP_INSET_MM / 2.0)
    top_lip_z = shoulder_z1 + YOKE_Z_CLEARANCE_MM + YOKE_WALL_MM / 2.0
    z_start_y = tip_y - Z_FLEXURE_LENGTH_Y_MM
    z_beam = _box(
        Z_FLEXURE_WIDTH_X_MM,
        Z_FLEXURE_LENGTH_Y_MM,
        Z_FLEXURE_THICKNESS_Z_MM,
        (top_lip_x, 0.5 * (z_start_y + tip_y), top_lip_z),
    )
    z_relief_start = z_start_y + ROOT_OVERLAP_Y_MM
    z_relief = _box(
        Z_FLEXURE_WIDTH_X_MM + 2.0 * RELIEF_SIDE_MARGIN_MM,
        tip_y - z_relief_start + RELIEF_SIDE_MARGIN_MM,
        YOKE_WALL_MM + 2.0 * RELIEF_THROUGH_MARGIN_MM,
        (
            top_lip_x,
            0.5 * (z_relief_start + tip_y + RELIEF_SIDE_MARGIN_MM),
            top_lip_z,
        ),
    )

    modified = backbone.cut(x_relief).cut(z_relief)
    preload_parts = dict(datum_station.preload_installed_parts)
    modified = modified.fuse(x_beam).fuse(preload_parts["preload_x_installed"])
    modified = modified.fuse(z_beam).fuse(preload_parts["preload_z_installed"])
    for _name, shape in datum_station.master_parts + datum_station.rigid_backup_parts:
        modified = modified.fuse(shape)
    modified = modified.clean()
    if not modified.isValid() or len(modified.Solids()) != 1:
        raise TreatmentMountedFourZoneError(
            f"{reaction_id} V5 integral flexure backbone is not one valid solid"
        )

    return (
        modified,
        {
            "x_flexure_beam": x_beam,
            "z_flexure_beam": z_beam,
            "x_relief_reference": x_relief,
            "z_relief_reference": z_relief,
        },
        integral_flexure_screen(),
    )


def build_mounted_four_zone_architecture_v5(
    *,
    model: MasckOneModel | None = None,
    reactions: StructuralFrameActuatorReactionArchitecture | None = None,
    mates: StructuralFrameActuatorMateArchitecture | None = None,
    counterparts: TreatmentCarrierCounterpartArchitecture | None = None,
    terminal_datums: TerminalDatumPreloadArchitecture | None = None,
) -> tuple[MountedFourZoneArchitecture, TerminalDatumPreloadArchitecture]:
    model = build_model() if model is None else model
    reactions = build_structural_frame_actuator_reactions(model=model) if reactions is None else reactions
    mates = build_structural_frame_actuator_mates(model=model, reactions=reactions) if mates is None else mates
    base = build_mounted_four_zone_architecture_v2(
        model=model,
        reactions=reactions,
        mates=mates,
        counterparts=counterparts,
    )
    terminal_datums = (
        build_terminal_datum_preload_architecture(model=model, reactions=reactions, mates=mates)
        if terminal_datums is None
        else terminal_datums
    )
    datum_map = {item.reaction_id: item for item in terminal_datums.stations}
    _interfaces, _preload, _landing, _detent, source_targets = _source_targets(reactions, mates)
    frame_zmax = float(reactions.frame_with_reaction_counterparts.val().BoundingBox().zmax)

    built: list[MountedTreatmentStation] = []
    for station in base.stations:
        datum = datum_map[station.reaction_id]
        material = dict(station.material_parts)
        reference = dict(station.reference_parts)
        backbone, flexure_refs, flexure_screen = _integral_flexures_for_station(
            reaction_id=station.reaction_id,
            center_xy_mm=datum.center_xy_mm,
            frame_zmax=frame_zmax,
            backbone=material["fixed_backbone"],
            datum_station=datum,
        )
        material["fixed_backbone"] = backbone

        # Free states and lossy inserts remain references. Installed preload shoes
        # are now material because they are integral with the relieved tongues.
        for name, shape in datum.preload_free_references:
            reference[f"terminal_{name}"] = shape
        for name, shape in datum.lossy_backup_references:
            reference[f"terminal_{name}"] = shape
        for name, shape in flexure_refs.items():
            reference[f"terminal_{name}"] = shape

        z_values = [
            value
            for shape in material.values()
            for value in (shape.BoundingBox().zmin, shape.BoundingBox().zmax)
        ]
        protected_targets = _protected_targets(model, min(z_values) - 1.0, max(z_values) + 1.0)
        material_compound = cq.Compound.makeCompound(list(material.values()))
        nominal_source = {
            name: round(_iv(material_compound, target), 8) for name, target in source_targets
        }
        nominal_protected = {
            name: round(_iv(material_compound, target), 8) for name, target in protected_targets
        }
        nominal_shell = round(_iv(material_compound, model.shell.solid.val()), 8)

        operational = station.operational_sweep
        fixed_targets = cq.Compound.makeCompound(
            [
                material["fixed_backbone"],
                material["front_stop_ring"],
                material["front_buffer_inner"],
                material["front_buffer_outer"],
                material["rear_buffer"],
            ]
        )
        operational_fixed = round(_iv(operational, fixed_targets), 8)
        operational_source = round(
            sum(_iv(operational, target) for _name, target in source_targets), 8
        )
        operational_protected = round(
            sum(_iv(operational, target) for _name, target in protected_targets), 8
        )
        operational_shell = round(_iv(operational, model.shell.solid.val()), 8)

        service = cq.Compound.makeCompound(
            [
                _translation_envelope(shape, (0.0, SERVICE_WITHDRAWAL_MM, 0.0))
                for shape in material.values()
            ]
        )
        service_source = round(
            sum(_iv(service, target) for _name, target in source_targets), 8
        )
        service_protected = round(
            sum(_iv(service, target) for _name, target in protected_targets), 8
        )
        service_shell = round(_iv(service, model.shell.solid.val()), 8)

        truss_screen = dict(station.truss_screen)
        truss_screen["terminal_datum_preload"] = datum.manifest()
        truss_screen["integral_preload_flexure"] = flexure_screen
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
    return architecture, terminal_datums


def manifest_v5(
    architecture: MountedFourZoneArchitecture,
    terminal_datums: TerminalDatumPreloadArchitecture,
) -> dict[str, object]:
    payload = architecture.manifest()
    payload["schema"] = SCHEMA_V5
    payload["source_main_sha"] = SOURCE_MAIN_SHA
    payload["source_cell6_head_sha"] = SOURCE_CELL6_HEAD_SHA
    payload["source_treatment_head_sha"] = SOURCE_TREATMENT_HEAD_SHA
    payload["terminal_datum_preload_architecture_sha256"] = terminal_datums.architecture_sha256
    payload["integral_preload_flexure_screen"] = integral_flexure_screen()
    payload["mechanical_status"] = (
        "FOUR_MOUNTED_STATION_V5_CANDIDATES_WITH_DETERMINISTIC_MASTER_DATUMS_AND_INTEGRAL_RELIEVED_"
        "PRELOAD_TONGUES; LOSSY_BACKUP_INSERT_MATERIAL_AND_PHYSICAL_RESPONSE_OPEN"
    )
    payload["part_count_change_vs_spring_insert_direction"] = (
        "REMOVES_SEPARATE_X_Z_SPRING_INSERTS_AND_THEIR_ROOT_CAPTURE_INTERFACES"
    )
    payload["buttery_mechanics_intent"] = (
        "FREE_RAIL_APPROACH -> ZERO_SLOPE_CAM_TAKEUP -> CONTINUOUS_DATUM_PRELOAD -> MUTED_AXIAL_SEAT; "
        "NO_NORMAL_40HZ_GAP_CYCLING_OR_SPRING_METAL_RING_PATH"
    )
    payload["physical_validation_eligible"] = False
    payload["physical_validation"] = (
        "OPEN_POLYMER_GRADE_CREEP_FATIGUE_MOLD_ROOT_FORCE_TRAVEL_WEAR_ACOUSTICS_LOSSY_BUMPER_"
        "MATERIAL_WET_CHEMICAL_TEMPERATURE_AND_PROCESS_CAPABILITY"
    )
    payload["supersedes_as_v1_baseline"] = "MASCK_ONE_TREATMENT_MOUNTED_FOUR_ZONE_V4"
    return payload


def export_mounted_four_zone_architecture_v5(output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    architecture, terminal_datums = build_mounted_four_zone_architecture_v5()
    for station in architecture.stations:
        slug = station.reaction_id.lower()
        cq.exporters.export(
            cq.Compound.makeCompound([shape for _name, shape in station.material_parts]),
            str(output_dir / f"{slug}_mounted_station_v5_material.step"),
        )
        cq.exporters.export(
            cq.Compound.makeCompound([shape for _name, shape in station.reference_parts]),
            str(output_dir / f"{slug}_mounted_station_v5_reference.step"),
        )
        cq.exporters.export(station.service_sweep, str(output_dir / f"{slug}_service_v5_sweep.step"))
    manifest = manifest_v5(architecture, terminal_datums)
    (output_dir / "treatment_mounted_four_zone_v5_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest
