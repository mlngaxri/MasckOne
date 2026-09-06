from __future__ import annotations

import json
from pathlib import Path

import cadquery as cq

from .assertions import run_assertions
from .boundary_release import (
    boundary_release_manifest,
    build_verified_interface_boundary_topology,
)
from .cleanser_cassette_reconciliation import build_reconciled_cleanser_cassette
from .contact_simulation import build_contact_simulation_framework
from .interface_attachment import build_interface_attachment_architecture
from .model import MasckOneModel, build_model
from .realized_waste_backbone_release import build_current_cell4_waste_backbone_release
from .structural_frame import build_structural_frame_topology
from .waste_cartridge_dfm import build_waste_cartridge_dfm_audit


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
    cleanser_cassette = build_reconciled_cleanser_cassette(model.authority)

    export_map = {
        "rigid_shell": model.shell.solid,
        "nasal_lobe_membrane_reference": model.nasal_interface.solid,
        "water_reservoir_envelope": model.water_reservoir_envelope.solid,
        "waste_cartridge_envelope": model.waste_cartridge_envelope.solid,
        "battery_reference_envelope": model.battery_reference_envelope.solid,
        "cleanser_cassette_body": cleanser_cassette.body_solid,
        "cleanser_cassette_cradle": cleanser_cassette.cradle_solid,
        "cleanser_cassette_retention_key_locked": cleanser_cassette.retention_key_locked_solid,
        "cleanser_cassette_internal_cavity_reference": cleanser_cassette.cavity_reference_solid,
        "cleanser_cassette_refill_closure_reservation_reference": cleanser_cassette.source_storage.refill_closure_reservation_solid,
        "cleanser_cassette_purge_connector_reservation_reference": cleanser_cassette.source_storage.purge_connector_reservation_solid,
        "cleanser_cassette_outlet_connector_reservation_reference": cleanser_cassette.source_storage.outlet_connector_reservation_solid,
        "cleanser_cassette_drain_path_reference": cleanser_cassette.source_storage.drain_path_reference_solid,
        "cleanser_cassette_key_unlock_rotation_sweep_reference": cleanser_cassette.key_unlock_rotation_sweep_reference_solid,
        "cleanser_cassette_key_withdrawal_sweep_reference": cleanser_cassette.key_withdrawal_sweep_reference_solid,
        "cleanser_cassette_withdrawal_sweep_reference": cleanser_cassette.cassette_withdrawal_sweep_reference_solid,
        "cleanser_upstream_complete_module_service_envelope_reference": cleanser_cassette.upstream_complete_module_service_envelope_reference_solid,
    }
    for index, actuator in enumerate(model.actuator_envelopes, start=1):
        export_map[f"actuator_envelope_{index}"] = actuator.solid

    for name, solid in export_map.items():
        cq.exporters.export(solid, str(output / f"{name}.step"))

    # The current waste-cartridge solid is an authority package envelope, not cartridge
    # material. Keep its standalone STEP for package/collision review but do not insert
    # the proxy box into the physical development compound. The reconciled cleanser
    # cassette is likewise withheld from the compound until a released positive
    # cradle-to-frame attachment exists. Its body/cradle/key are exported as standalone
    # physical-part review STEP files, while cavity/reservation/service solids remain
    # explicit reference-only artifacts.
    development_assembly_exclusions = (
        "waste_cartridge_envelope",
        "cleanser_cassette_pending_positive_cradle_to_frame_attachment",
    )
    shapes = [
        component.solid.val()
        for component in model.components
        if component.status != "REFERENCE_ONLY" and component.name != "waste_cartridge_envelope"
    ]
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
    waste_cartridge_dfm = build_waste_cartridge_dfm_audit(model=model)
    cleanser_manifest = cleanser_cassette.manifest()
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
            "realized_cleanser_cassette": cleanser_manifest,
        },
        "dfm_gates": {
            "waste_cartridge": waste_cartridge_dfm.manifest(),
        },
        "analysis_frameworks": {
            "contact_simulation": contact_framework.manifest(),
        },
        "development_assembly_exclusions": list(development_assembly_exclusions),
        "exported_step_files": [f"{name}.step" for name in export_map] + ["masck_one_development_assembly.step"],
        "exported_manifest_files": ["cleanser_cassette_manifest.json"],
        "note": (
            "BLOCKED checks are unresolved evidence gates, not software failures. The structural frame is currently "
            "a topology/datum contract without invented cross-section or material; no frame STEP member geometry is "
            "released by Iteration 15. The realized waste backbone is emitted as validated centerline/manifold data, "
            "not selected tubing, pump, barrier, connector, hydraulic, service, or physical-performance evidence. "
            "The waste-cartridge STEP remains an external package-envelope reference only and is deliberately excluded "
            "from physical development-assembly material until body, cavity, seal, retention and service geometry are "
            "realized. The reconciled cleanser cassette consumes the exact Cell 4 donor body/cavity/port geometry and "
            "adds positive rotate-to-release key capture plus digital tolerance closure, but remains outside the physical "
            "development compound until a released positive cradle-to-frame attachment exists. Cleanser compatibility, "
            "sealing, usable capacity, dose, leakage, hygiene, service force, durability and flow remain physical gates. "
            "Reference cavity, reservation and service-sweep STEP files must never be interpreted as physical material. "
            "Digital topology/manifests and analysis frameworks are not physical validation evidence."
        ),
    }
    with (output / "cleanser_cassette_manifest.json").open("w", encoding="utf-8") as handle:
        json.dump(cleanser_manifest, handle, indent=2)
        handle.write("\n")
    with (output / "build_report.json").open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")
    return report
