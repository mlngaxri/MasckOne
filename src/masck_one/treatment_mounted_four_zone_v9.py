from __future__ import annotations

"""Mounted four-zone V9: robust motion proof for the selected buttery terminal seat.

V9 preserves the V8 physical architecture but supersedes its reference-geometry
verification path. Historical V2/V8 builders fused swept-face prisms into one solid;
OpenCascade can return null topology for those reference unions even when the actual
manufactured B-reps are valid. V9 keeps manufactured material strict and uses
Boolean-free motion/service compounds plus solid-pair volumetric collision checks.

Physical force, friction, fatigue, wear, wet contamination, acoustics and subjective
feel remain validation gates. "Buttery" here names the design intent only.
"""

import json
import math
from pathlib import Path

import cadquery as cq
import numpy as np

from studies.treatment_terminal_mechanics_v2 import build_manifest as mechanics_manifest
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
from .treatment_carrier_counterpart import (
    TreatmentCarrierCounterpartArchitecture,
    build_treatment_carrier_counterparts,
)
from .treatment_guided_preload_spring import build_guided_preload_spring_station
from .treatment_mounted_four_zone import (
    OPERATIONAL_HALF_STROKE_MM,
    SERVICE_WITHDRAWAL_MM,
    STATION_AXIS_DEG,
    STATION_CENTERS_MM,
    MountedFourZoneArchitecture,
    MountedTreatmentStation,
    TreatmentMountedFourZoneError,
    _local_cassette_material,
    _moving_output_linkage,
    _pose,
    _protected_targets,
    _rigid_shoulder_yoke,
    _source_targets,
)
from .treatment_mounted_four_zone_v2 import _posterior_truss_v2
from .treatment_reference_geometry import (
    intersection_volume_mm3,
    translation_reference_compound,
)
from .treatment_terminal_datum_preload_v4 import (
    SERVICE_UNSEAT_MM,
    TerminalDatumPreloadV4Architecture,
    build_terminal_datum_preload_v4_architecture,
)

SCHEMA_V9 = "MASCK_ONE_TREATMENT_MOUNTED_FOUR_ZONE_V9"
SOURCE_MAIN_SHA = "42fa11818184cde998c6df25d7c46d4fb0e4c3eb"
SOURCE_CELL6_HEAD_SHA = "c38d481c9868fb705a0b4084b2961807209e504c"
SOURCE_FAILURE_EVIDENCE_HEAD = "b803b36ddd270c3bcebf696e267015bc535ca7c9"
_INTERSECTION_TOLERANCE_MM3 = 1e-7
SERVICE_REFERENCE_REMAINING_WITHDRAWAL_MM = SERVICE_WITHDRAWAL_MM - SERVICE_UNSEAT_MM
if SERVICE_REFERENCE_REMAINING_WITHDRAWAL_MM <= 0.0:
    raise ValueError("four-zone service withdrawal must exceed positive unseat distance")


class TreatmentMountedFourZoneV9Error(TreatmentMountedFourZoneError):
    pass


def _join_to_one(base: cq.Shape, additions: list[cq.Shape], label: str) -> cq.Shape:
    result = base
    for shape in additions:
        result = result.fuse(shape)
    result = result.clean()
    if not result.isValid() or len(result.Solids()) != 1:
        raise TreatmentMountedFourZoneV9Error(f"{label} must resolve to one fixed backbone solid")
    return result


def _service_reference_after_unseat(shape: cq.Shape) -> cq.Compound:
    """Build only the post-unseat continuous service reference.

    The exact seated state is verified independently through nominal collision checks.
    Starting the 3-D service reference after the same positive +Y unseat already used
    by terminal datum V4 prevents exact contact/tangency at t=0 from becoming fake
    swept material while preserving the complete 32 mm service endpoint.
    """
    unseated = shape.translate((0.0, SERVICE_UNSEAT_MM, 0.0))
    return translation_reference_compound(
        unseated,
        (0.0, SERVICE_REFERENCE_REMAINING_WITHDRAWAL_MM, 0.0),
    )


