from dataclasses import replace

import cadquery as cq
import pytest

import masck_one.assembly_boundary as assembly_boundary_module
from masck_one.assembly_boundary import (
    AssemblyBoundaryError,
    ROLE_PACKAGE_REFERENCE,
    ROLE_PHYSICAL_MATERIAL,
    SOURCE_GEOMETRY_GIT_BLOB_IDENTITIES,
    build_current_main_assembly_boundary,
)
from masck_one.export import export_release
from masck_one.model import Component, build_model


@pytest.fixture(scope="module")
def model():
    return build_model()


@pytest.fixture(scope="module")
def boundary(model):
    return build_current_main_assembly_boundary(model=model)


def test_current_main_material_reference_partition_is_complete_and_fail_closed(boundary):
    names = {item.source_component_name for item in boundary.instances}
    assert len(boundary.instances) == 14
    assert len(names) == 14
    assert tuple(item.source_component_name for item in boundary.physical_material_instances) == ("rigid_shell",)

    reference_names = {item.source_component_name for item in boundary.reference_instances}
    assert reference_names == names - {"rigid_shell"}
    assert "waste_cartridge_envelope" in reference_names
    assert "battery_reference_envelope" in reference_names
    assert "water_reservoir_envelope" in reference_names
    assert "nasal_lobe_membrane_reference" in reference_names
    assert all(f"actuator_envelope_{index}" in reference_names for index in range(1, 5))
    assert set(boundary.development_assembly_exclusions) == reference_names


def test_composer_consumes_exact_released_model_component_objects(model, boundary):
    source_by_name = {component.name: component for component in model.components}
    instance_by_name = {item.source_component_name: item for item in boundary.instances}
    assert set(source_by_name) == set(instance_by_name)
    for name, component in source_by_name.items():
        assert instance_by_name[name].source_component is component


def test_package_reference_cannot_be_promoted_to_material_by_flag_or_role(boundary):
    cartridge = next(item for item in boundary.instances if item.source_component_name == "waste_cartridge_envelope")
    assert cartridge.role == ROLE_PACKAGE_REFERENCE
    assert cartridge.include_in_physical_material is False
    with pytest.raises(AssemblyBoundaryError, match="material/reference mixing"):
        replace(cartridge, include_in_physical_material=True)
    with pytest.raises(AssemblyBoundaryError, match="role mismatch"):
        replace(cartridge, role=ROLE_PHYSICAL_MATERIAL, include_in_physical_material=True)


def test_physical_material_cannot_be_demoted_or_bool_coerced(boundary):
    shell = boundary.physical_material_instances[0]
    assert shell.role == ROLE_PHYSICAL_MATERIAL
    with pytest.raises(AssemblyBoundaryError, match="role mismatch"):
        replace(shell, role=ROLE_PACKAGE_REFERENCE, include_in_physical_material=False)
    with pytest.raises(AssemblyBoundaryError, match="exact bool"):
        replace(shell, include_in_physical_material=1)


def test_frame_and_evidence_status_spoofing_fail_closed(boundary):
    shell = boundary.physical_material_instances[0]
    with pytest.raises(AssemblyBoundaryError, match="canonical authority world frame"):
        replace(shell, coordinate_frame_id="MASCK_ONE_GLOBAL")
    with pytest.raises(AssemblyBoundaryError, match="evidence status changed"):
        replace(shell, evidence_status="PHYSICALLY_VALIDATED")


def test_model_source_blob_movement_requires_explicit_rebind(monkeypatch, model):
    monkeypatch.setattr(assembly_boundary_module, "SOURCE_MODEL_GIT_BLOB_SHA", "0" * 40)
    with pytest.raises(AssemblyBoundaryError, match="assembly source moved"):
        build_current_main_assembly_boundary(model=model)


def test_direct_geometry_producer_movement_requires_explicit_rebind(monkeypatch, model):
    tampered = tuple(
        (path, "0" * 40 if path == "src/masck_one/anatomy.py" else digest)
        for path, digest in SOURCE_GEOMETRY_GIT_BLOB_IDENTITIES
    )
    monkeypatch.setattr(assembly_boundary_module, "SOURCE_GEOMETRY_GIT_BLOB_IDENTITIES", tampered)
    with pytest.raises(AssemblyBoundaryError, match=r"assembly source moved at src/masck_one/anatomy\.py"):
        build_current_main_assembly_boundary(model=model)


def test_same_name_status_geometry_substitution_fails_closed(boundary):
    shell = boundary.physical_material_instances[0]
    spoof = Component(
        name=shell.source_component.name,
        solid=cq.Workplane("XY").box(1.0, 1.0, 1.0),
        status=shell.source_component.status,
        notes=shell.source_component.notes,
    )
    with pytest.raises(AssemblyBoundaryError, match="source-component B-rep moved"):
        replace(shell, source_component=spoof)


def test_supplied_model_geometry_must_match_released_canonical_build(model):
    spoof_shell = replace(
        model.shell,
        solid=cq.Workplane("XY").box(1.0, 1.0, 1.0),
    )
    spoof_model = replace(model, shell=spoof_shell)
    with pytest.raises(AssemblyBoundaryError, match="supplied model B-rep differs"):
        build_current_main_assembly_boundary(model=spoof_model)


def test_manifest_is_deterministic_and_preserves_source_graph_and_brep_identity(model, boundary):
    second = build_current_main_assembly_boundary(model=model)
    manifest = boundary.manifest()
    assert second.manifest() == manifest
    assert len(manifest["manifest_sha256"]) == 64
    assert manifest["physical_validation_eligible"] is False
    assert manifest["physical_material_names"] == ["rigid_shell"]
    assert manifest["source_geometry_git_blob_identities"] == [
        list(item) for item in SOURCE_GEOMETRY_GIT_BLOB_IDENTITIES
    ]
    assert len(manifest["source_geometry_git_blob_identities"]) == 11
    assert all(len(item["source_component_brep_sha256"]) == 64 for item in manifest["instances"])


def test_material_and_reference_compounds_are_separate(boundary):
    material = boundary.physical_material_compound()
    references = boundary.reference_review_compound()
    assert len(material.Solids()) == 1
    assert len(references.Solids()) == 13


def test_release_export_uses_boundary_and_retains_reference_review_geometry(tmp_path):
    report = export_release(tmp_path)
    manifest = report["assembly_boundary"]
    assert manifest["physical_material_names"] == ["rigid_shell"]
    assert "waste_cartridge_envelope" in manifest["reference_review_names"]
    assert "waste_cartridge_envelope" in report["development_assembly_exclusions"]
    assert len(manifest["source_geometry_git_blob_identities"]) == 11
    assert all(len(item["source_component_brep_sha256"]) == 64 for item in manifest["instances"])
    assert "masck_one_reference_review_compound.step" in report["exported_step_files"]
    assert (tmp_path / "masck_one_development_assembly.step").is_file()
    assert (tmp_path / "masck_one_reference_review_compound.step").is_file()
