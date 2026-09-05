from __future__ import annotations

import json
from pathlib import Path

import cadquery as cq

from .assertions import run_assertions
from .boundary_release import (
    boundary_release_manifest,
    build_verified_interface_boundary_topology,
)
from .contact_simulation import build_contact_simulation_framework
from .interface_attachment import build_interface_attachment_architecture
from .model import MasckOneModel, build_model
from .realized_water_reservoir import build_realized_water_reservoir
from .structural_frame import build_structural_frame_topology
from .water_reservoir_interfaces import build_water_reservoir_interface_geometry


def _ensure_output_dir(path: str | Path) -> Path:
    output = Path(path).resolve()
    output.mkdir(parents=True, exist_ok=True)
    return output


def export_release(output_dir: str | Path = "generated", model: MasckOneModel | None = None) -> dict:
    model = model or build_model()
    output = _ensure_output_dir(output_dir)
    realized_water = build_realized_water_reservoir(model.authority)
    water_interfaces = build_water_reservoir_interface_geometry(model.authority, realized_water)

    export_map = {
        "rigid_shell": model.shell.solid,
        "nasal_lobe_membrane_reference": model.nasal_interface.solid,
        "water_reservoir_body": water_interfaces.body_with_pickup_port_solid,
        "water_reservoir_lid": water_interfaces.lid_with_fill_vent_ports_solid,
        "water_reservoir_internal_cavity_reference": model.water_reservoir_envelope.solid,
        "water_reservoir_service_sweep_reference": realized_water.service_sweep_solid,
        "water_reservoir_fill_closure_reservation_reference": water_interfaces.fill_closure_reservation_solid,
        "water_reservoir_vent_path_reference": water_interfaces.vent_path_solid,
        "water_reservoir_vent_barrier_reservation_reference": water_interfaces.vent_external_barrier_reservation_solid,
        "water_reservoir_pickup_passage_reference": water_interfaces.pickup_passage_solid,
        "water_reservoir_pickup_connector_reservation_reference": water_interfaces.pickup_connector_reservation_solid,
        "waste_cartridge_envelope": model.waste_cartridge_envelope.solid,
        "battery_reference_envelope": model.battery_reference_envelope.solid,
    }
    for index, actuator in enumerate(model.actuator_envelopes, start=1):
        export_map[f"actuator_envelope_{index}"] = actuator.solid

    for name, solid in export_map.items():
        cq.exporters.export(solid, str(output / f"{name}.step"))

    # The service/reference reservations above are voids/keepouts, not assembly material.
    # Substitute only the ported body/lid for their parent solids in the physical compound.
    shapes = []
    for component in model.components:
        if component.status == "REFERENCE_ONLY":
            continue
        if component.name == "water_reservoir_body":
            shapes.append(water_interfaces.body_with_pickup_port_solid.val())
        elif component.name == "water_reservoir_lid":
            shapes.append(water_interfaces.lid_with_fill_vent_ports_solid.val())
        else:
            shapes.append(component.solid.val())
    compound = cq.Compound.makeCompound(shapes)
    cq.exporters.export(compound, str(output / "masck_one_development_assembly.step"))

    checks = run_assertions(model)
    boundary_topology = build_verified_interface_boundary_topology(
        model.authority,
        model.facial_surface,
        model.coverage_mesh,
        model.compliant_interface_topology,
    )
    attachment = build_interface_attachment_architecture(model.authority, boundary_topology)
    contact_framework = build_contact_simulation_framework(model.authority, attachment)
    structural_frame = build_structural_frame_topology(model.authority, attachment)
    report = {
        "project": "Masck One",
        "authority_revision": model.authority.get("project", "authority_revision"),
        "development_phase": 3,
        "iteration": 15,
        "result": "PASS" if not any(c.status == "FAIL" for c in checks) else "FAIL",
        "checks": [c.to_dict() for c in checks],
        "digital_topology": {
            "coverage": model.coverage_mesh.manifest(),
            "compliant_interface": model.compliant_interface_topology.manifest(model.coverage_mesh),
            "nasal_subsystem": model.nasal_subsystem_topology.manifest(),
            "interface_boundaries": boundary_release_manifest(
                model.authority,
                model.facial_surface,
                model.coverage_mesh,
                model.compliant_interface_topology,
            ),
            "interface_attachment": attachment.manifest(),
            "structural_frame": structural_frame.manifest(),
        },
        "digital_geometry": {
            "water_reservoir": realized_water.manifest(),
            "water_reservoir_manifest_sha256": realized_water.manifest_sha256,
            "water_reservoir_interfaces": water_interfaces.manifest(),
            "water_reservoir_interfaces_manifest_sha256": water_interfaces.manifest_sha256,
        },
        "analysis_frameworks": {
            "contact_simulation": contact_framework.manifest(),
        },
        "exported_step_files": [f"{name}.step" for name in export_map] + ["masck_one_development_assembly.step"],
        "note": (
            "BLOCKED checks are unresolved evidence gates, not software failures. The structural frame is currently "
            "a topology/datum contract without invented cross-section or material; no frame STEP member geometry is "
            "released by Iteration 15. The water-reservoir assembly uses the ported body/lid candidate while cavity, "
            "service sweep, fill-closure, vent-path/barrier and pickup-passage/connector STEP outputs remain digital "
            "review references or keepouts. Their provisional geometry does not establish sealing, leakage, ingress, "
            "priming, spill behavior, orientation performance, hygiene, drying, serviceability, durability or physical "
            "safety. Digital topology/manifests and analysis frameworks are not physical validation evidence."
        ),
    }
    with (output / "build_report.json").open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")
    return report
