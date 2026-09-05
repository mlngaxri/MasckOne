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
from .realized_cleanser_storage import build_realized_cleanser_storage
from .realized_waste_backbone_release import build_current_cell4_waste_backbone_release
from .structural_frame import build_structural_frame_topology


def _ensure_output_dir(path: str | Path) -> Path:
    output = Path(path).resolve()
    output.mkdir(parents=True, exist_ok=True)
    return output


def _realized_waste_backbone_manifest() -> dict[str, object]:
    """Return the current validated route realization for deterministic release output."""
    release = build_current_cell4_waste_backbone_release()
    release_manifest = release.manifest()
    return {
        "release": release_manifest,
        "routes": [route.manifest() for route in release.realization.routes],
        "total_geometric_dead_volume_mL": release.realization.total_geometric_dead_volume_mL,
    }


def export_release(output_dir: str | Path = "generated", model: MasckOneModel | None = None) -> dict:
    model = model or build_model()
    output = _ensure_output_dir(output_dir)
    cleanser = build_realized_cleanser_storage(model.authority)

    export_map = {
        "rigid_shell": model.shell.solid,
        "nasal_lobe_membrane_reference": model.nasal_interface.solid,
        "water_reservoir_envelope": model.water_reservoir_envelope.solid,
        "waste_cartridge_envelope": model.waste_cartridge_envelope.solid,
        "battery_reference_envelope": model.battery_reference_envelope.solid,
        "cleanser_storage_body": cleanser.body_solid,
        "cleanser_storage_cradle": cleanser.cradle_solid,
        "cleanser_storage_retention_key": cleanser.retention_key_solid,
        "cleanser_storage_internal_cavity_reference": cleanser.internal_cavity_solid,
        "cleanser_storage_refill_closure_reservation_reference": cleanser.refill_closure_reservation_solid,
        "cleanser_storage_purge_connector_reservation_reference": cleanser.purge_connector_reservation_solid,
        "cleanser_storage_outlet_connector_reservation_reference": cleanser.outlet_connector_reservation_solid,
        "cleanser_storage_low_point_drain_reference": cleanser.drain_path_reference_solid,
        "cleanser_storage_cassette_service_sweep_reference": cleanser.cassette_service_sweep_solid,
        "cleanser_storage_key_service_sweep_reference": cleanser.key_service_sweep_solid,
    }
    for index, actuator in enumerate(model.actuator_envelopes, start=1):
        export_map[f"actuator_envelope_{index}"] = actuator.solid

    for name, solid in export_map.items():
        cq.exporters.export(solid, str(output / f"{name}.step"))

    # Reference/reservation solids are exported for review but are not assembly material.
    shapes = [component.solid.val() for component in model.components if component.status != "REFERENCE_ONLY"]
    shapes.extend(
        (
            cleanser.body_solid.val(),
            cleanser.cradle_solid.val(),
            cleanser.retention_key_solid.val(),
        )
    )
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
            "realized_waste_backbone": _realized_waste_backbone_manifest(),
        },
        "digital_geometry": {
            "realized_cleanser_storage": cleanser.manifest(),
            "realized_cleanser_storage_manifest_sha256": cleanser.manifest_sha256,
        },
        "analysis_frameworks": {
            "contact_simulation": contact_framework.manifest(),
        },
        "exported_step_files": [f"{name}.step" for name in export_map] + ["masck_one_development_assembly.step"],
        "note": (
            "BLOCKED checks are unresolved evidence gates, not software failures. The structural frame is currently "
            "a topology/datum contract without invented cross-section or material; no frame STEP member geometry is "
            "released by Iteration 15. The realized waste backbone is emitted as validated centerline/manifold data, "
            "not selected tubing, pump, barrier, connector, hydraulic, service, or physical-performance evidence. "
            "The realized cleanser cassette, cradle, ports, drain opening and retention key are provisional digital "
            "geometry only. Geometric cavity volume is not drawable volume or service cadence; closure, connector, "
            "isolation, purge, compatibility, leakage, hygiene, drying, wet-hand service and durability performance "
            "remain unresolved or validation-gated. Digital topology/manifests and analysis frameworks are not "
            "physical validation evidence."
        ),
    }
    with (output / "build_report.json").open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")
    return report
