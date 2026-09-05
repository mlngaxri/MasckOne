from __future__ import annotations

from dataclasses import replace
import json
import math

import cadquery as cq
import pytest

from masck_one.model import build_model
from masck_one.right_quick_release_latch import RELEASE_TRAVEL_MM, build_right_quick_release_latch
from masck_one.right_quick_release_reset import (
    RESET_DETENT_CLEAR_OFFSET_MM,
    RESET_FLEXURE_FREE_END_LIFT_MM,
    RightQuickReleaseResetError,
    build_right_quick_release_reset_mechanics,
)
from masck_one.right_quick_release_reset_export import export_right_quick_release_reset


def _intersection_mm3(first: cq.Workplane, second: cq.Workplane) -> float:
    return float(first.val().intersect(second.val()).Volume())


def test_reset_state_machine_is_explicit_reversible_and_reseats_positive_capture() -> None:
    reset = build_right_quick_release_reset_mechanics()
    manifest = reset.manifest()
    states = {state["state_id"]: state for state in manifest["state_machine"]}

    assert states["LATCHED"]["reset_required"] is False
    assert states["LATCHED"]["detent_reseated_in_neck"] is True
    assert states["LATCHED"]["pin_positive_capture"] is True
    assert states["RELEASING_DETENT_LIFTED"]["flexure_free_end_lift_mm"] == RESET_FLEXURE_FREE_END_LIFT_MM
    assert states["RELEASE_TRAVEL_LOW_OFFSET"]["slider_offset_mm"] == [0.0, RESET_DETENT_CLEAR_OFFSET_MM]
    assert states["RELEASE_TRAVEL_HIGH_OFFSET"]["slider_offset_mm"] == [RESET_DETENT_CLEAR_OFFSET_MM, RELEASE_TRAVEL_MM]
    assert states["RELEASED_RESET_REQUIRED"]["slider_offset_mm"] == RELEASE_TRAVEL_MM
    assert states["RELEASED_RESET_REQUIRED"]["reset_required"] is True
    assert states["RESET_TRAVEL_HIGH_OFFSET"]["reset_direction_xyz"] == [-1.0, 0.0, 0.0]
    assert states["RESET_TRAVEL_LOW_OFFSET"]["reset_direction_xyz"] == [-1.0, 0.0, 0.0]
    assert states["RESET_RESEATED_LATCHED"]["positive_capture_restored"] is True
    assert states["RESET_RESEATED_LATCHED"]["detent_reseated_in_neck"] is True
    assert states["RESET_RESEATED_LATCHED"]["reset_required"] is False

    proof = manifest["kinematic_proof"]
    assert proof["release_and_reset_use_same_reversible_geometric_path"] is True
    assert proof["passive_cam_force_mapping_validated"] is False
    assert manifest["physical_validation_eligible"] is False


def test_reset_flexure_has_free_leaf_fixed_root_and_continuous_clearance_proof() -> None:
    reset = build_right_quick_release_reset_mechanics()
    latch = reset.latch

    for part in (
        reset.nominal_flexure,
        reset.lifted_flexure,
        reset.deformation_envelope,
        reset.low_offset_translation_sweep,
        reset.high_offset_translation_sweep,
    ):
        assert part.solid.val().isValid()
        assert len(part.solid.val().Solids()) == 1
        assert float(part.solid.val().Volume()) > 0.0

    # The release-facing nominal flexure no longer embeds its moving beam in the guide.
    # Only the fixed root is allowed to overlap the guide as positive attachment.
    nominal_manifest = reset.nominal_flexure.manifest()
    assert nominal_manifest["bounds_mm"][5] > latch.flexure_detent.manifest()["bounds_mm"][5]

    assert _intersection_mm3(reset.deformation_envelope.solid, latch.guide_capsule.solid) == 0.0
    assert _intersection_mm3(reset.low_offset_translation_sweep.solid, reset.lifted_flexure.solid) == 0.0
    assert _intersection_mm3(reset.high_offset_translation_sweep.solid, reset.nominal_flexure.solid) == 0.0
    assert _intersection_mm3(reset.low_offset_translation_sweep.solid, latch.guide_capsule.solid) == 0.0
    assert _intersection_mm3(reset.high_offset_translation_sweep.solid, latch.guide_capsule.solid) == 0.0
    assert _intersection_mm3(reset.low_offset_translation_sweep.solid, latch.socket.solid) == 0.0
    assert _intersection_mm3(reset.high_offset_translation_sweep.solid, latch.socket.solid) == 0.0
    assert _intersection_mm3(reset.low_offset_translation_sweep.solid, latch.tongue.solid) == 0.0
    assert _intersection_mm3(reset.high_offset_translation_sweep.solid, latch.tongue.solid) == 0.0


