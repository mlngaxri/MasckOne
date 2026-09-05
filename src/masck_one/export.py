from __future__ import annotations

import json
from pathlib import Path

import cadquery as cq

from .assertions import run_assertions
from .boundary_release import (
    boundary_release_manifest,
    build_verified_interface_boundary_topology,
)
from .cleanser_storage import build_cleanser_storage_architecture
from .contact_simulation import build_contact_simulation_framework
from .fresh_pump_packaging import build_fresh_pump_packaging_architecture
from .interface_attachment import build_interface_attachment_architecture
from .model import MasckOneModel, build_model
from .realized_cleanser_pump import (
    CurrentCleanserPumpSources,
    build_realized_cleanser_pump,
)
from .realized_waste_backbone_release import build_current_cell4_waste_backbone_release
from .structural_frame import build_structural_frame_topology
from .water_reservoir import build_water_reservoir_architecture


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

    boundary_topology = build_verified_interface_boundary_topology(
        model.authority,
        model.facial_surface,
        model.coverage_mesh,
        model.compliant_interface_topology,
    )
    attachment = build_interface_attachment_architecture(model.authority, boundary_topology)
    structural_frame = build_structural_frame_topology(model.authority, attachment)
    water = build_water_reservoir_architecture(model.authority)
    cleanser = build_cleanser_storage_architecture(model.authority)
    pump_architecture = build_fresh_pump_packaging_architecture(
        model.authority,
        water,
        cleanser,
        structural_frame,
    )
    cleanser_pump_sources = CurrentCleanserPumpSources(
        model=model,
        authority=model.authority,
        water=water,
        cleanser=cleanser,
        frame=structural_frame,
        architecture=pump_architecture,
    )
    cleanser_pump_sources.validate()
    cleanser_pump = build_realized_cleanser_pump(cleanser_pump_sources)

    export_map = {
        "rigid_shell": model.shell.solid,
        "nasal_lobe_membrane_reference": model.nasal_interface.solid,
        "water_reservoir_envelope": model.water_reservoir_envelope.solid,
        "waste_cartridge_envelope": model.waste_cartridge_envelope.solid,
        "battery_reference_envelope": model.battery_reference_envelope.solid,
        "cleanser_pump_reference_envelope": cleanser_pump.package_reference_solid,
        "cleanser_pump_support_cradle": cleanser_pump.support_cradle_solid,
        "cleanser_pump_inlet_port_reservation_reference": cleanser_pump.inlet_port_reservation_solid,
        "cleanser_pump_outlet_port_reservation_reference": cleanser_pump.outlet_port_reservation_solid,
        "cleanser_pump_service_clearance_reference": cleanser_pump.service_clearance_solid,
    }
    for index, actuator in enumerate(model.actuator_envelopes, start=1):
        export_map[f"actuator_envelope_{index}"] = actuator.solid

    for name, solid in export_map.items():
        cq.exporters.export(solid, str(output / f"{name}.step"))

    # The dimensional screening body and drainable cradle enter the development
    # assembly for package review only. Port and service-clearance solids remain
    # explicit reference/reservation geometry and are not assembly material.
    shapes = [
        component.solid.val()
        for component in model.components
        if component.status != "REFERENCE_ONLY"
    ]
    shapes.extend(
        (
            cleanser_pump.package_reference_solid.val(),
            cleanser_pump.support_cradle_solid.val(),
        )
    )
    compound = cq.Compound.makeCompound(shapes)
    cq.exporters.export(compound, str(output / "masck_one_development_assembly.step"))

    checks = run_assertions(model)
    contact_framework = build_contact_simulation_framework(model.authority, attachment)
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
            "realized_cleanser_pump": cleanser_pump.manifest(),
            "realized_cleanser_pump_manifest_sha256": cleanser_pump.manifest_sha256,
        },
        "analysis_frameworks": {
            "contact_simulation": contact_framework.manifest(),
        },
        "exported_step_files": [f"{name}.step" for name in export_map]
        + ["masck_one_development_assembly.step"],
        "note": (
            "BLOCKED checks are unresolved evidence gates, not software failures. The structural frame is currently "
            "a topology/datum contract without invented cross-section or material; no frame STEP member geometry is "
            "released by Iteration 15. The realized waste backbone is emitted as validated centerline/manifold data, "
            "not selected tubing, pump, barrier, connector, hydraulic, service, or physical-performance evidence. "
            "The cleanser pump is a distinct CLEANSER-only dimensional package screen with local -X port reservations, "
            "an open WET_DRAINABLE cradle, and a stationary service-clearance reference. Supplier body dimensions are "
            "fit/collision references only and do not establish cleanser compatibility, viscosity range, pump selection, "
            "flow, pressure, metering, priming, orientation, leakage, acoustics, durability, runtime, or physical service "
            "performance. Fresh-water identity and released mixed-waste passive-backflow topology are unchanged. "
            "Digital topology/manifests and analysis frameworks are not physical validation evidence."
        ),
    }
    with (output / "build_report.json").open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")
    return report
