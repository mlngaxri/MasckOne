from __future__ import annotations

"""Mounted four-zone V3: V2 truss route plus terminal rigid kinematic seating.

V2 solved the posterior reaction-truss/frame-slab conflict but retained the original
parallel-clearance shoulder yoke. V3 keeps the low-drag rail/yoke approach and fuses
four treatment-owned terminal taper pads into each fixed backbone. At the selected
installed coordinate the taper faces are tangent to the rigid Cell 6 shoulder, so
X/Z running clearance is removed by the seating datum rather than by tightening the
whole service rail. A frame detent/cam still has to maintain axial seating in the
physical mechanism; that force, friction, contact pressure and tolerance closure are
not proved here.
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
from .treatment_terminal_kinematic_seat import (
    SOURCE_CELL6_HEAD_SHA,
    TerminalKinematicSeatArchitecture,
    build_terminal_kinematic_seats,
    seating_backdrive_screen,
)

SCHEMA_V3 = "MASCK_ONE_TREATMENT_MOUNTED_FOUR_ZONE_V3"
SOURCE_MAIN_SHA = "42fa11818184cde998c6df25d7c46d4fb0e4c3eb"
SOURCE_TREATMENT_HEAD_SHA = "2bcdba02e9ee30e86baa74e7cecc9095e8bf4a71"


def build_mounted_four_zone_architecture_v3(
    *,
    model: MasckOneModel | None = None,
    reactions: StructuralFrameActuatorReactionArchitecture | None = None,
    mates: StructuralFrameActuatorMateArchitecture | None = None,
    counterparts: TreatmentCarrierCounterpartArchitecture | None = None,
    terminal_seats: TerminalKinematicSeatArchitecture | None = None,
) -> tuple[MountedFourZoneArchitecture, TerminalKinematicSeatArchitecture]:
    model = build_model() if model is None else model
    reactions = build_structural_frame_actuator_reactions(model=model) if reactions is None else reactions
    mates = build_structural_frame_actuator_mates(model=model, reactions=reactions) if mates is None else mates

    # Build the already collision-informed V2 station from exactly the same source
    # objects, then add only treatment-owned terminal seat material.
    base = build_mounted_four_zone_architecture_v2(
        model=model,
        reactions=reactions,
        mates=mates,
        counterparts=counterparts,
    )
    terminal_seats = (
        build_terminal_kinematic_seats(model=model, reactions=reactions, mates=mates)
        if terminal_seats is None
        else terminal_seats
    )
    seat_map = {seat.reaction_id: seat for seat in terminal_seats.seats}
    _interfaces, _preload, _landing, _detent, source_targets = _source_targets(reactions, mates)

    built: list[MountedTreatmentStation] = []
    for station in base.stations:
        seat = seat_map[station.reaction_id]
        material = dict(station.material_parts)
        backbone = material["fixed_backbone"]
        for _name, pad in seat.pad_parts:
            backbone = backbone.fuse(pad)
        backbone = backbone.clean()
        if not backbone.isValid() or len(backbone.Solids()) != 1:
            raise TreatmentMountedFourZoneError(
                f"{station.reaction_id} terminal seat does not fuse into one fixed backbone"
            )
        material["fixed_backbone"] = backbone

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
        truss_screen["terminal_kinematic_seat"] = seat.manifest()
        built.append(
            MountedTreatmentStation(
                station.reaction_id,
                station.treatment_center_mm,
                station.axis_angle_deg,
                tuple(material.items()),
                station.reference_parts,
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
    return architecture, terminal_seats


def manifest_v3(
    architecture: MountedFourZoneArchitecture,
    terminal_seats: TerminalKinematicSeatArchitecture,
) -> dict[str, object]:
    payload = architecture.manifest()
    payload["schema"] = SCHEMA_V3
    payload["source_main_sha"] = SOURCE_MAIN_SHA
    payload["source_cell6_head_sha"] = SOURCE_CELL6_HEAD_SHA
    payload["source_treatment_head_sha"] = SOURCE_TREATMENT_HEAD_SHA
    payload["terminal_kinematic_seat_architecture_sha256"] = terminal_seats.architecture_sha256
    payload["terminal_seating_retention_screen"] = seating_backdrive_screen()
    payload["mechanical_status"] = (
        "FOUR_MOUNTED_STATION_V3_CANDIDATES_WITH_V2_ANTERIOR_TRUSS_ROUTE_PLUS_"
        "TERMINAL_RIGID_XZ_KINEMATIC_TAPER_SEATING_AND_32MM_SERVICE_SWEEP_DIGITALLY_TESTED"
    )
    payload["seated_play_status"] = (
        "IDEAL_RIGID_DATUM_MODEL_REMOVES_XZ_RUNNING_CLEARANCE_AT_TERMINAL_SEAT; "
        "AXIAL_SEATING_PRELOAD_TOLERANCE_FRICTION_WEAR_AND_CONTACT_PRESSURE_PHYSICAL_OPEN"
    )
    payload["supersedes"] = "MASCK_ONE_TREATMENT_MOUNTED_FOUR_ZONE_V2_PARALLEL_CLEARANCE_YOKE"
    return payload


def export_mounted_four_zone_architecture_v3(output_dir: Path) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    architecture, terminal_seats = build_mounted_four_zone_architecture_v3()
    for station in architecture.stations:
        slug = station.reaction_id.lower()
        cq.exporters.export(
            cq.Compound.makeCompound([shape for _name, shape in station.material_parts]),
            str(output_dir / f"{slug}_mounted_station_v3_material.step"),
        )
        cq.exporters.export(
            station.operational_sweep,
            str(output_dir / f"{slug}_operational_v3_sweep.step"),
        )
        cq.exporters.export(
            station.service_sweep,
            str(output_dir / f"{slug}_service_v3_sweep.step"),
        )
    manifest = manifest_v3(architecture, terminal_seats)
    (output_dir / "treatment_mounted_four_zone_v3_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest
