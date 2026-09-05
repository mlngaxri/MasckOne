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
from .realized_waste_backbone_release import (
    Cell4WasteBackboneRelease,
    build_current_cell4_waste_backbone_release,
)
from .realized_waste_pump import build_realized_waste_pump_package
from .structural_frame import build_structural_frame_topology


def _ensure_output_dir(path: str | Path) -> Path:
    output = Path(path).resolve()
    output.mkdir(parents=True, exist_ok=True)
    return output


def _realized_waste_backbone_manifest(
    release: Cell4WasteBackboneRelease | None = None,
) -> dict[str, object]:
    """Return the current validated route realization for deterministic release output."""
    release = release or build_current_cell4_waste_backbone_release()
    release.validate_invariants()
    release_manifest = {
        "authored_against_git_sha": release.authored_against_git_sha,
        "source_waste_pump_architecture_sha256": release.source_waste_pump_architecture_sha256,
        "authority_revision": release.realization.authority_revision,
        "realization_manifest_sha256": release.realization.manifest_sha256,
        "release_state": release.release_state,
    }
    return {
        "release": release_manifest,
        "routes": [route.manifest() for route in release.realization.routes],
        "total_geometric_dead_volume_mL": release.realization.total_geometric_dead_volume_mL,
    }


def export_release(output_dir: str | Path = "generated", model: MasckOneModel | None = None) -> dict:
    model = model or build_model()
    output = _ensure_output_dir(output_dir)

    waste_release = build_current_cell4_waste_backbone_release()
    waste_pump = build_realized_waste_pump_package(waste_release)

    export_map = {
        "rigid_shell": model.shell.solid,
        "nasal_lobe_membrane_reference": model.nasal_interface.solid,
        "water_reservoir_envelope": model.water_reservoir_envelope.solid,
        "waste_cartridge_envelope": model.waste_cartridge_envelope.solid,
        "battery_reference_envelope": model.battery_reference_envelope.solid,
        "mixed_waste_pump_package_screening_envelope": waste_pump.package_screening_solid,
        "mixed_waste_pump_support_cradle": waste_pump.support_cradle_solid,
        "mixed_waste_pump_inlet_port_reservation_reference": waste_pump.inlet_port_reservation_solid,
        "mixed_waste_pump_outlet_port_reservation_reference": waste_pump.outlet_port_reservation_solid,
        "mixed_waste_pump_drain_dry_clearance_reference": waste_pump.drain_dry_clearance_solid,
        "mixed_waste_pump_service_clearance_reference": waste_pump.service_clearance_solid,
    }
    for index, actuator in enumerate(model.actuator_envelopes, start=1):
        export_map[f"actuator_envelope_{index}"] = actuator.solid

    for name, solid in export_map.items():
        cq.exporters.export(solid, str(output / f"{name}.step"))

    # The provisional package body and open drainable cradle enter the development
    # compound for package/collision review only. Port, drain/dry, and service solids are
    # reference/free-space reservations and are never assembly material.
    shapes = [
        component.solid.val()
        for component in model.components
        if component.status != "REFERENCE_ONLY"
    ]
    shapes.extend(
        (
            waste_pump.package_screening_solid.val(),
            waste_pump.support_cradle_solid.val(),
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
            "realized_waste_backbone": _realized_waste_backbone_manifest(waste_release),
        },
        "digital_geometry": {
            "realized_mixed_waste_pump": waste_pump.manifest(),
            "realized_mixed_waste_pump_manifest_sha256": waste_pump.manifest_sha256,
        },
        "analysis_frameworks": {
            "contact_simulation": contact_framework.manifest(),
        },
        "exported_step_files": [f"{name}.step" for name in export_map]
        + ["masck_one_development_assembly.step"],
        "note": (
            "BLOCKED checks are unresolved evidence gates, not software failures. The structural frame is currently "
            "a topology/datum contract without invented cross-section or material; no frame STEP member geometry is "
            "released by Iteration 15. The realized waste backbone retains exact MIXED_AIR_LIQUID_FOAM_CONTAMINANT "
            "identity and acquisition -> waste pump -> passive backflow protection -> cartridge topology. The mixed-"
            "waste pump addition is a provisional 12 x 8 x 8 mm dimensional screening envelope at the released station, "
            "with route-anchor port reservations, an open WET_DRAINABLE cradle, a low-point drain/dry free-space "
            "reference, and stationary local service clearance. It does not select a pump or passive-backflow component "
            "and does not establish mixed-phase/foam handling, pressure-flow behavior, recovery, leakage, containment, "
            "orientation, hygiene, drying time, replacement trajectory, durability, acoustics, runtime, or physical "
            "performance. Digital topology/manifests and analysis frameworks are not physical validation evidence."
        ),
    }
    with (output / "build_report.json").open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")
    return report
