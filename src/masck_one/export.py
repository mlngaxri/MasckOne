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
from .dry_side_package import build_dry_side_package
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


def _dry_side_geometry_by_id(items, geometry_id: str):
    matches = tuple(item.solid for item in items if item.geometry_id == geometry_id)
    if len(matches) != 1:
        raise ValueError(f"expected exactly one Cell 12 geometry {geometry_id}")
    return matches[0]


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

    dry_side = build_dry_side_package(model.authority, model)
    dry_side_export_map = {
        "cell12_dry_bay_carrier_structure_candidate": _dry_side_geometry_by_id(
            dry_side.physical_geometry, "DRY_BAY_CARRIER_STRUCTURE"
        ),
        "cell12_battery_packaging_benchmark_reference": _dry_side_geometry_by_id(
            dry_side.reference_geometry, "BATTERY_PACKAGING_BENCHMARK"
        ),
        "cell12_battery_fault_clearance_reference": _dry_side_geometry_by_id(
            dry_side.reference_geometry, "BATTERY_FAULT_CLEARANCE_RESERVATION"
        ),
        "cell12_pcb_bare_board_reference": _dry_side_geometry_by_id(
            dry_side.reference_geometry, "PCB_BARE_BOARD_REFERENCE"
        ),
        "cell12_pcb_power_protection_zone_reference": _dry_side_geometry_by_id(
            dry_side.reference_geometry, "PCB_POWER_PROTECTION_CHARGING_ZONE"
        ),
        "cell12_charging_interface_reservation_reference": _dry_side_geometry_by_id(
            dry_side.reference_geometry, "CHARGING_INTERFACE_RESERVATION"
        ),
        "cell12_rear_closure_seal_interface_reference": _dry_side_geometry_by_id(
            dry_side.reference_geometry, "REAR_CLOSURE_SEAL_INTERFACE_RESERVATION"
        ),
        "cell12_battery_service_sweep_reference": _dry_side_geometry_by_id(
            dry_side.service_geometry, "BATTERY_REARWARD_SERVICE_SWEEP"
        ),
    }
    for name, solid in dry_side_export_map.items():
        cq.exporters.export(solid, str(output / f"{name}.step"))
    with (output / "cell12_dry_side_manifest.json").open("w", encoding="utf-8") as handle:
        json.dump(dry_side.manifest(), handle, indent=2)
        handle.write("\n")

    # The current waste-cartridge solid is an authority package envelope, not cartridge
    # material. Keep its standalone STEP for package/collision review but do not insert
    # the proxy box into the physical development compound. The Cell 12 dry-side package
    # is also review-only until released 3D frame attachment and the Cell 2 exterior
    # closure counterpart exist. Cell 12 deliberately creates no duplicate visible door.
    development_assembly_exclusions = ("waste_cartridge_envelope",)
    shapes = [
        component.solid.val()
        for component in model.components
        if component.status != "REFERENCE_ONLY" and component.name not in development_assembly_exclusions
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
            "dry_side_package_review": dry_side.manifest(),
        },
        "dfm_gates": {
            "waste_cartridge": waste_cartridge_dfm.manifest(),
        },
        "analysis_frameworks": {
            "contact_simulation": contact_framework.manifest(),
        },
        "development_assembly_exclusions": list(development_assembly_exclusions),
        "review_only_packages": ["cell12_dry_side_package"],
        "exported_step_files": (
            [f"{name}.step" for name in export_map]
            + [f"{name}.step" for name in dry_side_export_map]
            + ["masck_one_development_assembly.step"]
        ),
        "exported_manifest_files": ["cell12_dry_side_manifest.json"],
        "note": (
            "BLOCKED checks are unresolved evidence gates, not software failures. The structural frame is currently "
            "a topology/datum contract without invented cross-section or material; no frame STEP member geometry is "
            "released by Iteration 15. The realized waste backbone is emitted as validated centerline/manifold data, "
            "not selected tubing, pump, barrier, connector, hydraulic, service, or physical-performance evidence. "
            "The waste-cartridge STEP remains an external package-envelope reference only and is deliberately excluded "
            "from physical development-assembly material until body, cavity, seal, retention and service geometry are "
            "realized. The Cell 12 compact dry-side carrier is exported as deterministic review geometry only and is not "
            "inserted into the released physical development assembly until a released 3D frame attachment counterpart "
            "exists. Cell 12 exports a rear closure/seal interface reference but no visible rear door material; the visible "
            "rear service cover remains Cell 2 exterior ownership, avoiding duplicate stacked closure material. The Cell 12 "
            "battery remains a packaging benchmark and its PCB, charging and power geometry remains unselected digital "
            "reservation evidence. Digital topology/manifests and analysis frameworks are not physical validation evidence."
        ),
    }
    with (output / "build_report.json").open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")
    return report
