from __future__ import annotations

import json
import hashlib
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
from .structural_frame import build_structural_frame_topology
from .quarter_architecture import build_quarter_architecture


def _ensure_output_dir(path: str | Path) -> Path:
    output = Path(path).resolve()
    output.mkdir(parents=True, exist_ok=True)
    return output


def export_release(output_dir: str | Path = "generated", model: MasckOneModel | None = None) -> dict:
    model = model or build_model()
    output = _ensure_output_dir(output_dir)
    quarter = build_quarter_architecture(model)

    export_map = {
        "rigid_shell": model.shell.solid,
        "nasal_lobe_membrane_reference": model.nasal_interface.solid,
        "water_reservoir_envelope": model.water_reservoir_envelope.solid,
        "waste_cartridge_envelope": model.waste_cartridge_envelope.solid,
        "battery_reference_envelope": model.battery_reference_envelope.solid,
    }
    for index, actuator in enumerate(model.actuator_envelopes, start=1):
        export_map[f"actuator_envelope_{index}"] = actuator.solid
    for index, swept in enumerate(quarter.actuation.swept_envelopes(), start=1):
        export_map[f"actuator_swept_envelope_{index}"] = swept
    for station in quarter.fresh_fluid.pump_stations:
        export_map[station.station_id.lower()] = station.cad_envelope()
    for role in ("WATER", "CLEANSER"):
        export_map[f"{role.lower()}_outlet_center_references"] = (
            quarter.distribution_manifold.cad_outlet_references(role)
        )
    export_map["waste_acquisition_centerline_references"] = quarter.waste.cad_acquisition_centerlines()
    export_map["waste_pump_alpha"] = quarter.waste.pump_station.cad_envelope()
    export_map["waste_capacity_reservation"] = quarter.waste.cartridge.cad_capacity_reservation()
    export_map["retention_interface_references"] = quarter.wearable.retention.cad_interface_references()

    for name, solid in export_map.items():
        cq.exporters.export(solid, str(output / f"{name}.step"))

    quarter_assembly_shapes = [
        *(shape.val() for shape in quarter.actuation.swept_envelopes()),
        *(station.cad_envelope().val() for station in quarter.fresh_fluid.pump_stations),
        quarter.distribution_manifold.cad_outlet_references("WATER").val(),
        quarter.distribution_manifold.cad_outlet_references("CLEANSER").val(),
        quarter.waste.cad_acquisition_centerlines().val(),
        quarter.waste.pump_station.cad_envelope().val(),
        quarter.waste.cartridge.cad_capacity_reservation().val(),
        quarter.wearable.retention.cad_interface_references().val(),
    ]
    shapes = [
        component.solid.val()
        for component in model.components
        if component.status != "REFERENCE_ONLY"
    ] + quarter_assembly_shapes
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
        "development_phase": 8,
        "iteration": 40,
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
            "quarter_architecture": quarter.manifest(),
        },
        "analysis_frameworks": {
            "contact_simulation": contact_framework.manifest(),
        },
        "exported_step_files": [f"{name}.step" for name in export_map] + ["masck_one_development_assembly.step"],
        "step_sha256": {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(output.glob("*.step"))
        },
        "note": (
            "BLOCKED checks are unresolved evidence gates, not software failures. The structural frame is currently "
            "a topology/datum contract without invented cross-section or material; no frame STEP member geometry is "
            "released by Iteration 15. Digital topology/manifests and analysis frameworks are not physical validation evidence."
        ),
    }
    with (output / "build_report.json").open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")
    build_report_path = output / "build_report.json"
    release_manifest = {
        "project": "Masck One",
        "authority_revision": model.authority.get("project", "authority_revision"),
        "iteration": 40,
        "digital_alpha_status": quarter.alpha_closure.digital_alpha_status,
        "physical_mvp_status": quarter.alpha_closure.physical_mvp_status,
        "architecture_sha256": quarter.alpha_closure.topology_sha256,
        "build_report_sha256": hashlib.sha256(build_report_path.read_bytes()).hexdigest(),
        "step_sha256": report["step_sha256"],
        "required_physical_gate_iterations": list(
            quarter.alpha_closure.release.required_physical_gate_iterations
        ),
        "integrated_mvp_gate_iteration": quarter.alpha_closure.release.integrated_mvp_gate_iteration,
    }
    with (output / "release_manifest.json").open("w", encoding="utf-8") as handle:
        json.dump(release_manifest, handle, indent=2)
        handle.write("\n")
    return report
