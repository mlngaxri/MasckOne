from __future__ import annotations

"""Mounted four-zone V8: moment-balanced datums plus true guided preload shoes.

V8 is a material architecture change, not a cosmetic version increment. It supersedes
V7 because V7's intended terminal contacts created an unbalanced preload couple and
its transverse spring pair did not intrinsically guide shoe rotation.

V8 retains the collision-cleared V2 posterior treatment backbone and replaces only
the terminal precision seat:

low-drag Cell 6 rail -> phased C2 X/Z take-up -> coaxial rigid datum pairs ->
axis-separated parallelogram preload springs -> one final axial seat -> lossy backup
-> rigid overload stop.

The free spring B-rep is the manufacturing definition. The installed spring B-rep is
an elastically preloaded occupied-volume reference used for installed collision checks.
"""

import json
import math
from pathlib import Path

import cadquery as cq
import numpy as np

from studies.treatment_terminal_mechanics_v2 import build_manifest as mechanics_manifest
from .model import MasckOneModel, build_model
from .structural_frame_actuator_mates import StructuralFrameActuatorMateArchitecture, build_structural_frame_actuator_mates
from .structural_frame_actuator_reactions import StructuralFrameActuatorReactionArchitecture, build_structural_frame_actuator_reactions
from .treatment_carrier_counterpart import TreatmentCarrierCounterpartArchitecture
from .treatment_guided_preload_spring import build_guided_preload_spring_station
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
from .treatment_mounted_four_zone_v2 import build_mounted_four_zone_architecture_v2
from .treatment_terminal_datum_preload_v3 import (
    TerminalDatumPreloadV3Architecture,
    build_terminal_datum_preload_v3_architecture,
)

SCHEMA_V8 = "MASCK_ONE_TREATMENT_MOUNTED_FOUR_ZONE_V8"
SOURCE_MAIN_SHA = "42fa11818184cde998c6df25d7c46d4fb0e4c3eb"
SOURCE_CELL6_HEAD_SHA = "fcccde02b31cc1c4e01136630d92e550e4e09a11"
SOURCE_FAILURE_EVIDENCE_HEAD = "b803b36ddd270c3bcebf696e267015bc535ca7c9"
_INTERSECTION_TOLERANCE_MM3 = 1e-7


class TreatmentMountedFourZoneV8Error(TreatmentMountedFourZoneError):
    pass


def _join_to_one(base: cq.Shape, additions: list[cq.Shape], label: str) -> cq.Shape:
    result = base
    for shape in additions:
        result = result.fuse(shape)
    result = result.clean()
    if not result.isValid() or len(result.Solids()) != 1:
        raise TreatmentMountedFourZoneV8Error(f"{label} must resolve to one fixed backbone solid")
    return result


