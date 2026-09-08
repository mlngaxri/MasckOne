from __future__ import annotations

import json
import math
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
from .structural_frame_actuator_reactions import build_structural_frame_actuator_reactions
from .structural_frame_crown_support import build_structural_frame_crown_support
from .structural_frame_realization import build_structural_frame_realization
from .structural_frame_retention_roots import build_structural_frame_retention_roots
from .structural_frame_shell_joints import build_structural_frame_shell_joints
from .waste_cartridge_dfm import build_waste_cartridge_dfm_audit


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


def _write_manifest(path: Path, payload: dict[str, object]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


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
    structural_frame_realization = build_structural_frame_realization(
        model=model,
        structural_frame=structural_frame,
    )
    shell_joints = build_structural_frame_shell_joints(
        model=model,
        frame=structural_frame_realization,
    )
    actuator_reactions = build_structural_frame_actuator_reactions(
        model=model,
        shell_joints=shell_joints,
    )
    retention_roots = build_structural_frame_retention_roots(
        model=model,
        reactions=actuator_reactions,
    )
    crown_support = build_structural_frame_crown_support(
        model=model,
        roots=retention_roots,
    )
    waste_cartridge_dfm = build_waste_cartridge_dfm_audit(model=model)

    registry_manifest = component_registry.manifest()
    brand_identity_manifest = build_brand_identity_manifest()
    structural_frame_realization_manifest = structural_frame_realization.manifest()
    shell_joint_manifest = shell_joints.manifest()
    actuator_reaction_manifest = actuator_reactions.manifest()
    retention_root_manifest = retention_roots.manifest()
    crown_support_manifest = crown_support.manifest()

    structural_frame_step_name = "structural_frame_reaction_loop_v1.step"
    shell_joint_frame_step_name = "structural_frame_with_positive_shell_tenons.step"
    shell_joint_shell_step_name = "rigid_shell_with_frame_mortises_and_pin_bores.step"
    actuator_reaction_frame_step_name = "structural_frame_with_four_actuator_reaction_counterparts.step"
    retention_root_frame_step_name = "structural_frame_with_bilateral_retention_roots.step"
    crown_support_step_name = "structural_frame_crown_support.step"

    shell_joint_pin_step_names = [
        f"structural_frame_shell_capture_pin_{index}.step"
        for index, _joint in enumerate(shell_joints.joints, start=1)
    ]
    shell_joint_retainer_step_names = [
        f"structural_frame_shell_pin_retainer_{index}.step"
        for index, _joint in enumerate(shell_joints.joints, start=1)
    ]
    retention_root_pin_step_names = [
        f"{root.root_id.lower()}_capture_pin.step" for root in retention_roots.roots
    ]
    retention_root_retainer_step_names = [
        f"{root.root_id.lower()}_split_retainer.step" for root in retention_roots.roots
    ]
    crown_pin_step_names = [
        f"structural_frame_crown_{crown_attachment.side.lower()}_capture_pin.step"
        for crown_attachment in crown_support.attachments
    ]
    crown_retainer_step_names = [
        f"structural_frame_crown_{crown_attachment.side.lower()}_split_retainer.step"
        for crown_attachment in crown_support.attachments
    ]

    structural_manifest_files = [
        "structural_frame_realization_manifest.json",
        "structural_frame_shell_joints_manifest.json",
        "structural_frame_actuator_reactions_manifest.json",
        "structural_frame_retention_roots_manifest.json",
        "structural_frame_crown_support_manifest.json",
    ]
    structural_step_files = [
        structural_frame_step_name,
        shell_joint_frame_step_name,
        shell_joint_shell_step_name,
        *shell_joint_pin_step_names,
        *shell_joint_retainer_step_names,
        actuator_reaction_frame_step_name,
        retention_root_frame_step_name,
        *retention_root_pin_step_names,
        *retention_root_retainer_step_names,
        crown_support_step_name,
        *crown_pin_step_names,
        *crown_retainer_step_names,
    ]

    report = {
        "project": "Masck One",
        "parent_brand": "MASCK",
        "brand_identity": brand_identity_manifest,
        "authority_revision": model.authority.get("project", "authority_revision"),
        "development_phase": 3,
        "iteration": 15,
        "result": "PASS",
        "build_scope": "DEVELOPMENT_ONLY",
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
            "structural_frame_realization": structural_frame_realization_manifest,
            "structural_frame_shell_joints": shell_joint_manifest,
            "structural_frame_actuator_reactions": actuator_reaction_manifest,
            "structural_frame_retention_roots": retention_root_manifest,
            "structural_frame_crown_support": crown_support_manifest,
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
        "standalone_physical_geometry_pending_assembly_rebind": [
            structural_frame_realization.member_id,
            "STRUCTURAL_FRAME_POSITIVE_SHELL_JOINT_ARCHITECTURE_V2",
            "STRUCTURAL_FRAME_FOUR_ACTUATOR_REACTION_COUNTERPARTS_V1",
            "STRUCTURAL_FRAME_BILATERAL_RETENTION_ROOTS_V1",
            "STRUCTURAL_FRAME_BILATERAL_CROWN_SUPPORT_V1",
        ],
        "exported_step_files": [
            f"{component.name}.step" for component in components
        ]
        + structural_step_files
        + ["masck_one_development_assembly.step"],
        "exported_manifest_files": structural_manifest_files,
        "exported_manifests": [
            "component_registry.json",
            "brand_identity.json",
            *structural_manifest_files,
            "build_report.json",
            "package_manifest.json",
        ],
        "note": (
            "BLOCKED checks are unresolved evidence gates, not software failures. "
            "The canonical component registry is the sole physical-material membership "
            "authority for the development assembly. Package references, development "
            "references, protected keepouts, topology and unresolved identities remain "
            "non-material. Cell 6 structural frame, positive shell joints, actuator reaction "
            "counterparts, retention roots and crown support are deterministic standalone "
            "mechanical evidence pending explicit canonical assembly rebind. The MASCK brand "
            "identity manifest is a source-bound product, interaction and CMF contract only; "
            "it does not override engineering authority, protected geometry, manufacturing "
            "truth or physical-validation gates. Digital structural geometry does not establish "
            "material, strength, fatigue, process capability, production tolerance, fit, comfort, "
            "hair safety, tactile feel, acoustics, wear or service ergonomics. The realized waste "
            "backbone is emitted as validated centerline and manifold data, not selected tubing, "
            "pump, barrier, connector, hydraulic, service or physical-performance evidence. The "
            "waste-cartridge STEP remains an external package-envelope reference only until body, "
            "cavity, seal, retention and service geometry are realized. Digital topology, manifests "
            "and analysis frameworks are not physical validation evidence."
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

        structural_roundtrip: dict[str, dict[str, object]] = {}

        def export_verified(name: str, solid) -> None:
            path = stage / name
            cq.exporters.export(solid, str(path))
            source = cq.Compound.makeCompound(solid.vals())
            structural_roundtrip[name] = verify_step_geometry(source, path)

        export_verified(structural_frame_step_name, structural_frame_realization.solid)
        export_verified(shell_joint_frame_step_name, shell_joints.assembled_frame)
        export_verified(shell_joint_shell_step_name, shell_joints.modified_shell)
        for joint, pin_name, retainer_name in zip(
            shell_joints.joints,
            shell_joint_pin_step_names,
            shell_joint_retainer_step_names,
        ):
            export_verified(pin_name, joint.pin)
            export_verified(retainer_name, joint.retainer_clip)
        export_verified(
            actuator_reaction_frame_step_name,
            actuator_reactions.frame_with_reaction_counterparts,
        )
        export_verified(retention_root_frame_step_name, retention_roots.frame_with_retention_roots)
        for root, pin_name, retainer_name in zip(
            retention_roots.roots,
            retention_root_pin_step_names,
            retention_root_retainer_step_names,
        ):
            export_verified(pin_name, root.capture_pin)
            export_verified(retainer_name, root.split_retainer)
        export_verified(crown_support_step_name, crown_support.crown_support)
        for crown_attachment, pin_name, retainer_name in zip(
            crown_support.attachments,
            crown_pin_step_names,
            crown_retainer_step_names,
        ):
            export_verified(pin_name, crown_attachment.capture_pin)
            export_verified(retainer_name, crown_attachment.split_retainer)

        report["structural_frame_step_roundtrip"] = structural_roundtrip

        _write_manifest(stage / "component_registry.json", registry_manifest)
        _write_manifest(stage / "brand_identity.json", brand_identity_manifest)
        _write_manifest(
            stage / structural_manifest_files[0],
            structural_frame_realization_manifest,
        )
        _write_manifest(stage / structural_manifest_files[1], shell_joint_manifest)
        _write_manifest(stage / structural_manifest_files[2], actuator_reaction_manifest)
        _write_manifest(stage / structural_manifest_files[3], retention_root_manifest)
        _write_manifest(stage / structural_manifest_files[4], crown_support_manifest)
        _write_manifest(stage / "build_report.json", report)

    publish_package(output_dir, write_exports)
    return report
