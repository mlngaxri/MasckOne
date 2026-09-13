from __future__ import annotations

import json

import cadquery as cq

from masck_one.export import export_release
from masck_one.structural_frame_release_export import (
    EXPORTED_MANIFEST_FILES,
    EXPORTED_STEP_FILES,
    STANDALONE_PHYSICAL_GEOMETRY_PENDING_ASSEMBLY_REBIND,
)


REQUIRED_MECHANICAL_STEPS = (
    "structural_frame_with_four_actuator_reaction_counterparts.step",
    "structural_frame_with_bilateral_retention_roots.step",
    "retention_root_wearer_left_capture_pin.step",
    "retention_root_wearer_left_split_retainer.step",
    "retention_root_wearer_right_capture_pin.step",
    "retention_root_wearer_right_split_retainer.step",
    "structural_frame_crown_support.step",
    "structural_frame_crown_wearer_left_capture_pin.step",
    "structural_frame_crown_wearer_left_split_retainer.step",
    "structural_frame_crown_wearer_right_capture_pin.step",
    "structural_frame_crown_wearer_right_split_retainer.step",
)

REQUIRED_MECHANICAL_MANIFESTS = (
    "structural_frame_actuator_reactions_manifest.json",
    "structural_frame_retention_roots_manifest.json",
    "structural_frame_crown_support_manifest.json",
)


def test_export_release_preserves_current_mechanical_dependency_chain(tmp_path) -> None:
    report = export_release(tmp_path)

    exported_steps = set(report["exported_step_files"])
    exported_manifests = set(report["exported_manifest_files"])
    assert set(REQUIRED_MECHANICAL_STEPS) <= exported_steps
    assert set(REQUIRED_MECHANICAL_MANIFESTS) <= exported_manifests

    topology = report["digital_topology"]
    reactions = topology["structural_frame_actuator_reactions"]
    roots = topology["structural_frame_retention_roots"]
    crown = topology["structural_frame_crown_support"]

    assert reactions["schema"] == "MASCK_ONE_STRUCTURAL_FRAME_ACTUATOR_REACTIONS_V1"
    assert roots["schema"] == "MASCK_ONE_STRUCTURAL_FRAME_RETENTION_ROOTS_V1"
    assert crown["schema"] == "MASCK_ONE_STRUCTURAL_FRAME_CROWN_SUPPORT_V1"

    assert roots["source_frame_reaction_architecture_sha256"] == reactions["architecture_sha256"]
    assert crown["source_retention_root_architecture_sha256"] == roots["architecture_sha256"]
    assert reactions["physical_validation_eligible"] is False
    assert roots["physical_validation_eligible"] is False
    assert crown["physical_validation_eligible"] is False

    for filename in REQUIRED_MECHANICAL_MANIFESTS:
        payload = json.loads((tmp_path / filename).read_text(encoding="utf-8"))
        assert payload["physical_validation_eligible"] is False

    for filename in (
        "structural_frame_with_four_actuator_reaction_counterparts.step",
        "structural_frame_with_bilateral_retention_roots.step",
        "structural_frame_crown_support.step",
    ):
        imported = cq.importers.importStep(str(tmp_path / filename))
        assert imported.val().isValid()
        assert len(imported.val().Solids()) == 1
        assert imported.val().Volume() > 0.0


def test_release_report_keeps_solved_mechanical_geometry_out_of_canonical_assembly(tmp_path) -> None:
    report = export_release(tmp_path)
    pending = set(report["standalone_physical_geometry_pending_assembly_rebind"])
    assert {
        "STRUCTURAL_FRAME_FOUR_ACTUATOR_REACTION_COUNTERPARTS_V1",
        "STRUCTURAL_FRAME_BILATERAL_RETENTION_ROOTS_V1",
        "STRUCTURAL_FRAME_BILATERAL_CROWN_SUPPORT_V1",
    } <= pending


def test_export_release_is_bound_to_complete_cell6_release_bundle(tmp_path) -> None:
    report = export_release(tmp_path)

    exported_steps = set(report["exported_step_files"])
    exported_manifests = set(report["exported_manifest_files"])
    pending = set(report["standalone_physical_geometry_pending_assembly_rebind"])

    assert set(EXPORTED_STEP_FILES) <= exported_steps
    assert set(EXPORTED_MANIFEST_FILES) <= exported_manifests
    assert set(STANDALONE_PHYSICAL_GEOMETRY_PENDING_ASSEMBLY_REBIND) == pending

    topology = report["digital_topology"]
    assert topology["structural_frame_dry_package_supports"]["physical_validation_eligible"] is False
    assert topology["structural_frame_shell_joint_service"]["physical_validation_eligible"] is False

    release_manifest_path = tmp_path / "structural_frame_release_export_manifest.json"
    assert release_manifest_path.is_file()
    release_manifest = json.loads(release_manifest_path.read_text(encoding="utf-8"))
    assert release_manifest["exported_step_files"] == list(EXPORTED_STEP_FILES)
    assert release_manifest["exported_manifest_files"] == list(EXPORTED_MANIFEST_FILES)
    assert (
        release_manifest["standalone_physical_geometry_pending_assembly_rebind"]
        == list(STANDALONE_PHYSICAL_GEOMETRY_PENDING_ASSEMBLY_REBIND)
    )
    assert release_manifest["physical_validation_eligible"] is False