def build_mounted_four_zone_architecture_v8(
    *,
    model: MasckOneModel | None = None,
    reactions: StructuralFrameActuatorReactionArchitecture | None = None,
    mates: StructuralFrameActuatorMateArchitecture | None = None,
    counterparts: TreatmentCarrierCounterpartArchitecture | None = None,
    terminal_datums: TerminalDatumPreloadV3Architecture | None = None,
) -> tuple[MountedFourZoneArchitecture, TerminalDatumPreloadV3Architecture]:
    model = build_model() if model is None else model
    reactions = build_structural_frame_actuator_reactions(model=model) if reactions is None else reactions
    mates = build_structural_frame_actuator_mates(model=model, reactions=reactions) if mates is None else mates
    base = build_mounted_four_zone_architecture_v2(model=model, reactions=reactions, mates=mates, counterparts=counterparts)
    terminal_datums = build_terminal_datum_preload_v3_architecture(model=model, reactions=reactions, mates=mates) if terminal_datums is None else terminal_datums
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
            [shape for _name, shape in datum.master_parts + datum.rigid_backup_parts + guided.root_polymer],
            station.reaction_id,
        )

        # Installed occupied material. The stress-free spring remains a manufacturing
        # component reference and is exported separately; it is not double-counted in
        # the installed assembly.
        installed_material: dict[str, cq.Shape] = {"fixed_backbone": backbone, **material}
        installed_material.update(dict(guided.installed_springs))
        installed_material.update(dict(guided.installed_shoes))

        # Keep physically distinct material domains non-overlapping. Contact at a
        # zero-volume boundary is permitted; positive overlap is not.
        spring_x = dict(guided.installed_springs)["terminal_x_spring_installed"]
        spring_z = dict(guided.installed_springs)["terminal_z_spring_installed"]
        shoe_x = dict(guided.installed_shoes)["terminal_x_preload_shoe"]
        shoe_z = dict(guided.installed_shoes)["terminal_z_preload_shoe"]
        partition_checks = {
            "x_spring_to_backbone": _iv(spring_x, backbone),
            "z_spring_to_backbone": _iv(spring_z, backbone),
            "x_spring_to_shoe": _iv(spring_x, shoe_x),
            "z_spring_to_shoe": _iv(spring_z, shoe_z),
            "x_to_z_spring": _iv(spring_x, spring_z),
        }
        if max(partition_checks.values()) > _INTERSECTION_TOLERANCE_MM3:
            raise TreatmentMountedFourZoneV8Error(f"{station.reaction_id} V8 material domains overlap")

        for name, shape in guided.free_springs + guided.free_shoes + datum.lossy_backup_references:
            reference[name] = shape

        z_values = [value for shape in installed_material.values() for value in (shape.BoundingBox().zmin, shape.BoundingBox().zmax)]
        protected_targets = _protected_targets(model, min(z_values) - 1.0, max(z_values) + 1.0)
        material_compound = cq.Compound.makeCompound(list(installed_material.values()))
        nominal_source = {name: round(_iv(material_compound, target), 8) for name, target in source_targets}
        nominal_protected = {name: round(_iv(material_compound, target), 8) for name, target in protected_targets}
        nominal_shell = round(_iv(material_compound, model.shell.solid.val()), 8)

        moving_names = {"moving_cup", "moving_rear_clamp", "moving_front_clamp", "moving_output_linkage"}
        fixed_targets = cq.Compound.makeCompound([shape for name, shape in installed_material.items() if name not in moving_names])
        operational = station.operational_sweep
        operational_fixed = round(_iv(operational, fixed_targets), 8)
        operational_source = round(sum(_iv(operational, target) for _name, target in source_targets), 8)
        operational_protected = round(sum(_iv(operational, target) for _name, target in protected_targets), 8)
        operational_shell = round(_iv(operational, model.shell.solid.val()), 8)

        # Conservative service envelope includes both fully seated installed material
        # and stress-free endpoint spring/shoe states translated through the full
        # +Y withdrawal. It does not claim the nonlinear elastic transition path.
        service_pieces = [_translation_envelope(shape, (0.0, SERVICE_WITHDRAWAL_MM, 0.0)) for shape in installed_material.values()]
        service_pieces.extend(_translation_envelope(shape, (0.0, SERVICE_WITHDRAWAL_MM, 0.0)) for _name, shape in guided.free_springs + guided.free_shoes)
        service = cq.Compound.makeCompound(service_pieces)
        service_source = round(sum(_iv(service, target) for _name, target in source_targets), 8)
        service_protected = round(sum(_iv(service, target) for _name, target in protected_targets), 8)
        service_shell = round(_iv(service, model.shell.solid.val()), 8)

        truss_screen = dict(station.truss_screen)
        truss_screen["terminal_datum_preload_v3"] = datum.manifest()
        truss_screen["guided_preload_spring_v8"] = guided.manifest()
        truss_screen["v8_material_partition_mm3"] = {name: round(value, 8) for name, value in partition_checks.items()}
        truss_screen["service_semantics_v8"] = (
            "FULL_32MM_RIGID_WITHDRAWAL_ENVELOPES_FOR_INSTALLED_AND_FREE_ENDPOINT_STATES; "
            "NONLINEAR_SPRING_UNLOAD_PATH_REMAINS_PHYSICAL_FEA_VALIDATION"
        )

        built.append(MountedTreatmentStation(
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
        ))

    architecture = MountedFourZoneArchitecture(base.source_counterpart_sha256, reactions.architecture_sha256, mates.architecture_sha256, tuple(built), False)
    architecture.__post_init__()
    return architecture, terminal_datums


