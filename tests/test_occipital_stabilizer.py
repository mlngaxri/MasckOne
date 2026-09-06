from __future__ import annotations

from dataclasses import replace
import json
import math

import cadquery as cq
import pytest

import masck_one.occipital_stabilizer as occipital_module
from masck_one.model import Component, build_model
from masck_one.occipital_stabilizer import (
    CENTRAL_REAR_PACKAGE_KEEP_OUT_XYZ_MM,
    DIGITAL_ONLY,
    DONOR_OCCIPITAL_BLOB_SHA,
    PAD_BACKER_XYZ_MM,
    PAD_CONTACT_FACE_Z_MM,
    ROOT_CAPTURE_BORE_RADIUS_MM,
    SOURCE_MAIN_SHA,
    WORLD_FRAME_ID,
    OccipitalStabilizerError,
    build_occipital_stabilizer,
    export_occipital_stabilizer,
)


@pytest.fixture(scope="module")
def stabilizer():
    return build_occipital_stabilizer()


def _bounds(solid: cq.Workplane) -> tuple[float, float, float, float, float, float]:
    bb = solid.val().BoundingBox()
    return tuple(float(value) for value in (bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax))


def _intersection_mm3(first: cq.Workplane, second: cq.Workplane) -> float:
    return float(first.val().intersect(second.val()).Volume())


def _datum_map(stabilizer) -> dict[str, tuple[float, float, float]]:
    return {datum.datum_id: datum.center_xyz_mm for datum in stabilizer.datums}


def test_occipital_source_graph_is_exact_current_main_and_pins_unchanged_cell3_donor(stabilizer) -> None:
    manifest = stabilizer.manifest()
    assert SOURCE_MAIN_SHA == "afe29ff78419b6625dca5594974b6351f6f80e1b"
    assert manifest["source_main_sha"] == SOURCE_MAIN_SHA
    assert manifest["coordinate_frame_id"] == WORLD_FRAME_ID
    assert manifest["donor"]["pr"] == 92
    assert manifest["donor"]["occipital_blob_sha"] == DONOR_OCCIPITAL_BLOB_SHA
    assert len(manifest["source_graph_sha256"]) == 64
    assert manifest["source_git_blobs"]["config/masck_one_authority.yaml"] == "2608dda483b995539de422290371c219668a1527"


def test_source_graph_fails_closed_when_a_direct_released_blob_moves(monkeypatch) -> None:
    original = occipital_module.SOURCE_GIT_BLOB_IDENTITIES
    path, digest = original[0]
    assert len(digest) == 40
    monkeypatch.setattr(
        occipital_module,
        "SOURCE_GIT_BLOB_IDENTITIES",
        ((path, "0" * 40), *original[1:]),
    )
    with pytest.raises(OccipitalStabilizerError, match="occipital source moved"):
        build_occipital_stabilizer()


def test_bilateral_yokes_preserve_current_frame_root_datums_and_positive_bores(stabilizer) -> None:
    datums = _datum_map(stabilizer)
    assert datums["OCCIPITAL_ROOT_LEFT"] == (-72.0, 10.0, -31.0)
    assert datums["OCCIPITAL_ROOT_RIGHT"] == (72.0, 10.0, -31.0)
    assert datums["OCCIPITAL_CONTACT_BACKER_LEFT"] == (-52.0, -5.0, -49.5)
    assert datums["OCCIPITAL_CONTACT_BACKER_RIGHT"] == (52.0, -5.0, -49.5)

    root = stabilizer.manifest()["root_capture_interface"]
    assert root["bore_axis"] == "Y"
    assert root["bore_radius_mm"] == ROOT_CAPTURE_BORE_RADIUS_MM == 1.6
    assert root["positive_capture_bore_realized"] is True
    assert root["frame_side_pin_or_clevis_realized"] is False
    assert root["friction_only_attachment_allowed"] is False
    assert root["overlap_as_attachment_allowed"] is False
    assert root["closure_status"].startswith("BLOCKED_PENDING_REALIZED_FRAME_SIDE")

    for yoke, bore in zip((stabilizer.left.solid, stabilizer.right.solid), stabilizer.root_capture_bores, strict=True):
        assert yoke.val().isValid()
        assert len(yoke.val().Solids()) == 1
        assert _intersection_mm3(yoke, bore) == pytest.approx(0.0, abs=1e-8)


def test_yoke_contact_backers_and_compact_posterior_packaging_match_donor_geometry(stabilizer) -> None:
    left = _bounds(stabilizer.left.solid)
    right = _bounds(stabilizer.right.solid)
    central = _bounds(stabilizer.central_rear_package_keepout)
    crown = _bounds(stabilizer.crown_support_corridor)

    assert PAD_BACKER_XYZ_MM == (16.0, 30.0, 3.0)
    assert PAD_CONTACT_FACE_Z_MM == -49.5
    assert CENTRAL_REAR_PACKAGE_KEEP_OUT_XYZ_MM == (68.0, 104.0, 24.0)
    assert central == pytest.approx((-34.0, 34.0, -52.0, 52.0, -48.0, -24.0), abs=2e-6)
    assert central[0] - left[1] >= 8.0
    assert right[0] - central[1] >= 8.0
    assert max(left[3], right[3]) < crown[2]
    assert left[5] < 0.0 and right[5] < 0.0
    assert _intersection_mm3(stabilizer.left.solid, stabilizer.central_rear_package_keepout) == 0.0
    assert _intersection_mm3(stabilizer.right.solid, stabilizer.central_rear_package_keepout) == 0.0
    assert _intersection_mm3(stabilizer.left.solid, stabilizer.crown_support_corridor) == 0.0
    assert _intersection_mm3(stabilizer.right.solid, stabilizer.crown_support_corridor) == 0.0


