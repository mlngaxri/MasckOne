from __future__ import annotations

import json
import math

import cadquery as cq

from masck_one.right_quick_release_latch import (
    AUTHORITY_REVISION,
    BORE_RADIUS_MM,
    BORE_RADIUS_TOL_MM,
    CAPSULE_CENTER_X_MM,
    CAPSULE_XYZ_MM,
    CAVITY_CENTER_X_MM,
    CAVITY_END_TOL_MM,
    CAVITY_XYZ_MM,
    CHANNEL_SIZE_TOL_MM,
    DETENT_NECK_RADIAL_CLEARANCE_MM,
    DETENT_POSITION_TOL_MM,
    PIN_LENGTH_MM,
    PIN_LENGTH_TOL_MM,
    PIN_RADIUS_MM,
    PIN_RADIUS_TOL_MM,
    RELEASE_TRAVEL_MM,
    SOURCE_MAIN_SHA,
    SPOOL_LEFT_RADIUS_MM,
    SPOOL_NECK_RADIUS_MM,
    SPOOL_RADIUS_TOL_MM,
    TONGUE_CHANNEL_XYZ_MM,
    TONGUE_SIZE_TOL_MM,
    TONGUE_XYZ_MM,
    TRAVEL_TOL_MM,
    WORLD_FRAME_ID,
    build_right_quick_release_latch,
)
from masck_one.right_quick_release_latch_export import export_right_quick_release_latch


def test_right_latch_has_positive_capture_captive_stops_and_reset_semantics() -> None:
    latch = build_right_quick_release_latch()
    manifest = latch.manifest()

    assert manifest["source_main_sha"] == SOURCE_MAIN_SHA
    assert manifest["source_authority_revision"] == AUTHORITY_REVISION
    assert manifest["coordinate_frame_id"] == WORLD_FRAME_ID
    assert manifest["latched_state"]["positive_capture"] is True
    assert manifest["latched_state"]["flexure_cam_tooth_in_spool_neck"] is True
    assert manifest["latched_state"]["reset_required"] is False
    assert manifest["release_transition"]["cam_surface"] == "SLOPED_FLEXURE_TOOTH_UNDERSIDE"
    assert manifest["release_transition"]["rigid_pull_blocked_by_positive_geometry"] is True
    assert manifest["release_transition"]["digital_escape_lift_is_material_model"] is False
    assert manifest["release_transition"]["power_dependency"] is None
    assert manifest["release_transition"]["firmware_dependency"] is None
    assert manifest["release_transition"]["app_dependency"] is None
    assert manifest["released_state"]["tongue_capture"] is False
    assert manifest["released_state"]["slider_captive"] is True
    assert manifest["released_state"]["reset_required"] is True
    assert manifest["released_state"]["state_id"] == "RELEASED_RESET_REQUIRED"
    assert math.isclose(
        manifest["latched_state"]["spool_inboard_face_x_mm"],
        manifest["latched_state"]["inboard_hard_stop_x_mm"],
        rel_tol=0.0,
        abs_tol=1e-12,
    )
    assert math.isclose(
        manifest["released_state"]["spool_outboard_face_x_mm"],
        manifest["released_state"]["outboard_hard_stop_x_mm"],
        rel_tol=0.0,
        abs_tol=1e-12,
    )


def test_every_exported_latch_part_is_one_connected_solid() -> None:
    latch = build_right_quick_release_latch()
    parts = (
        latch.socket,
        latch.tongue,
        latch.guide_capsule,
        latch.flexure_detent,
        latch.slider_and_grip,
        latch.continuous_withdrawal_sweep,
    )
    for part in parts:
        assert part.solid.val().isValid()
        assert len(part.solid.val().Solids()) == 1
        assert part.manifest()["solid_count"] == 1


