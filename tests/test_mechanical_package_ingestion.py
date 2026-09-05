from __future__ import annotations

import json
from pathlib import Path
import subprocess

import cadquery as cq
import pytest

import masck_one.mechanical_package_ingestion as ingestion
from masck_one.mechanical_package_ingestion import (
    CELL3_SOURCE_BLOBS,
    SOURCE_CELL3_HEAD_SHA,
    SOURCE_MAIN_SHA,
    MechanicalPackageIngestionError,
    MechanicalPackageIntegration,
    MechanicalSourceBinding,
    build_mechanical_package_integration,
    export_mechanical_package_review,
)
from masck_one.model import build_model
from masck_one.right_quick_release_assembly import build_right_quick_release_assembly
from masck_one.right_quick_release_latch import RELEASE_TRAVEL_MM


@pytest.fixture(scope="module")
def mechanical_integration() -> MechanicalPackageIntegration:
    """Build the immutable Cell 1 integration once for this CAD-heavy module."""
    return build_mechanical_package_integration()


def _git(*args: str) -> str:
    return subprocess.check_output(("git", *args), text=True).strip()


def test_exact_cell3_source_head_is_ancestor_and_source_blobs_are_bound():
    _git("cat-file", "-e", f"{SOURCE_CELL3_HEAD_SHA}^{{commit}}")
    assert subprocess.run(
        ("git", "merge-base", "--is-ancestor", SOURCE_CELL3_HEAD_SHA, "HEAD"),
        check=False,
    ).returncode == 0
    for path, expected_blob in CELL3_SOURCE_BLOBS:
        assert _git("hash-object", path) == expected_blob


def test_source_binding_fails_closed_on_main_head_frame_or_blob_drift(
    mechanical_integration: MechanicalPackageIntegration,
):
    binding = mechanical_integration.binding
    binding.validate()

    with pytest.raises(MechanicalPackageIngestionError, match="current released main"):
        MechanicalSourceBinding(
            source_main_sha="f" * 40,
            source_cell3_pr=binding.source_cell3_pr,
            source_cell3_head_sha=binding.source_cell3_head_sha,
            authority_revision=binding.authority_revision,
            authority_blob_sha=binding.authority_blob_sha,
            model_blob_sha=binding.model_blob_sha,
            structural_frame_blob_sha=binding.structural_frame_blob_sha,
            cell3_source_blobs=binding.cell3_source_blobs,
            world_frame_id=binding.world_frame_id,
        ).validate()
    with pytest.raises(MechanicalPackageIngestionError, match="exact Cell 3 head"):
        MechanicalSourceBinding(
            source_main_sha=SOURCE_MAIN_SHA,
            source_cell3_pr=binding.source_cell3_pr,
            source_cell3_head_sha="e" * 40,
            authority_revision=binding.authority_revision,
            authority_blob_sha=binding.authority_blob_sha,
            model_blob_sha=binding.model_blob_sha,
            structural_frame_blob_sha=binding.structural_frame_blob_sha,
            cell3_source_blobs=binding.cell3_source_blobs,
            world_frame_id=binding.world_frame_id,
        ).validate()
    with pytest.raises(MechanicalPackageIngestionError, match="canonical authority world frame"):
        MechanicalSourceBinding(
            source_main_sha=SOURCE_MAIN_SHA,
            source_cell3_pr=binding.source_cell3_pr,
            source_cell3_head_sha=binding.source_cell3_head_sha,
            authority_revision=binding.authority_revision,
            authority_blob_sha=binding.authority_blob_sha,
            model_blob_sha=binding.model_blob_sha,
            structural_frame_blob_sha=binding.structural_frame_blob_sha,
            cell3_source_blobs=binding.cell3_source_blobs,
            world_frame_id="MASCK_ONE_LOCAL_MECHANISM",
        ).validate()
    stale_blobs = list(binding.cell3_source_blobs)
    stale_blobs[0] = (stale_blobs[0][0], "d" * 40)
    with pytest.raises(MechanicalPackageIngestionError, match="source blob set changed"):
        MechanicalSourceBinding(
            source_main_sha=SOURCE_MAIN_SHA,
            source_cell3_pr=binding.source_cell3_pr,
            source_cell3_head_sha=binding.source_cell3_head_sha,
            authority_revision=binding.authority_revision,
            authority_blob_sha=binding.authority_blob_sha,
            model_blob_sha=binding.model_blob_sha,
            structural_frame_blob_sha=binding.structural_frame_blob_sha,
            cell3_source_blobs=tuple(stale_blobs),
            world_frame_id=binding.world_frame_id,
        ).validate()


