from __future__ import annotations

import json

import cadquery as cq
import pytest

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


@pytest.fixture(scope="module")
def released_cell6_package(tmp_path_factory):
    """Build the immutable canonical release package once for this contract module.

    export_release() performs the full Cell 6 B-rep realization, STEP emission,
    STEP round-trip validation and package publication. The tests below are
    independent read-only assertions over that same deterministic package, so
    rebuilding it once per assertion only repeats expensive OpenCascade work
    without increasing coverage.
    """

    output_dir = tmp_path_factory.mktemp("cell6_release_chain")
    report = export_release(output_dir)
    return output_dir, report


def test_export_release_preserves_current_mechanical_dependency_chain(released_cell6_package) -> None:
    output_dir, report = released_cell6_package

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
        payload = json.loads((output_dir / filename).read_text(encoding="utf-8"))
        assert payload["physical_validation_eligible"] is False

    for filename in (
        "structural_frame_with_four_actuator_reaction_counterparts.step",
        "structural_frame_with_bilateral_retention_roots.step",
        "structural_frame_crown_support.step",
    ):
        imported = cq.importers.importStep(str(output_dir / filename))
        assert imported.val().isValid()
        assert len(imported.val().Solids()) == 1
        assert imported.val().Volume() > 0.0


def test_release_report_keeps_solved_mechanical_geometry_out_of_canonical_assembly(
    released_cell6_package,
) -> None:
    _output_dir, report = released_cell6_package
    pending = set(report["standalone_physical_geometry_pending_assembly_rebind"])
    assert {
        "STRUCTURAL_FRAME_FOUR_ACTUATOR_REACTION_COUNTERPARTS_V1",
        "STRUCTURAL_FRAME_BILATERAL_RETENTION_ROOTS_V1",
        "STRUCTURAL_FRAME_BILATERAL_CROWN_SUPPORT_V1",
    } <= pending


def test_export_release_is_bound_to_complete_cell6_release_bundle(released_cell6_package) -> None:
    output_dir, report = released_cell6_package

    exported_steps = set(report["exported_step_files"])
    exported_manifests = set(report["exported_manifest_files"])
    pending = set(report["standalone_physical_geometry_pending_assembly_rebind"])

    assert set(EXPORTED_STEP_FILES) <= exported_steps
    assert set(EXPORTED_MANIFEST_FILES) <= exported_manifests
    assert set(STANDALONE_PHYSICAL_GEOMETRY_PENDING_ASSEMBLY_REBIND) == pending

    topology = report["digital_topology"]
    assert topology["structural_frame_dry_package_supports"]["physical_validation_eligible"] is False
    assert topology["structural_frame_shell_joint_service"]["physical_validation_eligible"] is False

    release_manifest_path = output_dir / "structural_frame_release_export_manifest.json"
    assert release_manifest_path.is_file()
    release_manifest = json.loads(release_manifest_path.read_text(encoding="utf-8"))
    assert release_manifest["exported_step_files"] == list(EXPORTED_STEP_FILES)
    assert release_manifest["exported_manifest_files"] == list(EXPORTED_MANIFEST_FILES)
    assert (
        release_manifest["standalone_physical_geometry_pending_assembly_rebind"]
        == list(STANDALONE_PHYSICAL_GEOMETRY_PENDING_ASSEMBLY_REBIND)
    )
    assert release_manifest["physical_validation_eligible"] is False