def test_reset_source_binding_rejects_modified_shell_or_actuator_model() -> None:
    model = build_model()
    latch = build_right_quick_release_latch(model.authority, model)
    valid = build_right_quick_release_reset_mechanics(latch=latch, authority=model.authority, model=model)
    assert valid.manifest()["source_model_matches_current_main"] is True

    moved_shell = replace(
        model.shell,
        solid=model.shell.solid.translate((0.5, 0.0, 0.0)),
    )
    mutated = replace(model, shell=moved_shell)
    with pytest.raises(RightQuickReleaseResetError, match="does not match current-main canonical geometry"):
        build_right_quick_release_reset_mechanics(authority=model.authority, model=mutated)


def test_reset_package_and_release_artifacts_are_deterministic_and_roundtrip(tmp_path) -> None:
    first = build_right_quick_release_reset_mechanics()
    second = build_right_quick_release_reset_mechanics()
    assert first.package_sha256 == second.package_sha256
    assert first.manifest() == second.manifest()

    paths = export_right_quick_release_reset(tmp_path, first.latch, first)
    expected = {
        "right_latch_frame_socket.step",
        "right_latch_halo_tongue.step",
        "right_latch_captive_guide.step",
        "right_latch_flexure_cam_detent.step",
        "right_latch_captive_slider.step",
        "right_latch_continuous_withdrawal_sweep.step",
        "right_latch_captive_slider_released_state.step",
        "right_latch_reset_flexure_lifted.step",
        "right_latch_reset_deformation_envelope.step",
        "right_latch_reset_low_offset_translation_sweep.step",
        "right_latch_reset_high_offset_translation_sweep.step",
        "right_quick_release_latch_manifest.json",
        "right_quick_release_reset_manifest.json",
    }
    assert {path.name for path in paths} == expected

    for path in paths:
        assert path.is_file() and path.stat().st_size > 0
        if path.suffix.lower() not in {".step", ".stp"}:
            continue
        shape = cq.importers.importStep(str(path)).val()
        assert shape.isValid()
        assert len(shape.Solids()) == 1

    exported_flexure = cq.importers.importStep(str(tmp_path / "right_latch_flexure_cam_detent.step"))
    expected_bb = first.nominal_flexure.solid.val().BoundingBox()
    actual_bb = exported_flexure.val().BoundingBox()
    for actual, expected_value in (
        (actual_bb.xmin, expected_bb.xmin),
        (actual_bb.xmax, expected_bb.xmax),
        (actual_bb.ymin, expected_bb.ymin),
        (actual_bb.ymax, expected_bb.ymax),
        (actual_bb.zmin, expected_bb.zmin),
        (actual_bb.zmax, expected_bb.zmax),
    ):
        assert math.isclose(float(actual), float(expected_value), rel_tol=0.0, abs_tol=1e-8)

    payload = json.loads((tmp_path / "right_quick_release_reset_manifest.json").read_text(encoding="utf-8"))
    assert payload["package_sha256"] == first.package_sha256
    assert payload["source_latch_package_sha256"] == first.latch.package_sha256