def _build_collision_robust_v2_base(
    *,
    model: MasckOneModel,
    reactions: StructuralFrameActuatorReactionArchitecture,
    mates: StructuralFrameActuatorMateArchitecture,
    counterparts: TreatmentCarrierCounterpartArchitecture | None,
) -> MountedFourZoneArchitecture:
    interfaces, preload, landing, detent, source_targets = _source_targets(reactions, mates)
    counterparts = (
        build_treatment_carrier_counterparts(
            interfaces=interfaces,
            preload=preload,
            landing=landing,
            detent=detent,
        )
        if counterparts is None
        else counterparts
    )
    counterpart_map = {item.reaction_id: item for item in counterparts.counterparts}
    frame_zmax = float(reactions.frame_with_reaction_counterparts.val().BoundingBox().zmax)
    local_material, local_reference = _local_cassette_material()

    built: list[MountedTreatmentStation] = []
    for reaction_id in REACTION_IDS:
        center = STATION_CENTERS_MM[reaction_id]
        angle = STATION_AXIS_DEG[reaction_id]
        reaction_xy = counterpart_map[reaction_id].center_xy_mm
        shoe = counterpart_map[reaction_id].shoe.val()
        yoke_backbone = _rigid_shoulder_yoke(reaction_id, shoe, frame_zmax, reaction_xy)
        truss, truss_screen = _posterior_truss_v2(
            reaction_id,
            center,
            angle,
            yoke_backbone,
            frame_zmax,
            reaction_xy,
        )

        posed = {name: _pose(shape, center, angle) for name, shape in local_material.items()}
        rear_capture = intersection_volume_mm3(truss, posed["fixed_cage"])
        if rear_capture <= _INTERSECTION_TOLERANCE_MM3:
            raise TreatmentMountedFourZoneV9Error(f"{reaction_id} revised truss lacks positive rear-cage capture")
        truss_screen["positive_rear_cage_capture_mm3"] = rear_capture
        backbone = yoke_backbone.fuse(truss).fuse(posed.pop("fixed_cage")).clean()
        if not backbone.isValid() or len(backbone.Solids()) != 1:
            raise TreatmentMountedFourZoneV9Error(f"{reaction_id} revised fixed backbone is not one solid")

        kind = "superior" if "SUPERIOR" in reaction_id else "inferior"
        moving_output = _moving_output_linkage(kind, center, angle)
        material = {"fixed_backbone": backbone, **posed, "moving_output_linkage": moving_output}
        references = {name: _pose(shape, center, angle) for name, shape in local_reference.items()}

        z_values = [
            value
            for shape in material.values()
            for value in (shape.BoundingBox().zmin, shape.BoundingBox().zmax)
        ]
        protected_targets = _protected_targets(model, min(z_values) - 1.0, max(z_values) + 1.0)
        material_compound = cq.Compound.makeCompound(list(material.values()))
        nominal_source = {
            name: round(intersection_volume_mm3(material_compound, target), 8)
            for name, target in source_targets
        }
        nominal_protected = {
            name: round(intersection_volume_mm3(material_compound, target), 8)
            for name, target in protected_targets
        }
        nominal_shell = round(intersection_volume_mm3(material_compound, model.shell.solid.val()), 8)

        axis = np.array(
            [math.sin(math.radians(angle)), 0.0, math.cos(math.radians(angle))],
            dtype=float,
        )
        moving_names = (
            "moving_cup",
            "moving_rear_clamp",
            "moving_front_clamp",
            "moving_output_linkage",
        )
        operational_travel = tuple(
            float(2.0 * OPERATIONAL_HALF_STROKE_MM * value) for value in axis
        )
        operational_pieces = []
        for name in moving_names:
            start = material[name].translate(
                tuple(float(-OPERATIONAL_HALF_STROKE_MM * value) for value in axis)
            )
            operational_pieces.append(
                translation_reference_compound(start, operational_travel)
            )
        operational = cq.Compound.makeCompound(operational_pieces)
        fixed_targets = cq.Compound.makeCompound(
            [
                material["fixed_backbone"],
                material["front_stop_ring"],
                material["front_buffer_inner"],
                material["front_buffer_outer"],
                material["rear_buffer"],
            ]
        )
        operational_fixed = round(intersection_volume_mm3(operational, fixed_targets), 8)
        operational_source = round(
            sum(intersection_volume_mm3(operational, target) for _name, target in source_targets),
            8,
        )
        operational_protected = round(
            sum(intersection_volume_mm3(operational, target) for _name, target in protected_targets),
            8,
        )
        operational_shell = round(
            intersection_volume_mm3(operational, model.shell.solid.val()),
            8,
        )

        service_pieces = [
            _service_reference_after_unseat(shape)
            for shape in material.values()
        ]
        service = cq.Compound.makeCompound(service_pieces)
        service_source = round(
            sum(intersection_volume_mm3(service, target) for _name, target in source_targets),
            8,
        )
        service_protected = round(
            sum(intersection_volume_mm3(service, target) for _name, target in protected_targets),
            8,
        )
        service_shell = round(intersection_volume_mm3(service, model.shell.solid.val()), 8)

        truss_screen = dict(truss_screen)
        truss_screen["reference_motion_verifier"] = (
            "BOOLEAN_FREE_FACE_PRISM_COMPOUNDS_WITH_SOLID_PAIR_VOLUMETRIC_COLLISION"
        )
        truss_screen["service_unseat_mm"] = SERVICE_UNSEAT_MM
        truss_screen["service_reference_remaining_withdrawal_mm"] = (
            SERVICE_REFERENCE_REMAINING_WITHDRAWAL_MM
        )
        built.append(
            MountedTreatmentStation(
                reaction_id,
                center,
                angle,
                tuple(material.items()),
                tuple(references.items()),
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
        counterparts.architecture_sha256,
        reactions.architecture_sha256,
        mates.architecture_sha256,
        tuple(built),
        False,
    )
    architecture.__post_init__()
    return architecture


def build_mounted_four_zone_architecture_v9(
    *,
    model: MasckOneModel | None = None,
    reactions: StructuralFrameActuatorReactionArchitecture | None = None,
    mates: StructuralFrameActuatorMateArchitecture | None = None,
    counterparts: TreatmentCarrierCounterpartArchitecture | None = None,
    terminal_datums: TerminalDatumPreloadV4Architecture | None = None,
) -> tuple[MountedFourZoneArchitecture, TerminalDatumPreloadV4Architecture]:
    model = build_model() if model is None else model
    reactions = build_structural_frame_actuator_reactions(model=model) if reactions is None else reactions
    mates = build_structural_frame_actuator_mates(model=model, reactions=reactions) if mates is None else mates
    base = _build_collision_robust_v2_base(
        model=model,
        reactions=reactions,
        mates=mates,
        counterparts=counterparts,
    )
    terminal_datums = (
        build_terminal_datum_preload_v4_architecture(
            model=model,
            reactions=reactions,
            mates=mates,
        )
        if terminal_datums is None
        else terminal_datums
    )
    datum_map = {item.reaction_id: item for item in terminal_datums.stations}
    _interfaces, _preload, _landing, _detent, source_targets = _source_targets(reactions, mates)

    built: list[MountedTreatmentStation] = []
    for station in base.stations:
        datum = datum_map[station.reaction_id]
        guided = build_guided_preload_spring_station(datum)
        material = dict(station.material_parts)
        reference = dict(station.reference_parts)
        backbone = material.pop("fixed_backbone")
        backbone = _join_to_one(
            backbone,
            [
                shape
                for _name, shape in datum.master_parts + datum.rigid_backup_parts + guided.root_polymer
            ],
            station.reaction_id,
        )

        installed_material: dict[str, cq.Shape] = {"fixed_backbone": backbone, **material}
        installed_material.update(dict(guided.installed_springs))
        installed_material.update(dict(guided.installed_shoes))

        spring_x = dict(guided.installed_springs)["terminal_x_spring_installed"]
        spring_z = dict(guided.installed_springs)["terminal_z_spring_installed"]
        shoe_x = dict(guided.installed_shoes)["terminal_x_preload_shoe"]
        shoe_z = dict(guided.installed_shoes)["terminal_z_preload_shoe"]
        partition_checks = {
            "x_spring_to_backbone": intersection_volume_mm3(spring_x, backbone),
            "z_spring_to_backbone": intersection_volume_mm3(spring_z, backbone),
            "x_spring_to_shoe": intersection_volume_mm3(spring_x, shoe_x),
            "z_spring_to_shoe": intersection_volume_mm3(spring_z, shoe_z),
            "x_to_z_spring": intersection_volume_mm3(spring_x, spring_z),
        }
        if max(partition_checks.values()) > _INTERSECTION_TOLERANCE_MM3:
            raise TreatmentMountedFourZoneV9Error(f"{station.reaction_id} V9 material domains overlap")

        for name, shape in guided.free_springs + guided.free_shoes + datum.lossy_backup_references:
            reference[name] = shape

        z_values = [
            value
            for shape in installed_material.values()
            for value in (shape.BoundingBox().zmin, shape.BoundingBox().zmax)
        ]
        protected_targets = _protected_targets(model, min(z_values) - 1.0, max(z_values) + 1.0)
        material_compound = cq.Compound.makeCompound(list(installed_material.values()))
        nominal_source = {
            name: round(intersection_volume_mm3(material_compound, target), 8)
            for name, target in source_targets
        }
        nominal_protected = {
            name: round(intersection_volume_mm3(material_compound, target), 8)
            for name, target in protected_targets
        }
        nominal_shell = round(
            intersection_volume_mm3(material_compound, model.shell.solid.val()),
            8,
        )

        moving_names = {
            "moving_cup",
            "moving_rear_clamp",
            "moving_front_clamp",
            "moving_output_linkage",
        }
        fixed_targets = cq.Compound.makeCompound(
            [shape for name, shape in installed_material.items() if name not in moving_names]
        )
        operational = station.operational_sweep
        operational_fixed = round(intersection_volume_mm3(operational, fixed_targets), 8)
        operational_source = round(
            sum(intersection_volume_mm3(operational, target) for _name, target in source_targets),
            8,
        )
        operational_protected = round(
            sum(intersection_volume_mm3(operational, target) for _name, target in protected_targets),
            8,
        )
        operational_shell = round(
            intersection_volume_mm3(operational, model.shell.solid.val()),
            8,
        )

        service_pieces = [
            _service_reference_after_unseat(shape)
            for shape in installed_material.values()
        ]
        service_pieces.extend(
            _service_reference_after_unseat(shape)
            for _name, shape in guided.free_springs + guided.free_shoes
        )
        service = cq.Compound.makeCompound(service_pieces)
        service_source = round(
            sum(intersection_volume_mm3(service, target) for _name, target in source_targets),
            8,
        )
        service_protected = round(
            sum(intersection_volume_mm3(service, target) for _name, target in protected_targets),
            8,
        )
        service_shell = round(intersection_volume_mm3(service, model.shell.solid.val()), 8)

        truss_screen = dict(station.truss_screen)
        truss_screen["terminal_datum_preload_v4"] = datum.manifest()
        truss_screen["guided_preload_spring_v9"] = guided.manifest()
        truss_screen["v9_material_partition_mm3"] = {
            name: round(value, 8) for name, value in partition_checks.items()
        }
        truss_screen["service_semantics_v9"] = (
            "SEATED_STATE_CHECKED_INDEPENDENTLY_THEN_0.05MM_POSITIVE_UNSEAT_PLUS_31.95MM_"
            "BOOLEAN_FREE_WITHDRAWAL_REFERENCE_FOR_INSTALLED_AND_FREE_ENDPOINT_STATES; "
            "NONLINEAR_SPRING_UNLOAD_PATH_REMAINS_PHYSICAL_FEA_VALIDATION"
        )

        built.append(
            MountedTreatmentStation(
                station.reaction_id,
                station.treatment_center_mm,
                station.axis_angle_deg,
                tuple(installed_material.items()),
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


def _axis_vector(angle_deg: float) -> list[float]:
    angle = math.radians(angle_deg)
    return [math.sin(angle), 0.0, math.cos(angle)]


def fusion_handoff_manifest(
    architecture: MountedFourZoneArchitecture,
    datums: TerminalDatumPreloadV4Architecture,
) -> dict[str, object]:
    mechanics = mechanics_manifest()
    datum_map = {row.reaction_id: row for row in datums.stations}
    stations: list[dict[str, object]] = []
    for station in architecture.stations:
        cx, cy, cz = station.treatment_center_mm
        stations.append(
            {
                "reaction_id": station.reaction_id,
                "local_origin_world_mm": [cx, cy, cz],
                "treatment_axis_world_unit": _axis_vector(station.axis_angle_deg),
                "station_rotation_about_world_Y_deg": station.axis_angle_deg,
                "carrier_insertion_direction_world_unit": [0.0, -1.0, 0.0],
                "carrier_service_withdrawal_direction_world_unit": [0.0, 1.0, 0.0],
                "service_withdrawal_mm": SERVICE_WITHDRAWAL_MM,
                "service_unseat_mm": SERVICE_UNSEAT_MM,
                "service_reference_after_unseat_mm": SERVICE_REFERENCE_REMAINING_WITHDRAWAL_MM,
                "functional_datums": {
                    "X_master": "rigid_master_x_v3",
                    "Z_master": "rigid_master_z_v3",
                    "final_Y_seat": "CELL6_LANDING_DETENT_STACK",
                    "treatment_origin": [cx, cy, cz],
                },
                "manufacturing_components": [
                    "fixed_backbone",
                    "terminal_x_spring_free",
                    "terminal_z_spring_free",
                    "terminal_x_preload_shoe",
                    "terminal_z_preload_shoe",
                    *[
                        name
                        for name, _shape in station.material_parts
                        if name
                        not in {
                            "fixed_backbone",
                            "terminal_x_spring_installed",
                            "terminal_z_spring_installed",
                            "terminal_x_preload_shoe",
                            "terminal_z_preload_shoe",
                        }
                    ],
                ],
                "installed_reference_components": [
                    "terminal_x_spring_installed",
                    "terminal_z_spring_installed",
                ],
                "joint_intent": {
                    "fixed_backbone": "RIGID_TO_CARRIER_FRAME_REACTION",
                    "preload_shoes": "COMPLIANT_RADIAL_TRANSLATION_VIA_PARALLELOGRAM_FLEXURE_NOT_A_RIGID_FUSION_JOINT",
                    "massage_stage": "COMPLIANT_TREATMENT_AXIS_MOTION_USE_REFERENCE_POSES_NOT_FAKE_SLIDER_FOR_FLEXURE",
                },
                "terminal_contact_alignment": datum_map[station.reaction_id]
                .manifest()["contact_resultant_alignment"],
            }
        )
    return {
        "schema": "MASCK_ONE_TREATMENT_FUSION_HANDOFF_V2",
        "cad_platform": "AUTODESK_FUSION_360",
        "repo_role": "DETERMINISTIC_PRODUCTION_INTENT_CAD_AND_DIGITAL_VERIFICATION_SOURCE",
        "fusion_role": "HUMAN_EDITABLE_ASSEMBLY_DFM_DRAWING_AND_PROTOTYPE_MANUFACTURING_ENVIRONMENT",
        "coordinate_frame": "+X_WEARER_RIGHT_+Y_SUPERIOR_+Z_ANTERIOR",
        "selected_terminal_mechanics": mechanics["selected_architecture"],
        "reference_sweep_semantics": (
            "BOOLEAN_FREE_COMPOUNDS_AFTER_EXPLICIT_POSITIVE_SERVICE_UNSEAT_NEVER_MANUFACTURED_MATERIAL"
        ),
        "stations": stations,
        "export_rules": {
            "manufactured_springs": "EXPORT_STRESS_FREE_BREP",
            "installed_spring_shapes": "REFERENCE_ONLY_PRELOADED_OCCUPIED_VOLUME",
            "sweeps_keepouts_protected": "REFERENCE_ONLY_NEVER_MERGE_WITH_MANUFACTURED_MATERIAL",
            "step_preference": "CLEAN_BREP_STEP_SUPPORTED_BY_CADQUERY_EXPORTER",
        },
        "physical_validation_eligible": False,
    }


def manifest_v9(
    architecture: MountedFourZoneArchitecture,
    datums: TerminalDatumPreloadV4Architecture,
) -> dict[str, object]:
    payload = architecture.manifest()
    payload.update(
        {
            "schema": SCHEMA_V9,
            "source_main_sha": SOURCE_MAIN_SHA,
            "source_cell6_head_sha": SOURCE_CELL6_HEAD_SHA,
            "source_failure_evidence_head": SOURCE_FAILURE_EVIDENCE_HEAD,
            "terminal_datum_v4_architecture_sha256": datums.architecture_sha256,
            "selected_buttery_candidate": (
                "LOW_DRAG_RAIL -> PHASED_C2_X_THEN_Z_TAKEUP -> COAXIAL_RIGID_MASTER_PRELOAD_PAIRS -> "
                "AXIS_SEPARATED_PARALLELOGRAM_SPRINGS -> ONE_FINAL_AXIAL_SEAT -> LOSSY_BACKUP -> RIGID_STOP"
            ),
            "verification_revision": (
                "MANUFACTURED_BREPS_STRICT; OPERATIONAL_MOTION_BOOLEAN_FREE_REFERENCE; "
                "SERVICE_SEATED_STATE_CHECKED_SEPARATELY_THEN_EXPLICIT_0.05MM_POSITIVE_UNSEAT_BEFORE_"
                "BOOLEAN_FREE_REMAINING_WITHDRAWAL_REFERENCE; COLLISION_SOLID_PAIR_VOLUMETRIC"
            ),
            "V8_rejection": (
                "SUPERSEDED_AS_CURRENT_CANDIDATE_BECAUSE_REFERENCE_SWEEP_BOOLEAN_FUSION_AND_EMPTY_COMMON_"
                "TOPOLOGY_COULD_FAIL_THE_KERNEL_WITHOUT_ESTABLISHING_POSITIVE_COLLISION"
            ),
            "physical_validation_eligible": False,
            "physical_validation": (
                "OPEN_NONLINEAR_FEA_SPRING_ALLOY_FORMING_FATIGUE_RELAXATION_CONTACT_PRESSURE_FRICTION_"
                "WEAR_CORROSION_WET_CHEMICAL_DAMPING_ACOUSTICS_FORCE_TRAVEL_SENSOR_ACTUATOR_AND_SUBJECTIVE_FEEL"
            ),
        }
    )
    payload["fusion_handoff"] = fusion_handoff_manifest(architecture, datums)
    return payload


def export_mounted_four_zone_architecture_v9(output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    architecture, datums = build_mounted_four_zone_architecture_v9()
    datum_map = {row.reaction_id: row for row in datums.stations}
    installed_station_shapes: list[cq.Shape] = []
    handoff = fusion_handoff_manifest(architecture, datums)

    for station in architecture.stations:
        slug = station.reaction_id.lower()
        material = dict(station.material_parts)
        reference = dict(station.reference_parts)
        for name, shape in material.items():
            suffix = "REFERENCE" if name.endswith("_spring_installed") else "MANUFACTURED"
            cq.exporters.export(shape, str(output_dir / f"{slug}_{name}_{suffix}.step"))
        for free_name in ("terminal_x_spring_free", "terminal_z_spring_free"):
            cq.exporters.export(
                reference[free_name],
                str(output_dir / f"{slug}_{free_name}_MANUFACTURED.step"),
            )
        installed = cq.Compound.makeCompound(list(material.values()))
        installed_station_shapes.append(installed)
        cq.exporters.export(
            installed,
            str(output_dir / f"{slug}_installed_station_assembly.step"),
        )
        cq.exporters.export(
            station.operational_sweep,
            str(output_dir / f"{slug}_operational_sweep_REFERENCE.step"),
        )
        cq.exporters.export(
            station.service_sweep,
            str(output_dir / f"{slug}_service_sweep_REFERENCE.step"),
        )
        station_manifest = {
            "reaction_id": station.reaction_id,
            "terminal_datum": datum_map[station.reaction_id].manifest(),
            "fusion_handoff": next(
                row for row in handoff["stations"] if row["reaction_id"] == station.reaction_id
            ),
        }
        (output_dir / f"{slug}_fusion_manifest.json").write_text(
            json.dumps(station_manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    cq.exporters.export(
        cq.Compound.makeCompound(installed_station_shapes),
        str(output_dir / "treatment_four_zone_installed_assembly_v9.step"),
    )
    manifest = manifest_v9(architecture, datums)
    (output_dir / "treatment_mounted_four_zone_v9_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "treatment_fusion_handoff_v2.json").write_text(
        json.dumps(manifest["fusion_handoff"], indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest