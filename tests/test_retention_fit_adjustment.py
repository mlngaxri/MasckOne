from __future__ import annotations

import json
import math

import cadquery as cq
import pytest

from masck_one.retention_fit_adjustment import (
    HARD_STOP_TRAVEL_MM,
    INDEX_OFFSETS_MM,
    INDEX_PIN_BORE_RADIUS_MM,
    INDEX_PIN_RADIUS_MM,
    OVERTRAVEL_PROBE_MM,
    SOURCE_OCCIPITAL_GIT_BLOB_SHA,
    STOP_CLIP_INNER_RADIUS_MM,
    STOP_CLIP_OUTER_RADIUS_MM,
    STOP_PIN_BORE_RADIUS_MM,
    STOP_PIN_GROOVE_RADIUS_MM,
    STOP_PIN_RADIUS_MM,
    RetentionFitAdjustmentError,
    _bbox,
    _intersection_mm3,
    _translated,
    build_retention_fit_adjustment,
    export_retention_fit_adjustment,
)


def _roundtrip(path):
    imported = cq.importers.importStep(str(path))
    shape = imported.val()
    assert shape.isValid()
    assert len(shape.Solids()) == 1
    assert float(shape.Volume()) > 0.0
    return imported


def test_three_indexed_states_are_bounded_geometry_not_universal_fit_claim():
    adjustment = build_retention_fit_adjustment()
    manifest = adjustment.manifest()

    assert manifest["adjustment_architecture"]["index_offsets_mm"] == [-2.0, 0.0, 2.0]
    assert manifest["adjustment_architecture"]["hard_stop_travel_mm"] == 2.0
    assert manifest["adjustment_architecture"]["sampled_waypoints_primary_proof"] is False
    assert manifest["fit_claim_boundary"]["anthropometric_head_range_mm"] is None
    assert manifest["fit_claim_boundary"]["universal_fit_claim"] is False
    assert manifest["fit_claim_boundary"]["comfort_claim"] is False
    assert manifest["physical_validation_eligible"] is False
    assert manifest["four_zone_actuation_preserved"] is True

    assert tuple(state.offset_mm for state in adjustment.left.states) == INDEX_OFFSETS_MM
    assert tuple(state.offset_mm for state in adjustment.right.states) == INDEX_OFFSETS_MM


def test_indexed_states_clear_guides_and_pins_while_nonindexed_state_rejects_lock():
    adjustment = build_retention_fit_adjustment()

    for side in (adjustment.left, adjustment.right):
        assert side.housing.val().isValid()
        assert len(side.housing.val().Solids()) == 1
        assert side.nominal_successor_yoke.val().isValid()
        assert len(side.nominal_successor_yoke.val().Solids()) == 1

        for state in side.states:
            assert _intersection_mm3(state.successor_yoke, side.housing) == 0.0
            assert _intersection_mm3(state.successor_yoke, side.stop_pin) == 0.0
            assert _intersection_mm3(state.successor_yoke, side.index_pin_engaged) == 0.0

        non_index = _translated(side.nominal_successor_yoke, side.side_sign * 1.0)
        assert _intersection_mm3(non_index, side.index_pin_engaged) > 0.0
        assert _intersection_mm3(non_index, side.stop_pin) == 0.0


def test_permanent_stop_pin_blocks_both_overtravel_directions():
    adjustment = build_retention_fit_adjustment()

    for side in (adjustment.left, adjustment.right):
        for signed_offset in (
            -HARD_STOP_TRAVEL_MM - OVERTRAVEL_PROBE_MM,
            HARD_STOP_TRAVEL_MM + OVERTRAVEL_PROBE_MM,
        ):
            probe = _translated(side.nominal_successor_yoke, side.side_sign * signed_offset)
            assert _intersection_mm3(probe, side.stop_pin) > 0.0
            assert _intersection_mm3(probe, side.housing) == 0.0


def test_stop_pin_has_positive_axial_retention_geometry_and_pin_clearances_are_explicit():
    adjustment = build_retention_fit_adjustment()

    assert STOP_PIN_GROOVE_RADIUS_MM < STOP_CLIP_INNER_RADIUS_MM < STOP_PIN_RADIUS_MM
    assert STOP_CLIP_OUTER_RADIUS_MM > STOP_PIN_BORE_RADIUS_MM
    assert INDEX_PIN_RADIUS_MM < INDEX_PIN_BORE_RADIUS_MM

    for side in (adjustment.left, adjustment.right):
        assert _intersection_mm3(side.stop_pin, side.stop_pin_clip) == 0.0
        assert _intersection_mm3(side.stop_pin_clip, side.housing) == 0.0


def test_complete_translation_envelopes_preserve_prompt08_package_margin_and_visual_restraint():
    adjustment = build_retention_fit_adjustment()
    left_bounds = _bbox(adjustment.left.complete_translation_envelope)
    right_bounds = _bbox(adjustment.right.complete_translation_envelope)
    left_housing = _bbox(adjustment.left.housing)
    right_housing = _bbox(adjustment.right.housing)

    # Prompt 08 central package keepout is X [-34, 34]; hard-stop motion must preserve 8 mm.
    assert math.isclose(-34.0 - left_bounds[1], 8.0, rel_tol=0.0, abs_tol=1e-9)
    assert math.isclose(right_bounds[0] - 34.0, 8.0, rel_tol=0.0, abs_tol=1e-9)

    # Fixed housings stay inside the released 172 mm lateral design envelope.
    assert left_housing[0] >= -86.0
    assert right_housing[1] <= 86.0

    # Complete moving bounds are conservative AABBs over the pure-X hard-stop interval.
    assert left_bounds == (-88.0, -42.0, -20.0, 15.0, -52.5, -28.0)
    assert right_bounds == (42.0, 88.0, -20.0, 15.0, -52.5, -28.0)


def test_service_logic_is_unworn_unpowered_and_requires_index_reseat():
    adjustment = build_retention_fit_adjustment()
    sequence = adjustment.service_sequence(2.0, worn=False, powered=False)

    assert [step["step"] for step in sequence] == [1, 2, 3, 4, 5]
    assert sequence[1]["stop_pin_remains_installed"] is True
    assert sequence[2]["hard_stop_travel_mm"] == HARD_STOP_TRAVEL_MM
    assert sequence[-1]["wear_eligible_only_after_full_reseat"] is True

    with pytest.raises(RetentionFitAdjustmentError, match="prohibited while worn"):
        adjustment.service_sequence(0.0, worn=True, powered=False)
    with pytest.raises(RetentionFitAdjustmentError, match="prohibited while powered"):
        adjustment.service_sequence(0.0, worn=False, powered=True)
    with pytest.raises(RetentionFitAdjustmentError, match="three indexed"):
        adjustment.service_sequence(1.0, worn=False, powered=False)


def test_index_pin_retracted_state_clears_moving_yoke_but_remains_in_guide_region():
    adjustment = build_retention_fit_adjustment()

    for side in (adjustment.left, adjustment.right):
        nominal = side.state_for_offset(0.0)
        assert _intersection_mm3(side.index_pin_retracted, nominal.successor_yoke) == 0.0
        pin_bounds = _bbox(side.index_pin_retracted)
        housing_bounds = _bbox(side.housing)
        # Retracted pin still overlaps the housing Y interval geometrically, so it remains guided.
        assert pin_bounds[2] < housing_bounds[3]
        assert pin_bounds[3] > housing_bounds[2]


def test_all_external_collision_checks_pass_and_released_cell4_waste_is_included():
    adjustment = build_retention_fit_adjustment()
    assert adjustment.collision_checks
    assert all(check.passes for check in adjustment.collision_checks)
    assert any("SERVICE_AABB" in check.obstacle_id for check in adjustment.collision_checks)
    assert any("RIGID_SHELL" in check.obstacle_id for check in adjustment.collision_checks)
    assert any("ACTUATOR" in check.obstacle_id for check in adjustment.collision_checks)


def test_manifest_and_package_digest_are_deterministic():
    first = build_retention_fit_adjustment()
    second = build_retention_fit_adjustment()

    assert first.package_sha256 == second.package_sha256
    assert json.dumps(first.manifest(), sort_keys=True, allow_nan=False) == json.dumps(
        second.manifest(), sort_keys=True, allow_nan=False
    )
    assert first.manifest()["source_occipital_git_blob_sha"] == SOURCE_OCCIPITAL_GIT_BLOB_SHA


def test_source_occipital_blob_tamper_fails_closed(monkeypatch):
    from masck_one import retention_fit_adjustment as module

    monkeypatch.setattr(module, "SOURCE_OCCIPITAL_GIT_BLOB_SHA", "0" * 40)
    with pytest.raises(RetentionFitAdjustmentError, match="requires explicit rebind"):
        module.build_retention_fit_adjustment()


def test_exported_key_solids_roundtrip_and_manifest_preserves_evidence_firewall(tmp_path):
    adjustment = build_retention_fit_adjustment()
    paths = export_retention_fit_adjustment(tmp_path, adjustment)
    names = {path.name for path in paths}

    required = {
        "retention_fit_left_housing.step",
        "retention_fit_right_housing.step",
        "retention_fit_left_yoke_tight.step",
        "retention_fit_left_yoke_nominal.step",
        "retention_fit_left_yoke_loose.step",
        "retention_fit_right_yoke_tight.step",
        "retention_fit_right_yoke_nominal.step",
        "retention_fit_right_yoke_loose.step",
        "retention_fit_left_complete_translation_envelope.step",
        "retention_fit_right_complete_translation_envelope.step",
        "retention_fit_adjustment_manifest.json",
    }
    assert required <= names

    for name in (
        "retention_fit_left_housing.step",
        "retention_fit_right_housing.step",
        "retention_fit_left_yoke_tight.step",
        "retention_fit_right_yoke_loose.step",
        "retention_fit_left_complete_translation_envelope.step",
        "retention_fit_right_complete_translation_envelope.step",
    ):
        imported = _roundtrip(tmp_path / name)
        assert _bbox(imported) == _bbox(
            adjustment.left.housing
            if name == "retention_fit_left_housing.step"
            else adjustment.right.housing
            if name == "retention_fit_right_housing.step"
            else adjustment.left.state_for_offset(-2.0).successor_yoke
            if name == "retention_fit_left_yoke_tight.step"
            else adjustment.right.state_for_offset(2.0).successor_yoke
            if name == "retention_fit_right_yoke_loose.step"
            else adjustment.left.complete_translation_envelope
            if name == "retention_fit_left_complete_translation_envelope.step"
            else adjustment.right.complete_translation_envelope
        )

    payload = json.loads((tmp_path / "retention_fit_adjustment_manifest.json").read_text())
    assert payload["physical_validation_eligible"] is False
    assert payload["fit_claim_boundary"]["universal_fit_claim"] is False
    assert payload["service_logic"]["worn_adjustment_allowed"] is False
    assert payload["service_logic"]["powered_adjustment_allowed"] is False
