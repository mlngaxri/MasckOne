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
from .contact_simulation import build_contact_simulation_framework
from .interface_attachment import build_interface_attachment_architecture
from .model import MasckOneModel, build_model
from .release_package import (
    ExportValidationError,
    development_readiness,
    publish_package,
    validate_checks,
)
from .realized_waste_backbone_release import build_current_cell4_waste_backbone_release
from .structural_frame import build_structural_frame_topology
from .waste_cartridge_dfm import build_waste_cartridge_dfm_audit


def _component_record(component, *, included: bool) -> dict:
    shapes = component.solid.vals()
    if not shapes or any(not isinstance(shape, cq.Shape) for shape in shapes):
        raise ExportValidationError(f"No B-rep shape for {component.name}")
    solids = [solid for shape in shapes for solid in shape.Solids()]
    if (not solids or any(not shape.isValid() for shape in shapes)
            or any(not solid.isValid() or not math.isfinite(solid.Volume())
                   or solid.Volume() <= 0 for solid in solids)):
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
        "geometry_role": "DEVELOPMENT_GEOMETRY" if included else "PACKAGE_REFERENCE_ONLY",
        "included_in_development_assembly": included,
        "solid_count": len(solids),
        "volume_mm3": sum(float(solid.Volume()) for solid in solids),
        "bounding_span_mm": spans,
        "volume_semantics": "GEOMETRIC_ONLY_NOT_MASS_OR_USABLE_FLUID_CAPACITY",
        "step_file": f"{component.name}.step",
    }


def _source_content_identity() -> dict[str, str]:
    root = Path(__file__).resolve().parents[2]
    paths = [root / "pyproject.toml", root / "config/masck_one_authority.yaml",
             root / "schemas/masck_one_authority.schema.json"]
    paths.extend(sorted((root / "src/masck_one").rglob("*.py")))
    return {p.relative_to(root).as_posix(): sha256(p.read_bytes()).hexdigest() for p in paths}


def _realized_waste_backbone_manifest() -> dict[str, object]:
    """Return the current validated route realization for deterministic release output."""
    release = build_current_cell4_waste_backbone_release()
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
        model.shell, model.nasal_interface, model.water_reservoir_envelope,
        model.waste_cartridge_envelope, model.battery_reference_envelope,
        *model.actuator_envelopes,
    )
    expected_names = (
        "rigid_shell", "nasal_lobe_membrane_reference", "water_reservoir_envelope",
        "waste_cartridge_envelope", "battery_reference_envelope",
        "actuator_envelope_1", "actuator_envelope_2", "actuator_envelope_3", "actuator_envelope_4",
    )
    if tuple(c.name for c in components) != expected_names:
        raise ExportValidationError("Export component identities changed; reconcile the export contract")
    # All seven package envelopes remain individually available for packaging review.
    # Only the authored shell and local membrane development geometry enter this compound.
    included_names = ("rigid_shell", "nasal_lobe_membrane_reference")
    development_assembly_exclusions = tuple(c.name for c in components if c.name not in included_names)
    records = [_component_record(c, included=c.name in included_names) for c in components]
    checks = run_assertions(model)
    check_records = [c.to_dict() for c in checks]
    validate_checks(check_records)
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
        "result": "PASS",
        "build_scope": "DEVELOPMENT_ONLY",
        "checks": check_records,
        "production_readiness": development_readiness(check_records, records),
        "components": records,
        "source_content_sha256": _source_content_identity(),
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
        "dfm_gates": {
            "waste_cartridge": waste_cartridge_dfm.manifest(),
        },
        "analysis_frameworks": {
            "contact_simulation": contact_framework.manifest(),
        },
        "development_assembly_exclusions": list(development_assembly_exclusions),
        "development_assembly_components": list(included_names),
        "exported_step_files": [f"{c.name}.step" for c in components] + ["masck_one_development_assembly.step"],
        "note": (
            "BLOCKED checks are unresolved evidence gates, not software failures. The structural frame is currently "
            "a topology/datum contract without invented cross-section or material; no frame STEP member geometry is "
            "released by Iteration 15. The realized waste backbone is emitted as validated centerline/manifold data, "
            "not selected tubing, pump, barrier, connector, hydraulic, service, or physical-performance evidence. "
            "Water, battery, actuator and waste-cartridge envelopes are package references and are excluded from "
            "the development material compound. The waste-cartridge STEP remains an external package-envelope reference only and is deliberately excluded "
            "from physical development-assembly material until body, cavity, seal, retention and service geometry are "
            "realized. The cartridge DFM gate records digital closure requirements only and does not establish usable "
            "capacity, retained-liquid behavior, sealing, leakage, hygiene, durability, disposal performance or wet-hand "
            "serviceability. Digital topology/manifests and analysis frameworks are not physical validation evidence."
        ),
    }
    # Complete all engineering/DFM/source checks and JSON serialization before any
    # STEP output is published. A failed kernel export cannot overwrite a good package.
    report_json = json.dumps(report, indent=2, allow_nan=False) + "\n"
    shapes = [shape for c in components if c.name in included_names for shape in c.solid.vals()]
    compound = cq.Compound.makeCompound(shapes)

    def write_exports(stage: Path) -> None:
        for component in components:
            cq.exporters.export(component.solid, str(stage / f"{component.name}.step"))
        cq.exporters.export(compound, str(stage / "masck_one_development_assembly.step"))
        (stage / "build_report.json").write_text(report_json, encoding="utf-8")

    publish_package(output_dir, write_exports)
    return report
