from __future__ import annotations

from dataclasses import replace
import subprocess

import pytest

from masck_one.assembly_composer import (
    AUTHORITY_REVISION,
    SOURCE_AUTHORITY_GIT_BLOB_SHA,
    SOURCE_MAIN_SHA,
    SOURCE_MODEL_GIT_BLOB_SHA,
    AssemblyComposerError,
    CanonicalTransform,
    build_integrated_assembly_skeleton,
)
from masck_one.model import build_model


def test_composer_consumes_exact_released_source_objects_without_repositioning() -> None:
    model = build_model()
    skeleton = build_integrated_assembly_skeleton(model)
    source_by_name = {component.name: component for component in model.components}

    assert skeleton.source_main_sha == SOURCE_MAIN_SHA
    assert skeleton.authority_revision == AUTHORITY_REVISION
    assert skeleton.source_authority_git_blob_sha == SOURCE_AUTHORITY_GIT_BLOB_SHA
    assert len(skeleton.instances) == len(model.components) == 14
    for instance in skeleton.instances:
        assert instance.source_component is source_by_name[instance.source_component_name]
        assert instance.transform.is_identity
        assert instance.transform.source_frame_id == "MASCK_ONE_AUTHORITY_WORLD_MM"
        assert instance.transform.target_frame_id == "MASCK_ONE_AUTHORITY_WORLD_MM"


def test_development_compound_is_exact_non_reference_source_set() -> None:
    model = build_model()
    skeleton = build_integrated_assembly_skeleton(model)
    expected = tuple(component for component in model.components if component.status != "REFERENCE_ONLY")
    expected_shapes = [component.solid.val() for component in expected]
    expected_compound = __import__("cadquery").Compound.makeCompound(expected_shapes)
    actual_compound = skeleton.development_compound()

    assert len(skeleton.development_instances) == len(expected) == 9
    assert len(actual_compound.Solids()) == len(expected_compound.Solids())
    actual_box = actual_compound.BoundingBox()
    expected_box = expected_compound.BoundingBox()
    assert (actual_box.xlen, actual_box.ylen, actual_box.zlen) == pytest.approx(
        (expected_box.xlen, expected_box.ylen, expected_box.zlen), abs=1e-12
    )


def test_reference_keepouts_are_kept_out_of_development_compound() -> None:
    model = build_model()
    skeleton = build_integrated_assembly_skeleton(model)

    assert len(skeleton.reference_keepout_instances) == 5
    assert {item.source_component_name for item in skeleton.reference_keepout_instances} == {
        "visual_eye_left",
        "visual_eye_right",
        "visual_mouth",
        "visual_nostril_left",
        "visual_nostril_right",
    }
    assert all(not item.include_in_development_compound for item in skeleton.reference_keepout_instances)
    assert all(item.source_component.status == "REFERENCE_ONLY" for item in skeleton.reference_keepout_instances)


def test_assembly_source_git_blobs_match_checked_out_release_sources() -> None:
    actual_model_blob = subprocess.check_output(
        ["git", "hash-object", "src/masck_one/model.py"], text=True
    ).strip()
    actual_authority_blob = subprocess.check_output(
        ["git", "hash-object", "config/masck_one_authority.yaml"], text=True
    ).strip()
    assert actual_model_blob == SOURCE_MODEL_GIT_BLOB_SHA
    assert actual_authority_blob == SOURCE_AUTHORITY_GIT_BLOB_SHA


def test_non_identity_transform_is_rejected_instead_of_mutating_subsystem_geometry() -> None:
    with pytest.raises(AssemblyComposerError, match="cannot transform released world-frame geometry"):
        CanonicalTransform(translation_xyz_mm=(1.0, 0.0, 0.0))


def test_stale_source_binding_fails_closed() -> None:
    skeleton = build_integrated_assembly_skeleton()
    with pytest.raises(AssemblyComposerError, match="model source blob is stale"):
        replace(skeleton, source_model_git_blob_sha="0" * 40)


def test_manifest_is_deterministic_and_preserves_evidence_firewall() -> None:
    first = build_integrated_assembly_skeleton()
    second = build_integrated_assembly_skeleton()

    assert first.manifest() == second.manifest()
    assert first.assembly_sha256 == second.assembly_sha256
    assert first.physical_validation_eligible is False
    assert "NOT_FIT_CLEARANCE_SERVICE_LOAD" in first.evidence_status
    assert all("NOT_A_PHYSICAL_VALIDATION" in item.evidence_status for item in first.instances)
