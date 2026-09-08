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
from .realized_waste_backbone_release import build_current_cell4_waste_backbone_release
from .structural_frame import build_structural_frame_topology
from .structural_frame_actuator_reactions import build_structural_frame_actuator_reactions
from .structural_frame_crown_support import build_structural_frame_crown_support
from .structural_frame_realization import build_structural_frame_realization
from .structural_frame_retention_roots import build_structural_frame_retention_roots
from .structural_frame_shell_joints import build_structural_frame_shell_joints
from .waste_cartridge_dfm import build_waste_cartridge_dfm_audit


def _ensure_output_dir(path: str | Path) -> Path:
    output = Path(path).resolve()
    output.mkdir(parents=True, exist_ok=True)
    return output


def _realized_waste_backbone_manifest() -> dict[str, object]:
    release = build_current_cell4_waste_backbone_release()
    release_manifest = release.manifest()
    return {
        "release": release_manifest,
        "routes": [route.manifest() for route in release.realization.routes],
        "total_geometric_dead_volume_mL": release.realization.total_geometric_dead_volume_mL,
    }


def _write_manifest(path: Path, payload: dict[str, object]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")


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
    structural_frame_realization = build_structural_frame_realization(
        model=model,
        structural_frame=structural_frame,
    )

    structural_frame_step_name = "structural_frame_reaction_loop_v1.step"
    structural_frame_manifest_name = "structural_frame_realization_manifest.json"
    cq.exporters.export(structural_frame_realization.solid, str(output / structural_frame_step_name))
    structural_frame_realization_manifest = structural_frame_realization.manifest()
    _write_manifest(output / structural_frame_manifest_name, structural_frame_realization_manifest)

    shell_joints = build_structural_frame_shell_joints(model=model, frame=structural_frame_realization)
    shell_joint_manifest_name = "structural_frame_shell_joints_manifest.json"
    shell_joint_frame_step_name = "structural_frame_with_positive_shell_tenons.step"
    shell_joint_shell_step_name = "rigid_shell_with_frame_mortises_and_pin_bores.step"
    cq.exporters.export(shell_joints.assembled_frame, str(output / shell_joint_frame_step_name))
    cq.exporters.export(shell_joints.modified_shell, str(output / shell_joint_shell_step_name))
    shell_joint_pin_step_names: list[str] = []
    shell_joint_retainer_step_names: list[str] = []
    for index, joint in enumerate(shell_joints.joints, start=1):
        pin_name = f"structural_frame_shell_capture_pin_{index}.step"
        retainer_name = f"structural_frame_shell_pin_retainer_{index}.step"
        cq.exporters.export(joint.pin, str(output / pin_name))
        cq.exporters.export(joint.retainer_clip, str(output / retainer_name))
        shell_joint_pin_step_names.append(pin_name)
        shell_joint_retainer_step_names.append(retainer_name)
    shell_joint_manifest = shell_joints.manifest()
    _write_manifest(output / shell_joint_manifest_name, shell_joint_manifest)

    actuator_reactions = build_structural_frame_actuator_reactions(model=model, shell_joints=shell_joints)
    actuator_reaction_frame_step_name = "structural_frame_with_four_actuator_reaction_counterparts.step"
    actuator_reaction_manifest_name = "structural_frame_actuator_reactions_manifest.json"
    cq.exporters.export(
        actuator_reactions.frame_with_reaction_counterparts,
        str(output / actuator_reaction_frame_step_name),
    )
    actuator_reaction_manifest = actuator_reactions.manifest()
    _write_manifest(output / actuator_reaction_manifest_name, actuator_reaction_manifest)

    retention_roots = build_structural_frame_retention_roots(model=model, reactions=actuator_reactions)
    retention_root_frame_step_name = "structural_frame_with_bilateral_retention_roots.step"
    retention_root_manifest_name = "structural_frame_retention_roots_manifest.json"
    cq.exporters.export(retention_roots.frame_with_retention_roots, str(output / retention_root_frame_step_name))
    retention_root_pin_step_names: list[str] = []
    retention_root_retainer_step_names: list[str] = []
    for root in retention_roots.roots:
        token = root.root_id.lower()
        pin_name = f"{token}_capture_pin.step"
        retainer_name = f"{token}_split_retainer.step"
        cq.exporters.export(root.capture_pin, str(output / pin_name))
        cq.exporters.export(root.split_retainer, str(output / retainer_name))
        retention_root_pin_step_names.append(pin_name)
        retention_root_retainer_step_names.append(retainer_name)
    retention_root_manifest = retention_roots.manifest()
    _write_manifest(output / retention_root_manifest_name, retention_root_manifest)

    crown_support = build_structural_frame_crown_support(model=model, roots=retention_roots)
    crown_support_step_name = "structural_frame_crown_support.step"
    crown_support_manifest_name = "structural_frame_crown_support_manifest.json"
    cq.exporters.export(crown_support.crown_support, str(output / crown_support_step_name))
    crown_pin_step_names: list[str] = []
    crown_retainer_step_names: list[str] = []
    for crown_attachment in crown_support.attachments:
        token = crown_attachment.side.lower()
        pin_name = f"structural_frame_crown_{token}_capture_pin.step"
        retainer_name = f"structural_frame_crown_{token}_split_retainer.step"
        cq.exporters.export(crown_attachment.capture_pin, str(output / pin_name))
        cq.exporters.export(crown_attachment.split_retainer, str(output / retainer_name))
        crown_pin_step_names.append(pin_name)
        crown_retainer_step_names.append(retainer_name)
    crown_support_manifest = crown_support.manifest()
    _write_manifest(output / crown_support_manifest_name, crown_support_manifest)

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
            "structural_frame_realization": structural_frame_realization_manifest,
            "structural_frame_shell_joints": shell_joint_manifest,
            "structural_frame_actuator_reactions": actuator_reaction_manifest,
            "structural_frame_retention_roots": retention_root_manifest,
            "structural_frame_crown_support": crown_support_manifest,
            "realized_waste_backbone": _realized_waste_backbone_manifest(),
        },
        "dfm_gates": {"waste_cartridge": waste_cartridge_dfm.manifest()},
        "analysis_frameworks": {"contact_simulation": contact_framework.manifest()},
        "development_assembly_exclusions": list(development_assembly_exclusions),
        "standalone_physical_geometry_pending_assembly_rebind": [
            structural_frame_realization.member_id,
            "STRUCTURAL_FRAME_POSITIVE_SHELL_JOINT_ARCHITECTURE_V2",
            "STRUCTURAL_FRAME_FOUR_ACTUATOR_REACTION_COUNTERPARTS_V1",
            "STRUCTURAL_FRAME_BILATERAL_RETENTION_ROOTS_V1",
            "STRUCTURAL_FRAME_BILATERAL_CROWN_SUPPORT_V1",
        ],
        "exported_step_files": [f"{name}.step" for name in export_map]
        + [
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
            "masck_one_development_assembly.step",
        ],
        "exported_manifest_files": [
            structural_frame_manifest_name,
            shell_joint_manifest_name,
            actuator_reaction_manifest_name,
            retention_root_manifest_name,
            crown_support_manifest_name,
        ],
        "note": (
            "BLOCKED checks are unresolved evidence gates, not software failures. The source-bound reaction loop now exports the positive shell joints, "
            "four frame-side actuator reaction counterparts, bilateral retention-root counterparts, and bilateral crown-support attachment as one "
            "deterministic mechanical evidence chain. These mechanical B-reps remain standalone pending canonical assembly rebind. Digital geometry "
            "does not establish material, strength, fatigue, process capability, production tolerance, anthropometric fit, comfort, hair safety or "
            "physical service validation. Mounted carrier mates, dry/package supports, adjustment-guard installation, quick-release integration and "
            "continuous whole-head service motion remain unresolved."
        ),
    }
    with (output / "build_report.json").open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")
    return report