def _axis_vector(angle_deg: float) -> list[float]:
    angle = math.radians(angle_deg)
    return [math.sin(angle), 0.0, math.cos(angle)]


def fusion_handoff_manifest(architecture: MountedFourZoneArchitecture, datums: TerminalDatumPreloadV3Architecture) -> dict[str, object]:
    mechanics = mechanics_manifest()
    stations = []
    datum_map = {row.reaction_id: row for row in datums.stations}
    for station in architecture.stations:
        cx, cy, cz = station.treatment_center_mm
        stations.append({
            "reaction_id": station.reaction_id,
            "local_origin_world_mm": [cx, cy, cz],
            "treatment_axis_world_unit": _axis_vector(station.axis_angle_deg),
            "station_rotation_about_world_Y_deg": station.axis_angle_deg,
            "carrier_insertion_direction_world_unit": [0.0, -1.0, 0.0],
            "carrier_service_withdrawal_direction_world_unit": [0.0, 1.0, 0.0],
            "service_withdrawal_mm": SERVICE_WITHDRAWAL_MM,
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
                *[name for name, _shape in station.material_parts if name not in {"fixed_backbone", "terminal_x_spring_installed", "terminal_z_spring_installed", "terminal_x_preload_shoe", "terminal_z_preload_shoe"}],
            ],
            "installed_reference_components": ["terminal_x_spring_installed", "terminal_z_spring_installed"],
            "joint_intent": {
                "fixed_backbone": "RIGID_TO_CARRIER_FRAME_REACTION",
                "preload_shoes": "COMPLIANT_RADIAL_TRANSLATION_VIA_PARALLELOGRAM_FLEXURE_NOT_A_RIGID_FUSION_JOINT",
                "massage_stage": "COMPLIANT_TREATMENT_AXIS_MOTION_USE_REFERENCE_POSES_NOT_FAKE_SLIDER_FOR_FLEXURE",
            },
            "terminal_contact_alignment": datum_map[station.reaction_id].manifest()["contact_resultant_alignment"],
        })
    return {
        "schema": "MASCK_ONE_TREATMENT_FUSION_HANDOFF_V1",
        "cad_platform": "AUTODESK_FUSION_360",
        "repo_role": "DETERMINISTIC_PRODUCTION_INTENT_CAD_AND_DIGITAL_VERIFICATION_SOURCE",
        "fusion_role": "HUMAN_EDITABLE_ASSEMBLY_DFM_DRAWING_AND_PROTOTYPE_MANUFACTURING_ENVIRONMENT",
        "coordinate_frame": "+X_WEARER_RIGHT_+Y_SUPERIOR_+Z_ANTERIOR",
        "selected_terminal_mechanics": mechanics["selected_architecture"],
        "stations": stations,
        "export_rules": {
            "manufactured_springs": "EXPORT_STRESS_FREE_BREP",
            "installed_spring_shapes": "REFERENCE_ONLY_PRELOADED_OCCUPIED_VOLUME",
            "sweeps_keepouts_protected": "REFERENCE_ONLY_NEVER_MERGE_WITH_MANUFACTURED_MATERIAL",
            "step_preference": "CLEAN_BREP_STEP_SUPPORTED_BY_CADQUERY_EXPORTER",
        },
        "physical_validation_eligible": False,
    }