def test_right_latch_tolerance_stacks_are_positive_source_bound_and_dimensionally_exact() -> None:
    latch = build_right_quick_release_latch()
    values = dict(latch.tolerance_values_mm)
    stacks = {stack.stack_id: stack for stack in latch.tolerance_stacks}

    assert set(values) == {
        "LATCH_TONGUE_CHANNEL_CLEARANCE",
        "LATCH_PIN_BORE_RADIAL_CLEARANCE",
        "LATCH_RELEASED_TONGUE_CLEARANCE",
        "LATCH_CAPTIVE_RADIAL_MARGIN",
        "LATCH_HARD_STOP_WALL_MARGIN",
        "LATCH_DETENT_ENGAGEMENT_MARGIN",
    }
    assert all(value > 0.0 for value in values.values())
    for stack in latch.tolerance_stacks:
        assert stack.source_geometry_sha256 == latch.geometry_sha256
        assert stack.coordinate_frame_id == WORLD_FRAME_ID

    expected_side = min(
        (
            (TONGUE_CHANNEL_XYZ_MM[axis] - CHANNEL_SIZE_TOL_MM)
            - (TONGUE_XYZ_MM[axis] + TONGUE_SIZE_TOL_MM)
        )
        / 2.0
        for axis in (0, 1)
    )
    expected_pin_bore = (
        BORE_RADIUS_MM - BORE_RADIUS_TOL_MM
    ) - (PIN_RADIUS_MM + PIN_RADIUS_TOL_MM)
    expected_released = (
        RELEASE_TRAVEL_MM
        - TRAVEL_TOL_MM
        - (PIN_LENGTH_MM + PIN_LENGTH_TOL_MM) / 2.0
        - (TONGUE_XYZ_MM[0] + TONGUE_SIZE_TOL_MM) / 2.0
    )
    expected_captive = (
        SPOOL_LEFT_RADIUS_MM - SPOOL_RADIUS_TOL_MM
    ) - (BORE_RADIUS_MM + BORE_RADIUS_TOL_MM)
    capsule_xmin = CAPSULE_CENTER_X_MM - CAPSULE_XYZ_MM[0] / 2.0
    capsule_xmax = CAPSULE_CENTER_X_MM + CAPSULE_XYZ_MM[0] / 2.0
    cavity_xmin = CAVITY_CENTER_X_MM - CAVITY_XYZ_MM[0] / 2.0
    cavity_xmax = CAVITY_CENTER_X_MM + CAVITY_XYZ_MM[0] / 2.0
    expected_hard_stop = min(
        cavity_xmin - CAVITY_END_TOL_MM - capsule_xmin,
        capsule_xmax - (cavity_xmax + CAVITY_END_TOL_MM),
    )
    expected_detent = (
        SPOOL_LEFT_RADIUS_MM
        - SPOOL_RADIUS_TOL_MM
        - (SPOOL_NECK_RADIUS_MM + SPOOL_RADIUS_TOL_MM)
        - (DETENT_NECK_RADIAL_CLEARANCE_MM + DETENT_POSITION_TOL_MM)
    )

    expected = {
        "LATCH_TONGUE_CHANNEL_CLEARANCE": expected_side,
        "LATCH_PIN_BORE_RADIAL_CLEARANCE": expected_pin_bore,
        "LATCH_RELEASED_TONGUE_CLEARANCE": expected_released,
        "LATCH_CAPTIVE_RADIAL_MARGIN": expected_captive,
        "LATCH_HARD_STOP_WALL_MARGIN": expected_hard_stop,
        "LATCH_DETENT_ENGAGEMENT_MARGIN": expected_detent,
    }
    for stack_id, independent_value in expected.items():
        assert math.isclose(
            values[stack_id], independent_value, rel_tol=0.0, abs_tol=1e-12
        )

    assert [cid for cid, _, _ in stacks["LATCH_TONGUE_CHANNEL_CLEARANCE"].contributions] == [
        "CHANNEL_HALF_SIZE",
        "TONGUE_HALF_SIZE",
    ]
    assert [cid for cid, _, _ in stacks["LATCH_RELEASED_TONGUE_CLEARANCE"].contributions] == [
        "TRAVEL",
        "PIN_HALF_LENGTH",
        "TONGUE_HALF_WIDTH",
    ]
    assert [cid for cid, _, _ in stacks["LATCH_DETENT_ENGAGEMENT_MARGIN"].contributions] == [
        "SPOOL_FLANGE_RADIUS",
        "SPOOL_NECK_RADIUS",
        "TOOTH_RADIAL_CLEARANCE",
    ]


def test_continuous_withdrawal_sweep_bounds_every_translation_state() -> None:
    latch = build_right_quick_release_latch()
    slider_bb = latch.slider_and_grip.solid.val().BoundingBox()
    sweep_bb = latch.continuous_withdrawal_sweep.solid.val().BoundingBox()

    assert math.isclose(float(sweep_bb.xmin), float(slider_bb.xmin), rel_tol=0.0, abs_tol=1e-9)
    assert math.isclose(float(sweep_bb.xmax), float(slider_bb.xmax) + RELEASE_TRAVEL_MM, rel_tol=0.0, abs_tol=1e-9)
    assert math.isclose(float(sweep_bb.ymin), float(slider_bb.ymin), rel_tol=0.0, abs_tol=1e-9)
    assert math.isclose(float(sweep_bb.ymax), float(slider_bb.ymax), rel_tol=0.0, abs_tol=1e-9)
    assert math.isclose(float(sweep_bb.zmin), float(slider_bb.zmin), rel_tol=0.0, abs_tol=1e-9)
    assert math.isclose(float(sweep_bb.zmax), float(slider_bb.zmax), rel_tol=0.0, abs_tol=1e-9)
    assert latch.all_required_clear is True
    assert all(check.intersection_volume_mm3 == 0.0 for check in latch.collision_checks)


def test_right_latch_preserves_four_zone_and_physical_evidence_firewall() -> None:
    manifest = build_right_quick_release_latch().manifest()
    assert manifest["actuation_compatibility"] == {
        "required_independent_zone_count": 4,
        "actuator_geometry_changed": False,
    }
    assert manifest["tolerance_basis"] == {
        "tongue_channel": "LIMITING_HALF_DIMENSION_BOUNDARY_CLEARANCE",
        "pin_bore": "RADIUS_TO_RADIUS_CLEARANCE",
        "released_tongue": "TRAVEL_MINUS_PIN_HALF_LENGTH_MINUS_TONGUE_HALF_WIDTH",
        "hard_stop": "LIMITING_CAVITY_END_TO_CAPSULE_END_CLEARANCE",
        "detent": "FLANGE_RADIUS_MINUS_NECK_RADIUS_MINUS_TOOTH_CLEARANCE",
    }
    physical = manifest["physical_gates"]
    assert physical["release_force_target_N"] == [5.0, 12.0]
    assert physical["release_force_measured_N"] is None
    assert physical["release_time_requirement_s"] == 2.0
    assert physical["release_time_measured_s"] is None
    assert physical["wet_one_hand_validation"] == "OPEN_PHYSICAL_GATE"
    assert physical["cam_contact_wear_and_jam_margin"] == "OPEN_PHYSICAL_GATE"
    assert manifest["physical_validation_eligible"] is False


def test_right_latch_manifest_is_deterministic_and_cad_export_builds(tmp_path) -> None:
    first = build_right_quick_release_latch()
    second = build_right_quick_release_latch()
    assert first.package_sha256 == second.package_sha256
    assert first.manifest() == second.manifest()

    paths = export_right_quick_release_latch(tmp_path, first)
    assert len(paths) == 8
    assert all(path.is_file() and path.stat().st_size > 0 for path in paths)

    released_path = tmp_path / "right_latch_captive_slider_released_state.step"
    assert released_path in paths
    released = cq.importers.importStep(str(released_path)).val()
    assert released.isValid()
    assert len(released.Solids()) == 1
    released_bb = released.BoundingBox()
    latched_bb = first.slider_and_grip.solid.val().BoundingBox()
    assert math.isclose(float(released_bb.xmin), float(latched_bb.xmin) + RELEASE_TRAVEL_MM, rel_tol=0.0, abs_tol=1e-9)
    assert math.isclose(float(released_bb.xmax), float(latched_bb.xmax) + RELEASE_TRAVEL_MM, rel_tol=0.0, abs_tol=1e-9)
    assert math.isclose(float(released_bb.ymin), float(latched_bb.ymin), rel_tol=0.0, abs_tol=1e-9)
    assert math.isclose(float(released_bb.ymax), float(latched_bb.ymax), rel_tol=0.0, abs_tol=1e-9)
    assert math.isclose(float(released_bb.zmin), float(latched_bb.zmin), rel_tol=0.0, abs_tol=1e-9)
    assert math.isclose(float(released_bb.zmax), float(latched_bb.zmax), rel_tol=0.0, abs_tol=1e-9)

    manifest_path = tmp_path / "right_quick_release_latch_manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert payload["released_state"]["state_id"] == "RELEASED_RESET_REQUIRED"
    assert payload["released_state"]["slider_offset_mm"] == RELEASE_TRAVEL_MM
    assert payload["package_sha256"] == first.package_sha256