def test_released_actuator_objects_are_consumed_without_reauthoring(monkeypatch):
    # This one intentionally needs a separate build because identity, not equality,
    # is the regression being protected.
    baseline = build_model()
    monkeypatch.setattr(ingestion, "build_model", lambda: baseline)
    integration = ingestion.build_mechanical_package_integration()
    assert integration.actuator_components is baseline.actuator_envelopes
    assert len(integration.actuator_components) == 4
    assert all(
        consumed is released
        for consumed, released in zip(integration.actuator_components, baseline.actuator_envelopes)
    )


def test_frame_stays_topology_only_and_whole_frame_blockers_remain_visible(
    mechanical_integration: MechanicalPackageIntegration,
):
    frame = mechanical_integration.frame
    assert frame.geometry_maturity == "TOPOLOGY_ONLY_3D_FRAME_NOT_YET_RELEASED"
    assert frame.cross_section_dimensions_mm is None
    assert frame.material_selection is None
    assert "REALIZE_3D_FRAME_MEMBER_GEOMETRY_AND_CROSS_SECTION" in frame.unresolved_requirements
    assert "LEFT_RETENTION_TO_FRAME_GEOMETRY_NOT_CURRENT_MAIN_RELEASED" in mechanical_integration.unresolved_integration
    assert "ACTUATOR_REACTION_CARRIERS_AND_FINAL_MECHANICAL_STOPS_NOT_CURRENT_MAIN_RELEASED" in mechanical_integration.unresolved_integration
    assert mechanical_integration.physical_validation_eligible is False


def test_active_static_package_uses_split_guide_and_never_reactivates_one_piece_capsule(
    mechanical_integration: MechanicalPackageIntegration,
):
    source_ids = {record.source_id for record in mechanical_integration.static_solids}
    assembly_ids = {record.assembly_id for record in mechanical_integration.static_solids}
    assert "RIGHT_LATCH_GUIDE_LOWER_BODY" in source_ids
    assert "RIGHT_LATCH_GUIDE_UPPER_CLOSURE" in source_ids
    assert "MECH_RIGHT_GUIDE_LOWER" in assembly_ids
    assert "MECH_RIGHT_GUIDE_UPPER" in assembly_ids
    assert "RIGHT_LATCH_GUIDE_CAPSULE" not in source_ids
    assert len(mechanical_integration.static_compound.val().Solids()) >= 4
    assert mechanical_integration.static_compound.val().isValid()


def test_cell1_integration_package_digests_equal_independently_rebuilt_cell3_source_chain(
    mechanical_integration: MechanicalPackageIntegration,
):
    model = build_model()
    source = build_right_quick_release_assembly(model=model)
    assert mechanical_integration.source_assembly_package_sha256 == source.package_sha256
    assert mechanical_integration.source_reset_package_sha256 == source.reset.package_sha256
    assert mechanical_integration.source_continuous_sweep_package_sha256 == source.continuous.package_sha256


def test_operational_reset_and_factory_states_are_first_class_and_ordered(
    mechanical_integration: MechanicalPackageIntegration,
):
    assert tuple(state.state_id for state in mechanical_integration.states) == (
        "LATCHED",
        "RELEASING_DETENT_LIFTED",
        "RELEASE_TRAVEL_LOW_OFFSET",
        "RELEASE_TRAVEL_HIGH_OFFSET",
        "RELEASED_RESET_REQUIRED",
        "RESET_TRAVEL_HIGH_OFFSET",
        "RESET_DETENT_LIFTED",
        "RESET_TRAVEL_LOW_OFFSET",
        "RESET_RESEATED_LATCHED",
        "GUIDE_OPEN_LOWER_HALF",
        "SLIDER_INSERTION",
        "UPPER_CLOSURE_DESCENT_HOOKS_DEFLECTED",
        "HOOK_RELAXATION_TO_POSITIVE_CAPTURE",
        "ASSEMBLED_OPERATIONAL",
    )
    assert all(state.full_head_removal_included is False for state in mechanical_integration.states)
    assert "FULL_POST_RELEASE_WHOLE_HEAD_REMOVAL_TRAJECTORY_OPEN" in mechanical_integration.unresolved_integration