def test_yokes_clear_current_released_packages_protected_regions_and_waste_service_bounds(stabilizer) -> None:
    checks = stabilizer.manifest()["collision_checks"]
    assert checks
    assert all(check["passes"] for check in checks)
    obstacle_ids = {check["obstacle_id"] for check in checks}
    assert "RIGID_SHELL" in obstacle_ids
    assert "BATTERY_REFERENCE_ENVELOPE" in obstacle_ids
    assert any(obstacle.endswith("_SERVICE_AABB") for obstacle in obstacle_ids)
    assert any("PROTECTED-EYE" in obstacle for obstacle in obstacle_ids)
    assert any("PROTECTED-NOSTRIL" in obstacle for obstacle in obstacle_ids)
    assert any("PROTECTED-MOUTH" in obstacle for obstacle in obstacle_ids)


def test_current_main_model_identity_fails_closed_on_geometry_translation() -> None:
    model = build_model()
    modified_shell = Component(
        model.shell.name,
        model.shell.solid.translate((0.5, 0.0, 0.0)),
        model.shell.status,
        model.shell.notes,
    )
    modified = replace(model, shell=modified_shell)
    with pytest.raises(OccipitalStabilizerError, match="does not match current-main canonical package geometry"):
        build_occipital_stabilizer(authority=model.authority, model=modified)


def test_nonfinite_geometry_seed_is_rejected(monkeypatch) -> None:
    monkeypatch.setattr(occipital_module, "ROOT_Z_MM", math.inf)
    with pytest.raises(OccipitalStabilizerError, match="must be finite"):
        build_occipital_stabilizer()


def test_reference_geometry_never_enters_bilateral_material_review_step(tmp_path, stabilizer) -> None:
    paths = export_occipital_stabilizer(tmp_path, stabilizer)
    expected = {
        "occipital_stabilizer_left_yoke.step",
        "occipital_stabilizer_right_yoke.step",
        "occipital_stabilizer_bilateral_material_review.step",
        "occipital_central_rear_package_keepout_reference.step",
        "occipital_crown_support_corridor_reference.step",
        "occipital_stabilizer_manifest.json",
    }
    assert {path.name for path in paths} == expected

    bilateral = cq.importers.importStep(str(tmp_path / "occipital_stabilizer_bilateral_material_review.step")).val()
    assert bilateral.isValid()
    assert len(bilateral.Solids()) == 2
    expected_volume = float(stabilizer.left.solid.val().Volume()) + float(stabilizer.right.solid.val().Volume())
    assert float(bilateral.Volume()) == pytest.approx(expected_volume, rel=0.0, abs=1e-5)

    central_ref = cq.importers.importStep(str(tmp_path / "occipital_central_rear_package_keepout_reference.step")).val()
    crown_ref = cq.importers.importStep(str(tmp_path / "occipital_crown_support_corridor_reference.step")).val()
    assert float(bilateral.intersect(central_ref).Volume()) == pytest.approx(0.0, abs=1e-8)
    assert float(bilateral.intersect(crown_ref).Volume()) == pytest.approx(0.0, abs=1e-8)

    payload = json.loads((tmp_path / "occipital_stabilizer_manifest.json").read_text(encoding="utf-8"))
    assert payload["development_assembly_material_eligible"] is False
    assert payload["central_rear_package_keepout"]["geometry_role"].startswith("REFERENCE_ONLY")
    assert payload["crown_support_corridor"]["geometry_role"].startswith("REFERENCE_ONLY")


def test_physical_and_remaining_digital_gates_stay_open(stabilizer) -> None:
    manifest = stabilizer.manifest()
    contact = manifest["nominal_contact_geometry"]
    assert contact["contact_layer_material"] is None
    assert contact["preload_N"] is None
    assert contact["fit_range_mm"] is None
    assert manifest["physical_validation_eligible"] is False
    assert manifest["development_assembly_material_eligible"] is False
    assert manifest["evidence_status"] == DIGITAL_ONLY
    assert "CELL6_REALIZED_FRAME_SIDE_POSITIVE_RETENTION_ROOT_COUNTERPART" in manifest["unresolved_digital_dependencies"]
    assert "POST_RELEASE_WHOLE_HEAD_REMOVAL_SWEEP" in manifest["unresolved_digital_dependencies"]
    assert "EMERGENCY_RELEASE_FORCE_5_TO_12_N_AND_TIME_LE_2_S" in manifest["unresolved_physical_gates"]
    assert "ONE_HAND_WET_UNPOWERED_REMOVAL" in manifest["unresolved_physical_gates"]


def test_occipital_package_is_deterministic(stabilizer) -> None:
    second = build_occipital_stabilizer()
    assert stabilizer.package_sha256 == second.package_sha256
    assert stabilizer.manifest() == second.manifest()
