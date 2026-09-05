from __future__ import annotations

from dataclasses import replace
import json

import cadquery as cq
import pytest

from masck_one.model import Component, build_model
from masck_one.occipital_stabilizer import (
    AUTHORITY_REVISION,
    CENTRAL_REAR_PACKAGE_KEEP_OUT_XYZ_MM,
    DIGITAL_ONLY,
    PAD_CONTACT_FACE_Z_MM,
    ROOT_CAPTURE_BORE_RADIUS_MM,
    OccipitalStabilizerError,
    build_occipital_stabilizer,
    export_occipital_stabilizer,
)


def _bounds(solid: cq.Workplane) -> tuple[float, float, float, float, float, float]:
    bb = solid.val().BoundingBox()
    return tuple(float(value) for value in (bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax))


def _intersection_mm3(first: cq.Workplane, second: cq.Workplane) -> float:
    return float(first.val().intersect(second.val()).Volume())


def test_occipital_geometry_is_distinct_from_crown_and_facial_reaction() -> None:
    stabilizer = build_occipital_stabilizer()
    manifest = stabilizer.manifest()

    separation = manifest["functional_separation"]
    assert separation["functions_conflated_into_single_halo_ring"] is False
    assert separation["occipital_stabilization"] == "PAIRED_LATERAL_FORK_YOKES_REALIZED"
    assert separation["crown_support"] == "SEPARATE_SUPERIOR_CORRIDOR_RESERVED_NO_CROWN_MEMBER_REALIZED_HERE"
    assert separation["facial_reaction"] == "FRONT_STRUCTURAL_REACTION_LOOP_UNCHANGED_BY_THIS_INCREMENT"

    assert len(stabilizer.left.solid.val().Solids()) == 1
    assert len(stabilizer.right.solid.val().Solids()) == 1
    assert stabilizer.left.solid.val().isValid()
    assert stabilizer.right.solid.val().isValid()
    assert _intersection_mm3(stabilizer.left.solid, stabilizer.right.solid) == 0.0
    assert manifest["four_zone_actuation_preserved"] is True


def test_lateral_yokes_leave_central_rear_packaging_window_and_crown_corridor_clear() -> None:
    stabilizer = build_occipital_stabilizer()
    left = _bounds(stabilizer.left.solid)
    right = _bounds(stabilizer.right.solid)
    central = _bounds(stabilizer.central_rear_package_keepout)
    crown = _bounds(stabilizer.crown_support_corridor)

    assert central == pytest.approx((-34.0, 34.0, -52.0, 52.0, -48.0, -24.0), abs=2e-6)
    assert CENTRAL_REAR_PACKAGE_KEEP_OUT_XYZ_MM == (68.0, 104.0, 24.0)
    assert central[0] - left[1] >= 8.0
    assert right[0] - central[1] >= 8.0
    assert _intersection_mm3(stabilizer.left.solid, stabilizer.central_rear_package_keepout) == 0.0
    assert _intersection_mm3(stabilizer.right.solid, stabilizer.central_rear_package_keepout) == 0.0
    assert _intersection_mm3(stabilizer.left.solid, stabilizer.crown_support_corridor) == 0.0
    assert _intersection_mm3(stabilizer.right.solid, stabilizer.crown_support_corridor) == 0.0
    assert max(left[3], right[3]) < crown[2]


def test_yokes_clear_released_packages_protected_regions_and_cell4_waste_route_bounds() -> None:
    stabilizer = build_occipital_stabilizer()
    manifest = stabilizer.manifest()
    assert manifest["source_authority_revision"] == AUTHORITY_REVISION

    checks = manifest["collision_checks"]
    assert checks
    assert all(check["passes"] for check in checks)
    obstacle_ids = {check["obstacle_id"] for check in checks}
    assert "RIGID_SHELL" in obstacle_ids
    assert "BATTERY_REFERENCE_ENVELOPE" in obstacle_ids
    assert any(obstacle.endswith("_SERVICE_AABB") for obstacle in obstacle_ids)
    assert any("PROTECTED-EYE" in obstacle for obstacle in obstacle_ids)


def test_positive_capture_root_bores_exist_without_friction_attachment_claim() -> None:
    stabilizer = build_occipital_stabilizer()
    manifest = stabilizer.manifest()
    root = manifest["root_capture_interface"]
    assert root["positive_capture_bore_realized"] is True
    assert root["bore_radius_mm"] == ROOT_CAPTURE_BORE_RADIUS_MM
    assert root["frame_side_pin_or_clevis_realized"] is False
    assert root["friction_only_attachment_allowed"] is False
    for yoke, bore in zip((stabilizer.left.solid, stabilizer.right.solid), stabilizer.root_capture_bores, strict=True):
        assert _intersection_mm3(yoke, bore) == 0.0


def test_human_fit_uncertainty_and_physical_gates_remain_open() -> None:
    manifest = build_occipital_stabilizer().manifest()
    contact = manifest["nominal_contact_geometry"]
    assert contact["backer_face_z_mm"] == PAD_CONTACT_FACE_Z_MM
    assert contact["contact_layer_material"] is None
    assert contact["preload_N"] is None
    assert contact["fit_range_mm"] is None
    assert "NO_REPRESENTATIVE_3D_HEADFORM" in contact["headform_status"]
    assert manifest["physical_validation_eligible"] is False
    assert manifest["evidence_status"] == DIGITAL_ONLY
    assert "EMERGENCY_RELEASE_FORCE_5_TO_12_N_AND_TIME_LE_2_S" in manifest["unresolved_physical_gates"]


def test_occipital_source_model_binding_fails_closed_on_modified_current_main_geometry() -> None:
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


def test_occipital_package_is_deterministic_and_step_roundtrips(tmp_path) -> None:
    first = build_occipital_stabilizer()
    second = build_occipital_stabilizer()
    assert first.package_sha256 == second.package_sha256
    assert first.manifest() == second.manifest()

    paths = export_occipital_stabilizer(tmp_path, first)
    expected = {
        "occipital_stabilizer_left_yoke.step",
        "occipital_stabilizer_right_yoke.step",
        "occipital_central_rear_package_keepout_reference.step",
        "occipital_crown_support_corridor_reference.step",
        "occipital_stabilizer_manifest.json",
    }
    assert {path.name for path in paths} == expected

    for path in paths:
        assert path.is_file() and path.stat().st_size > 0
        if path.suffix.lower() not in {".step", ".stp"}:
            continue
        shape = cq.importers.importStep(str(path)).val()
        assert shape.isValid()
        assert len(shape.Solids()) == 1
        assert float(shape.Volume()) > 0.0

    payload = json.loads((tmp_path / "occipital_stabilizer_manifest.json").read_text(encoding="utf-8"))
    assert payload["package_sha256"] == first.package_sha256
    assert payload["source_model_sha256"] == first.source_model_sha256
    assert payload["source_waste_release_sha256"] == first.source_waste_release_sha256