def test_exact_release_and_factory_motion_breps_are_preserved_with_actual_digests(
    mechanical_integration: MechanicalPackageIntegration,
):
    motion = {record.assembly_id: record for record in mechanical_integration.motion_solids}

    exact = motion["MOTION_RIGHT_EXACT_WITHDRAWAL_SWEEP"]
    bb = exact.solid.val().BoundingBox()
    assert exact.solid.val().isValid()
    assert len(exact.solid.val().Solids()) == 1
    assert bb.xmin == pytest.approx(73.5, abs=1e-6)
    assert bb.xmax == pytest.approx(100.0, abs=1e-6)
    assert bb.ymin == pytest.approx(-5.0, abs=1e-6)
    assert bb.ymax == pytest.approx(5.0, abs=1e-6)
    assert bb.zmin == pytest.approx(-22.5, abs=1e-6)
    assert bb.zmax == pytest.approx(-15.5, abs=1e-6)
    assert len(exact.brep_sha256) == 64

    factory = motion["FACTORY_RIGHT_SLIDER_INSERTION_SWEEP"]
    fbb = factory.solid.val().BoundingBox()
    assert fbb.xmin == pytest.approx(73.5, abs=1e-6)
    assert fbb.xmax == pytest.approx(92.7, abs=1e-6)
    assert fbb.ymin == pytest.approx(-5.0, abs=1e-6)
    assert fbb.ymax == pytest.approx(5.0, abs=1e-6)
    assert fbb.zmin == pytest.approx(-22.5, abs=1e-6)
    assert fbb.zmax == pytest.approx(-7.5, abs=1e-6)


def test_released_slider_state_is_exact_plus_7p3_mm_rigid_translation(
    mechanical_integration: MechanicalPackageIntegration,
):
    static = {record.assembly_id: record for record in mechanical_integration.static_solids}
    motion = {record.assembly_id: record for record in mechanical_integration.motion_solids}
    latched = static["MECH_RIGHT_SLIDER_LATCHED"].solid.val().BoundingBox()
    released = motion["MOTION_RIGHT_SLIDER_RELEASED_STATE"].solid.val().BoundingBox()
    assert released.xmin - latched.xmin == pytest.approx(RELEASE_TRAVEL_MM, abs=1e-9)
    assert released.xmax - latched.xmax == pytest.approx(RELEASE_TRAVEL_MM, abs=1e-9)
    assert released.ymin == pytest.approx(latched.ymin, abs=1e-9)
    assert released.ymax == pytest.approx(latched.ymax, abs=1e-9)
    assert released.zmin == pytest.approx(latched.zmin, abs=1e-9)
    assert released.zmax == pytest.approx(latched.zmax, abs=1e-9)


def test_all_integrated_motion_clears_released_fixed_geometry_and_waste_service_envelopes(
    mechanical_integration: MechanicalPackageIntegration,
):
    assert mechanical_integration.collision_checks
    assert all(check.passes for check in mechanical_integration.collision_checks)
    assert max(check.intersection_volume_mm3 for check in mechanical_integration.collision_checks) == 0.0
    assert mechanical_integration.waste_separation_checks
    assert all(check.passes for check in mechanical_integration.waste_separation_checks)
    assert min(check.separation_mm for check in mechanical_integration.waste_separation_checks) > 0.0


def test_manifest_and_brep_provenance_are_deterministic_and_physically_fail_closed(
    mechanical_integration: MechanicalPackageIntegration,
):
    manifest_a = mechanical_integration.manifest()
    manifest_b = mechanical_integration.manifest()
    assert manifest_a == manifest_b
    assert len(mechanical_integration.integration_sha256) == 64
    assert manifest_a["integration_sha256"] == mechanical_integration.integration_sha256
    assert len(manifest_a["static_compound_brep_sha256"]) == 64
    assert manifest_a["physical_validation_eligible"] is False
    assert "NOT_RETENTION_FIT_COMFORT_RELEASE_FORCE_TIME" in manifest_a["evidence_status"]
    assert "RELEASE_FORCE_5_TO_12_N_PHYSICAL_GATE_OPEN" in manifest_a["unresolved_integration"]
    assert "RELEASE_TIME_LE_2S_PHYSICAL_GATE_OPEN" in manifest_a["unresolved_integration"]


def test_review_export_roundtrips_static_and_exact_motion_geometry(
    tmp_path: Path,
    mechanical_integration: MechanicalPackageIntegration,
):
    outputs = export_mechanical_package_review(tmp_path, mechanical_integration)
    by_name = {path.name: path for path in outputs}
    assert "cell1_mechanical_static_candidate.step" in by_name
    assert "motion_right_exact_withdrawal_sweep.step" in by_name
    assert "cell1_mechanical_package_ingestion_manifest.json" in by_name

    static = cq.importers.importStep(str(by_name["cell1_mechanical_static_candidate.step"]))
    sweep = cq.importers.importStep(str(by_name["motion_right_exact_withdrawal_sweep.step"]))
    assert static.val().isValid()
    assert len(static.val().Solids()) >= 4
    assert sweep.val().isValid()
    assert len(sweep.val().Solids()) == 1

    manifest = json.loads(
        by_name["cell1_mechanical_package_ingestion_manifest.json"].read_text(encoding="utf-8")
    )
    assert manifest["schema"] == "MASCK_ONE_CELL1_MECHANICAL_PACKAGE_INGESTION_V1"
    assert manifest["integration_sha256"] == mechanical_integration.integration_sha256
    assert manifest["physical_validation_eligible"] is False
