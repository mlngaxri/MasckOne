from __future__ import annotations

import json
from pathlib import Path

import cadquery as cq

from .assertions import run_assertions
from .boundary_release import (
    boundary_release_manifest,
    build_verified_interface_boundary_topology,
)
from .component_registry import build_current_component_registry
from .contact_simulation import build_contact_simulation_framework
from .interface_attachment import build_interface_attachment_architecture
from .model import MasckOneModel, build_model
from .realized_waste_backbone_release import (
    Cell4WasteBackboneRelease,
    build_current_cell4_waste_backbone_release,
)
from .structural_frame import build_structural_frame_topology
from .waste_cartridge_dfm import build_waste_cartridge_dfm_audit


def _ensure_output_dir(path: str | Path) -> Path:
    output = Path(path).resolve()
    output.mkdir(parents=True, exist_ok=True)
    return output


def _realized_waste_backbone_manifest(
    release: Cell4WasteBackboneRelease | None = None,
) -> dict[str, object]:
    """Return the current validated route realization for deterministic release output."""
    release = release or build_current_cell4_waste_backbone_release()
    release_manifest = release.manifest()
    return {
        "release": release_manifest,
        "routes": [route.manifest() for route in release.realization.routes],
        "total_geometric_dead_volume_mL": release.realization.total_geometric_dead_volume_mL,
    }


def export_release(output_dir: str | Path = "generated", model: MasckOneModel | None = None) -> dict:
    model = model or build_model()
    output = _ensure_output_dir(output_dir)

    export_map = {
        "rigid_shell": model.shell.solid,
        "nasal_lobe_membrane_reference": model.nasal_interface.solid,
        "water_reservoir_envelope": model.water_reservoir_envelope.solid,
        "waste_cartridge_envelope": model.waste_cartridge_envelope.solid,
        "battery_reference_envelope": model.battery_reference_envelope.solid,
    }
    for index, actuator in enumerate(model.actuator_envelopes, start=1):
        export_map[f"actuator_envelope_{index}"] = actuator.solid

    for name, solid in export_map.items():
        cq.exporters.export(solid, str(output / f"{name}.step"))

    # Reconstruct the accepted mixed-waste realization once and share it with the
    # canonical registry and release report. This avoids duplicated source-graph rebuild
    # cost while preserving the exact current-source validation performed by the release.
    waste_release = build_current_cell4_waste_backbone_release()
    component_registry = build_current_component_registry(model=model, waste_release=waste_release)

    model_component_by_name = {component.name: component for component in model.components}
    physical_material_names = component_registry.physical_material_model_component_names
    missing_material = tuple(name for name in physical_material_names if name not in model_component_by_name)
    if missing_material:
        raise ValueError(
            f"component registry selects model material that does not exist: {missing_material}"
        )
    physical_shapes = [
        model_component_by_name[name].solid.val()
        for name in physical_material_names
    ]
    if not physical_shapes:
        raise ValueError("canonical component registry selected no released physical material")
    compound = cq.Compound.makeCompound(physical_shapes)
    cq.exporters.export(compound, str(output / "masck_one_development_assembly.step"))

    development_assembly_exclusions = tuple(
        sorted(set(model_component_by_name) - set(physical_material_names))
    )

    registry_manifest = component_registry.manifest()
    with (output / "component_registry.json").open("w", encoding="utf-8") as handle:
        json.dump(registry_manifest, handle, indent=2, allow_nan=False)
        handle.write("\n")

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
    report = {
        "project": "Masck One",
        "authority_revision": model.authority.get("project", "authority_revision"),
        "development_phase": 3,
        "iteration": 15,
        "result": "PASS" if not any(c.status == "FAIL" for c in checks) else "FAIL",
        "checks": [c.to_dict() for c in checks],
        "component_registry": registry_manifest,
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
            "realized_waste_backbone": _realized_waste_backbone_manifest(waste_release),
        },
        "dfm_gates": {
            "waste_cartridge": waste_cartridge_dfm.manifest(),
        },
        "analysis_frameworks": {
            "contact_simulation": contact_framework.manifest(),
        },
        "development_assembly_material_components": list(physical_material_names),
        "development_assembly_exclusions": list(development_assembly_exclusions),
        "exported_step_files": [f"{name}.step" for name in export_map]
        + ["masck_one_development_assembly.step"],
        "exported_manifests": ["component_registry.json", "build_report.json"],
        "note": (
            "BLOCKED checks are unresolved evidence gates, not software failures. The canonical component registry "
            "is the physical-material boundary for the development assembly: only released PHYSICAL_MATERIAL may enter "
            "that STEP compound; development references, package references, protected keepouts, centerlines, topology "
            "and unresolved identities remain non-material review evidence. The structural frame is currently a "
            "topology/datum contract without invented cross-section or material; no frame STEP member geometry is "
            "released by Iteration 15. The realized waste backbone is emitted as validated centerline/manifold data, "
            "not selected tubing, pump, barrier, connector, hydraulic, service, or physical-performance evidence. "
            "The waste-cartridge STEP remains an external package-envelope reference only and is deliberately excluded "
            "from physical development-assembly material until body, cavity, seal, retention and service geometry are "
            "realized. The cartridge DFM gate records digital closure requirements only and does not establish usable "
            "capacity, retained-liquid behavior, sealing, leakage, hygiene, durability, disposal performance or wet-hand "
            "serviceability. Digital topology/manifests and analysis frameworks are not physical validation evidence."
        ),
    }
    with (output / "build_report.json").open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, allow_nan=False)
        handle.write("\n")
    return report