def manifest_v8(architecture: MountedFourZoneArchitecture, datums: TerminalDatumPreloadV3Architecture) -> dict[str, object]:
    payload = architecture.manifest()
    payload.update({
        "schema": SCHEMA_V8,
        "source_main_sha": SOURCE_MAIN_SHA,
        "source_cell6_head_sha": SOURCE_CELL6_HEAD_SHA,
        "source_failure_evidence_head": SOURCE_FAILURE_EVIDENCE_HEAD,
        "terminal_datum_v3_architecture_sha256": datums.architecture_sha256,
        "selected_buttery_candidate": (
            "LOW_DRAG_RAIL -> PHASED_C2_X_THEN_Z_TAKEUP -> COAXIAL_RIGID_MASTER_PRELOAD_PAIRS -> "
            "AXIS_SEPARATED_PARALLELOGRAM_SPRINGS -> ONE_FINAL_AXIAL_SEAT -> LOSSY_BACKUP -> RIGID_STOP"
        ),
        "V7_rejection": (
            "REJECTED_AS_CURRENT_CANDIDATE_UNBALANCED_TERMINAL_PRELOAD_COUPLE_AND_TRANSVERSE_LEAF_PAIR_"
            "DID_NOT_INTRINSICALLY_GUIDE_SHOE_ROTATION"
        ),
        "physical_validation_eligible": False,
        "physical_validation": (
            "OPEN_NONLINEAR_FEA_SPRING_ALLOY_FORMING_FATIGUE_RELAXATION_CONTACT_PRESSURE_FRICTION_"
            "WEAR_CORROSION_WET_CHEMICAL_DAMPING_ACOUSTICS_FORCE_TRAVEL_SENSOR_ACTUATOR_AND_SUBJECTIVE_FEEL"
        ),
    })
    payload["fusion_handoff"] = fusion_handoff_manifest(architecture, datums)
    return payload


def export_mounted_four_zone_architecture_v8(output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    architecture, datums = build_mounted_four_zone_architecture_v8()
    datum_map = {row.reaction_id: row for row in datums.stations}
    installed_station_shapes = []
    for station in architecture.stations:
        slug = station.reaction_id.lower()
        material = dict(station.material_parts)
        reference = dict(station.reference_parts)
        for name, shape in material.items():
            # Installed spring shapes are reference occupied volumes, not the
            # manufactured stress-free component.
            suffix = "REFERENCE" if name.endswith("_spring_installed") else "MANUFACTURED"
            cq.exporters.export(shape, str(output_dir / f"{slug}_{name}_{suffix}.step"))
        for free_name in ("terminal_x_spring_free", "terminal_z_spring_free"):
            cq.exporters.export(reference[free_name], str(output_dir / f"{slug}_{free_name}_MANUFACTURED.step"))
        installed = cq.Compound.makeCompound(list(material.values()))
        installed_station_shapes.append(installed)
        cq.exporters.export(installed, str(output_dir / f"{slug}_installed_station_assembly.step"))
        cq.exporters.export(station.service_sweep, str(output_dir / f"{slug}_service_sweep_REFERENCE.step"))
        station_manifest = {
            "reaction_id": station.reaction_id,
            "terminal_datum": datum_map[station.reaction_id].manifest(),
            "fusion_handoff": next(row for row in fusion_handoff_manifest(architecture, datums)["stations"] if row["reaction_id"] == station.reaction_id),
        }
        (output_dir / f"{slug}_fusion_manifest.json").write_text(json.dumps(station_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    cq.exporters.export(cq.Compound.makeCompound(installed_station_shapes), str(output_dir / "treatment_four_zone_installed_assembly.step"))
    manifest = manifest_v8(architecture, datums)
    (output_dir / "treatment_mounted_four_zone_v8_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / "treatment_fusion_handoff.json").write_text(json.dumps(manifest["fusion_handoff"], indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest
