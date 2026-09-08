from __future__ import annotations

import json
from pathlib import Path

import cadquery as cq

from .assertions import run_assertions
from .authority import Authority
from .boundary_release import (
    boundary_release_manifest,
    build_verified_interface_boundary_topology,
)
from .brand_identity import build_brand_identity_manifest
from .component_registry import build_current_component_registry
from .contact_simulation import build_contact_simulation_framework
from .exterior_eye_roll import build_eye_rolled_exterior_shell
from .integrated_product import integrated_exterior_manifest
from .interface_attachment import build_interface_attachment_architecture
from .model import MasckOneModel, build_model
from .realized_waste_backbone_release import (
    Cell4WasteBackboneRelease,
    build_current_cell4_waste_backbone_release,
)
from .rear_service_skin import build_rear_service_skin
from .structural_frame import build_structural_frame_topology
from .waste_cartridge_dfm import build_waste_cartridge_dfm_audit


CELL2_EXTERIOR_REVIEW_STEP = "cell2_rigid_shell_candidate_review.step"
CELL2_EXTERIOR_REVIEW_MANIFEST = "cell2_exterior_candidate_manifest.json"
CELL2_REAR_REVIEW_EXPORT_NAMES = (
    "cell2_rear_service_skin_review",
    "cell2_rear_service_cover_removal_reference",
    "cell2_rear_service_package_keepout_reference",
)
CELL2_REAR_REVIEW_MANIFEST = "cell2_rear_service_skin_manifest.json"


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


def _export_cell2_exterior_candidate_review(
    output: Path,
    model: MasckOneModel,
) -> dict[str, object]:
    """Exercise and export the exact Cell 2 shell without promoting it into released material."""
    candidate = build_eye_rolled_exterior_shell(model.authority, model.facial_reference)
    shape = candidate.val()
    if not shape.isValid() or candidate.solids().size() != 1 or float(shape.Volume()) <= 0.0:
        raise ValueError("Cell 2 exterior smoke candidate must be one valid positive solid")

    cq.exporters.export(candidate, str(output / CELL2_EXTERIOR_REVIEW_STEP))
    imported = cq.importers.importStep(str(output / CELL2_EXTERIOR_REVIEW_STEP))
    if imported.solids().size() != 1 or not imported.val().isValid():
        raise ValueError("Cell 2 exterior smoke STEP must round-trip as one valid solid")

    bb = shape.BoundingBox()
    imported_bb = imported.val().BoundingBox()
    for expected, actual in (
        (bb.xlen, imported_bb.xlen),
        (bb.ylen, imported_bb.ylen),
        (bb.zlen, imported_bb.zlen),
    ):
        if abs(float(expected) - float(actual)) > 1e-4:
            raise ValueError("Cell 2 exterior smoke STEP bounds changed on round-trip")

    manifest: dict[str, object] = {
        "schema": "MASCK_ONE_CELL2_EXTERIOR_SMOKE_REVIEW_V1",
        "coordinate_frame": "MASCK_ONE_AUTHORITY_WORLD_MM",
        "shell_valid": True,
        "shell_solid_count": 1,
        "shell_volume_mm3": float(shape.Volume()),
        "shell_bounds_mm": [
            float(bb.xmin), float(bb.xmax), float(bb.ymin), float(bb.ymax), float(bb.zmin), float(bb.zmax)
        ],
        "integrated_exterior": integrated_exterior_manifest(model.authority),
        "assembly_policy": "REVIEW_ONLY_NOT_RELEASED_DEVELOPMENT_ASSEMBLY_MATERIAL",
        "evidence_status": "DIGITAL_CELL2_CANDIDATE_SMOKE_NOT_RELEASED_PRODUCT_OR_PHYSICAL_EVIDENCE",
    }
    with (output / CELL2_EXTERIOR_REVIEW_MANIFEST).open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    return manifest


def _export_cell2_rear_service_review(
    output: Path,
    authority: Authority,
) -> tuple[dict[str, object], list[str]]:
    """Export Cell 2 rear geometry as review evidence, never assembly material."""
    skin = build_rear_service_skin(authority)
    review_map = {
        CELL2_REAR_REVIEW_EXPORT_NAMES[0]: skin.cover,
        CELL2_REAR_REVIEW_EXPORT_NAMES[1]: skin.cover_removal_envelope_reference,
        CELL2_REAR_REVIEW_EXPORT_NAMES[2]: skin.package_keepout_reference,
    }
    step_files: list[str] = []
    for name, solid in review_map.items():
        filename = f"{name}.step"
        cq.exporters.export(solid, str(output / filename))
        step_files.append(filename)

    manifest = skin.manifest()
    with (output / CELL2_REAR_REVIEW_MANIFEST).open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")
    return manifest, step_files


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

    exterior_candidate_manifest = _export_cell2_exterior_candidate_review(output, model)
    rear_service_manifest, rear_review_step_files = _export_cell2_rear_service_review(output, model.authority)

    # Reconstruct the accepted mixed-waste realization once and share it with the
    # canonical registry and release report. Cell 2 review geometry remains independent
    # evidence and never enters the physical-material compound below.
    waste_release = build_current_cell4_waste_backbone_release()
    component_registry = build_current_component_registry(model=model, waste_release=waste_release)

    model_component_by_name = {component.name: component for component in model.components}
    physical_material_names = component_registry.physical_material_model_component_names
    missing_material = tuple(name for name in physical_material_names if name not in model_component_by_name)
    if missing_material:
        raise ValueError(f"component registry selects model material that does not exist: {missing_material}")
    physical_shapes = [model_component_by_name[name].solid.val() for name in physical_material_names]
    if not physical_shapes:
        raise ValueError("canonical component registry selected no released physical material")
    compound = cq.Compound.makeCompound(physical_shapes)
    cq.exporters.export(compound, str(output / "masck_one_development_assembly.step"))

    development_assembly_exclusions = tuple(sorted(set(model_component_by_name) - set(physical_material_names)))

    registry_manifest = component_registry.manifest()
    with (output / "component_registry.json").open("w", encoding="utf-8") as handle:
        json.dump(registry_manifest, handle, indent=2, allow_nan=False)
        handle.write("\n")

    brand_identity_manifest = build_brand_identity_manifest()
    with (output / "brand_identity.json").open("w", encoding="utf-8") as handle:
        json.dump(brand_identity_manifest, handle, indent=2, allow_nan=False)
        handle.write("\n")

    checks = run_assertions(model)
    boundary_topology = build_verified_interface_boundary_topology(
        model.authority, model.facial_surface, model.coverage_mesh, model.compliant_interface_topology
    )
    attachment = build_interface_attachment_architecture(model.authority, boundary_topology)
    contact_framework = build_contact_simulation_framework(model.authority, attachment)
    structural_frame = build_structural_frame_topology(model.authority, attachment)
    waste_cartridge_dfm = build_waste_cartridge_dfm_audit(model=model)
    report = {
        "project": "Masck One",
        "parent_brand": "MASCK",
        "brand_identity": brand_identity_manifest,
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
                model.authority, model.facial_surface, model.coverage_mesh, model.compliant_interface_topology
            ),
            "interface_attachment": attachment.manifest(),
            "structural_frame": structural_frame.manifest(),
            "realized_waste_backbone": _realized_waste_backbone_manifest(waste_release),
        },
        "review_geometry": {
            "cell2_exterior_candidate": exterior_candidate_manifest,
            "cell2_rear_service_skin": rear_service_manifest,
        },
        "dfm_gates": {"waste_cartridge": waste_cartridge_dfm.manifest()},
        "analysis_frameworks": {"contact_simulation": contact_framework.manifest()},
        "development_assembly_material_components": list(physical_material_names),
        "development_assembly_exclusions": [
            *development_assembly_exclusions,
            "cell2_rigid_shell_candidate_review",
            *CELL2_REAR_REVIEW_EXPORT_NAMES,
        ],
        "exported_step_files": (
            [f"{name}.step" for name in export_map]
            + [CELL2_EXTERIOR_REVIEW_STEP]
            + rear_review_step_files
            + ["masck_one_development_assembly.step"]
        ),
        "exported_manifests": [
            "component_registry.json",
            "brand_identity.json",
            CELL2_EXTERIOR_REVIEW_MANIFEST,
            CELL2_REAR_REVIEW_MANIFEST,
            "build_report.json",
        ],
        "note": (
            "BLOCKED checks are unresolved evidence gates, not software failures. The canonical component registry "
            "is the sole physical-material boundary for the development assembly; Cell 2 eye-rolled shell and rear "
            "service geometry are independently built and STEP round-tripped as review-only evidence and never enter "
            "that compound. The MASCK brand identity manifest is a source-bound product/interaction/CMF contract only "
            "and does not override engineering authority, protected geometry, manufacturing truth or physical-validation "
            "gates. The structural frame remains a topology/datum contract without invented cross-section or material. "
            "The realized waste backbone is emitted as validated centerline/manifold data, not selected tubing, pump, "
            "barrier, connector, hydraulic, service or physical-performance evidence. The waste-cartridge STEP remains "
            "an external package-envelope reference only. Cell 2 rear-service geometry remains review-only until dry-side "
            "package reflow, attachment and battery extraction are reconciled. Digital topology/manifests and analysis "
            "frameworks are not physical validation evidence."
        ),
    }
    with (output / "build_report.json").open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, allow_nan=False)
        handle.write("\n")
    return report
