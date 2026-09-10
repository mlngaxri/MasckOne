from __future__ import annotations

import json
import math
import os
import re
from hashlib import sha256
from pathlib import Path

import cadquery as cq

from .assertions import run_assertions
from .boundary_release import (
    boundary_release_manifest,
    build_verified_interface_boundary_topology,
)
from .brand_identity import build_brand_identity_manifest
from .component_registry import build_current_component_registry
from .contact_simulation import build_contact_simulation_framework
from .integration_contract import integration_contract_manifest
from .interface_attachment import build_interface_attachment_architecture
from .model import MasckOneModel, build_model
from .release_package import (
    ExportValidationError,
    development_readiness,
    publish_package,
    validate_checks,
)
from .realized_waste_backbone_release import (
    Cell4WasteBackboneRelease,
    build_current_cell4_waste_backbone_release,
)
from .step_integrity import solid_volume, verify_step_geometry
from .structural_frame import build_structural_frame_topology
from .waste_cartridge_dfm import build_waste_cartridge_dfm_audit


_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_RELEASE_SOURCE_ENV = {
    "release_base_sha": "MASCK_ONE_RELEASE_BASE_SHA",
    "source_head_sha": "MASCK_ONE_SOURCE_HEAD_SHA",
    "source_head_tree_sha": "MASCK_ONE_SOURCE_HEAD_TREE_SHA",
    "tested_commit_sha": "MASCK_ONE_TESTED_COMMIT_SHA",
    "tested_tree_sha": "MASCK_ONE_TESTED_TREE_SHA",
}


def _release_source_binding() -> dict[str, object]:
    values = {field: os.environ.get(env_name) for field, env_name in _RELEASE_SOURCE_ENV.items()}
    provided = {field: value for field, value in values.items() if value not in (None, "")}
    if not provided:
        return {
            "schema": "MASCK_ONE_RELEASE_SOURCE_BINDING_V1",
            "binding_state": "UNBOUND_LOCAL_BUILD",
            **{field: None for field in _RELEASE_SOURCE_ENV},
            "physical_validation_eligible": False,
            "evidence_scope": "LOCAL_BUILD_NOT_RELEASE_PROVENANCE",
        }
    if len(provided) != len(_RELEASE_SOURCE_ENV):
        missing = sorted(set(_RELEASE_SOURCE_ENV) - set(provided))
        raise ExportValidationError(
            "Incomplete release source binding; missing environment fields: "
            + ", ".join(missing)
        )
    malformed = sorted(
        field
        for field, value in provided.items()
        if type(value) is not str or _SHA40.fullmatch(value) is None
    )
    if malformed:
        raise ExportValidationError(
            "Malformed release source binding SHA fields: " + ", ".join(malformed)
        )
    return {
        "schema": "MASCK_ONE_RELEASE_SOURCE_BINDING_V1",
        "binding_state": "CI_EXACT_BOUND",
        **provided,
        "physical_validation_eligible": False,
        "evidence_scope": "DIGITAL_SOURCE_PROVENANCE_ONLY",
    }


def _component_record(component, *, included: bool) -> dict:
    shapes = component.solid.vals()
    if not shapes or any(not isinstance(shape, cq.Shape) for shape in shapes):
        raise ExportValidationError(f"No B-rep shape for {component.name}")
    solids = [solid for shape in shapes for solid in shape.Solids()]
    if (
        not solids
        or any(not shape.isValid() for shape in shapes)
        or any(
            not solid.isValid()
            or not math.isfinite(solid.Volume())
            or solid.Volume() <= 0
            for solid in solids
        )
    ):
        raise ExportValidationError(f"Invalid or non-volumetric B-rep for {component.name}")
    compound = cq.Compound.makeCompound(shapes)
    bounds = compound.BoundingBox()
    spans = [float(bounds.xlen), float(bounds.ylen), float(bounds.zlen)]
    if any(not math.isfinite(span) or span <= 0 for span in spans):
        raise ExportValidationError(f"Invalid B-rep bounds for {component.name}")
    return {
        "name": component.name,
        "status": component.status,
        "notes": component.notes,
        "geometry_role": "PHYSICAL_MATERIAL" if included else "NON_MATERIAL_REFERENCE",
        "included_in_development_assembly": included,
        "solid_count": len(solids),
        "volume_mm3": solid_volume(compound),
        "volume_measurement": "SUM_OF_SOLIDS_ADAPTIVE_INTEGRATION_1E-12",
        "bounding_span_mm": spans,
        "volume_semantics": "GEOMETRIC_ONLY_NOT_MASS_OR_USABLE_FLUID_CAPACITY",
        "step_file": f"{component.name}.step",
    }


def _source_content_identity() -> dict[str, str]:
    root = Path(__file__).resolve().parents[2]
    paths = [
        root / "pyproject.toml",
        root / "config/masck_one_authority.yaml",
        root / "schemas/masck_one_authority.schema.json",
        root / "config/masck_brand_authority.yaml",
        root / "schemas/masck_brand_authority.schema.json",
    ]
    paths.extend(sorted((root / "brand/assets").glob("*")))
    paths.extend(sorted((root / "src/masck_one").rglob("*.py")))
    return {
        path.relative_to(root).as_posix(): sha256(path.read_bytes()).hexdigest()
        for path in paths
        if path.is_file()
    }


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


def export_release(
    output_dir: str | Path = "generated",
    model: MasckOneModel | None = None,
    *,
    production: bool = False,
) -> dict:
    if type(production) is not bool:
        raise ExportValidationError("production must be a bool")
    if production:
        raise ExportValidationError(
            "Production export is blocked: the current model contains development geometry "
            "and package references, with unresolved manufacturing and physical evidence."
        )

    model = model or build_model()
    components = (
        model.shell,
        model.nasal_interface,
        model.water_reservoir_envelope,
        model.waste_cartridge_envelope,
        model.battery_reference_envelope,
        *model.actuator_envelopes,
    )
    expected_names = (
        "rigid_shell",
        "nasal_lobe_membrane_reference",
        "water_reservoir_envelope",
        "waste_cartridge_envelope",
        "battery_reference_envelope",
        "actuator_envelope_1",
        "actuator_envelope_2",
        "actuator_envelope_3",
        "actuator_envelope_4",
    )
    if tuple(component.name for component in components) != expected_names:
        raise ExportValidationError(
            "Export component identities changed; reconcile the export contract"
        )

    waste_release = build_current_cell4_waste_backbone_release()
    component_registry = build_current_component_registry(
        model=model,
        waste_release=waste_release,
    )
    included_names = component_registry.physical_material_model_component_names
    component_by_name = {component.name: component for component in components}
    missing_material = tuple(
        name for name in included_names if name not in component_by_name
    )
    if missing_material:
        raise ExportValidationError(
            f"Canonical component registry selects absent export material: {missing_material}"
        )
    if not included_names:
        raise ExportValidationError(
            "Canonical component registry selected no released physical material"
        )

    development_assembly_exclusions = tuple(
        component.name for component in components if component.name not in included_names
    )
    records = [
        _component_record(component, included=component.name in included_names)
        for component in components
    ]

    checks = run_assertions(model)
    check_records = [check.to_dict() for check in checks]
    validate_checks(check_records)

    boundary_topology = build_verified_interface_boundary_topology(
        model.authority,
        model.facial_surface,
        model.coverage_mesh,
        model.compliant_interface_topology,
    )
    attachment = build_interface_attachment_architecture(
        model.authority,
        boundary_topology,
    )
    contact_framework = build_contact_simulation_framework(
        model.authority,
        attachment,
    )
    structural_frame = build_structural_frame_topology(
        model.authority,
        attachment,
    )
    waste_cartridge_dfm = build_waste_cartridge_dfm_audit(model=model)

    registry_manifest = component_registry.manifest()
    brand_identity_manifest = build_brand_identity_manifest()
    report = {
        "project": "Masck One",
        "parent_brand": "MASCK",
        "brand_identity": brand_identity_manifest,
        "authority_revision": model.authority.get("project", "authority_revision"),
        "development_phase": model.authority.get("project", "development_phase"),
        "iteration": model.authority.get("project", "completed_iteration"),
        "result": "PASS",
        "build_scope": "DEVELOPMENT_ONLY",
        "release_source_binding": _release_source_binding(),
        "integration_contract": integration_contract_manifest(),
        "checks": check_records,
        "production_readiness": development_readiness(check_records, records),
        "components": records,
        "component_registry": registry_manifest,
        "source_content_sha256": _source_content_identity(),
        "digital_topology": {
            "coverage": model.coverage_mesh.manifest(),
            "compliant_interface": model.compliant_interface_topology.manifest(
                model.coverage_mesh
            ),
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
        "development_assembly_material_components": list(included_names),
        "development_assembly_exclusions": list(development_assembly_exclusions),
        "development_assembly_components": list(included_names),
        "exported_step_files": [
            f"{component.name}.step" for component in components
        ]
        + ["masck_one_development_assembly.step"],
        "exported_manifests": [
            "component_registry.json",
            "brand_identity.json",
            "build_report.json",
            "package_manifest.json",
        ],
        "note": (
            "BLOCKED checks are unresolved evidence gates, not software failures. "
            "The canonical component registry is the sole physical-material membership "
            "authority for the development assembly. Package references, development "
            "references, protected keepouts, topology and unresolved identities remain "
            "non-material. The release source binding records CI source provenance only; "
            "it does not alter component ownership, geometry authority or physical evidence. "
            "The integration contract is navigation and edit ownership only; live GitHub "
            "supersedes its dated head snapshot and subsystem owners retain their internals. "
            "The MASCK brand identity manifest is a source-bound product, interaction and "
            "CMF contract only; it does not override engineering authority, protected geometry, "
            "manufacturing truth or physical-validation gates. The structural frame is currently "
            "a topology/datum contract without invented cross-section or material; no frame STEP "
            "member geometry is released by Iteration 15. The realized waste backbone is emitted "
            "as validated centerline and manifold data, not selected tubing, pump, barrier, "
            "connector, hydraulic, service or physical-performance evidence. The waste-cartridge "
            "STEP remains an external package-envelope reference only and is deliberately excluded "
            "from physical development-assembly material until body, cavity, seal, retention and "
            "service geometry are realized. Digital topology, manifests and analysis frameworks "
            "are not physical validation evidence."
        ),
    }
    json.dumps(report, allow_nan=False)

    shapes = [
        shape
        for component in components
        if component.name in included_names
        for shape in component.solid.vals()
    ]
    compound = cq.Compound.makeCompound(shapes)

    def write_exports(stage: Path) -> None:
        for component, record in zip(components, records):
            path = stage / f"{component.name}.step"
            cq.exporters.export(component.solid, str(path))
            source = cq.Compound.makeCompound(component.solid.vals())
            record["step_roundtrip"] = verify_step_geometry(source, path)

        assembly_path = stage / "masck_one_development_assembly.step"
        cq.exporters.export(compound, str(assembly_path))
        report["development_assembly_step_roundtrip"] = verify_step_geometry(
            compound,
            assembly_path,
        )

        (stage / "component_registry.json").write_text(
            json.dumps(registry_manifest, indent=2, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        (stage / "brand_identity.json").write_text(
            json.dumps(brand_identity_manifest, indent=2, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        (stage / "build_report.json").write_text(
            json.dumps(report, indent=2, allow_nan=False) + "\n",
            encoding="utf-8",
        )

    publish_package(output_dir, write_exports)
    return report
