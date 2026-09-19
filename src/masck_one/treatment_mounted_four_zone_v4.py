from __future__ import annotations

"""Mounted four-zone V4: deterministic terminal master datums + overload backups.

V3's fully rigid four-face taper is retained as historical evidence but is no longer
the preferred production baseline because independent dimensional error over-constrains
four matched contacts. V4 starts from the collision-informed V2 mounted station and
adds only the deterministic rigid pieces that are already justified:

- one rigid X master datum;
- one rigid Z master datum;
- one rigid X overload backup;
- one rigid Z overload backup.

Independent compliant preload shoes are carried as reference geometry until an
explicit spring-root capture is realized. They are intentionally not promoted to
material merely to make the assembly look complete.
"""

import json
from pathlib import Path

import cadquery as cq

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
from .treatment_mounted_four_zone_v2 import build_mounted_four_zone_architecture_v2
from .treatment_terminal_datum_preload import (
    SOURCE_CELL6_HEAD_SHA,
    TerminalDatumPreloadArchitecture,
    build_terminal_datum_preload_architecture,
)

SCHEMA_V4 = "MASCK_ONE_TREATMENT_MOUNTED_FOUR_ZONE_V4"
SOURCE_MAIN_SHA = "42fa11818184cde998c6df25d7c46d4fb0e4c3eb"
SOURCE_TREATMENT_HEAD_SHA = "fec29d21e0dfd516430841a870eac6d2d8912c93"


def build_mounted_four_zone_architecture_v4(
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

    built: list[MountedTreatmentStation] = []
    for station in base.stations:
        datum = datum_map[station.reaction_id]
        material = dict(station.material_parts)
        reference = dict(station.reference_parts)
        backbone = material["fixed_backbone"]
        for _name, shape in datum.master_parts + datum.rigid_backup_parts:
            backbone = backbone.fuse(shape)
        backbone = backbone.clean()
        if not backbone.isValid() or len(backbone.Solids()) != 1:
            raise TreatmentMountedFourZoneError(
                f"{station.reaction_id} deterministic datum/backups do not fuse into one fixed backbone"
            )
        material["fixed_backbone"] = backbone

        # Preload shoes are intentionally references until their spring-root capture
        # becomes real treatment material. This prevents a floating part from being
        # mislabeled as an attached mechanism.
        for name, shape in datum.preload_installed_parts:
            reference[f"terminal_{name}"] = shape
        for name, shape in datum.preload_free_references:
            reference[f"terminal_{name}"] = shape
        for name, shape in datum.lossy_backup_references:
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


def manifest_v4(
    architecture: MountedFourZoneArchitecture,
    terminal_datums: TerminalDatumPreloadArchitecture,
) -> dict[str, object]:
    payload = architecture.manifest()
    payload["schema"] = SCHEMA_V4
    payload["source_main_sha"] = SOURCE_MAIN_SHA
    payload["source_cell6_head_sha"] = SOURCE_CELL6_HEAD_SHA
    payload["source_treatment_head_sha"] = SOURCE_TREATMENT_HEAD_SHA
    payload["terminal_datum_preload_architecture_sha256"] = terminal_datums.architecture_sha256
    payload["mechanical_status"] = (
        "FOUR_MOUNTED_STATION_V4_CANDIDATES_WITH_V2_TRUSS_PLUS_DETERMINISTIC_RIGID_X_Z_MASTER_"
        "DATUMS_AND_OVERLOAD_BACKUPS; PRELOAD_SPRING_ROOT_CAPTURE_OPEN"
    )
    payload["normal_reaction_path"] = (
        "RIGID_MASTER_DATUMS_INTENDED_FOR_40HZ_WORKING_REACTION; PRELOAD_SHOES_MAINTAIN_CONTACT_ONLY"
    )
    payload["buttery_service_intent"] = (
        "CLEARANCE_RAIL_APPROACH_THEN_ZERO_SLOPE_TERMINAL_ACQUISITION_AND_MUTED_FINAL_SEATING_EVENT"
    )
    payload["material_boundary"] = (
        "RIGID_DATUMS_AND_BACKUPS_ARE_MATERIAL; PRELOAD_SHOES_SPRING_FREE_STATE_AND_LOSSY_BUMPERS_"
        "REMAIN_REFERENCE_UNTIL_ROOT_CAPTURE_AND_MATERIAL_SELECTION_CLOSE"
    )
    payload["supersedes_as_v1_baseline"] = "MASCK_ONE_TREATMENT_MOUNTED_FOUR_ZONE_V3"
    return payload


def export_mounted_four_zone_architecture_v4(output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    architecture, terminal_datums = build_mounted_four_zone_architecture_v4()
    for station in architecture.stations:
        slug = station.reaction_id.lower()
        cq.exporters.export(
            cq.Compound.makeCompound([shape for _name, shape in station.material_parts]),
            str(output_dir / f"{slug}_mounted_station_v4_material.step"),
        )
        cq.exporters.export(
            cq.Compound.makeCompound([shape for _name, shape in station.reference_parts]),
            str(output_dir / f"{slug}_mounted_station_v4_reference.step"),
        )
        cq.exporters.export(
            station.operational_sweep,
            str(output_dir / f"{slug}_operational_v4_sweep.step"),
        )
        cq.exporters.export(
            station.service_sweep,
            str(output_dir / f"{slug}_service_v4_sweep.step"),
        )
    manifest = manifest_v4(architecture, terminal_datums)
    (output_dir / "treatment_mounted_four_zone_v4_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest
