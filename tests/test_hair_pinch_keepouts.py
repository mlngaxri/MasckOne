from __future__ import annotations

import json
from pathlib import Path

import cadquery as cq
import pytest

import masck_one.hair_pinch_keepouts as hp
from masck_one.hair_pinch_keepouts import (
    SOURCE_RETENTION_FIT_GIT_BLOB_SHA,
    SOURCE_RIGHT_LATCH_HEAD_SHA,
    HairPinchKeepoutError,
    build_hair_pinch_keepouts,
    export_hair_pinch_keepouts,
)
from masck_one.model import build_model
from masck_one.retention_fit_adjustment import build_retention_fit_adjustment


@pytest.fixture(scope="module")
def model():
    return build_model()


@pytest.fixture(scope="module")
def adjustment(model):
    return build_retention_fit_adjustment(model.authority, model)


@pytest.fixture(scope="module")
def package(model, adjustment):
    return build_hair_pinch_keepouts(model.authority, model, adjustment)


def _intersection_mm3(first: cq.Workplane, second: cq.Workplane) -> float:
    return float(first.val().intersect(second.val()).Volume())


def _region(package, region_id: str):
    for region in package.hazard_regions:
        if region.region_id == region_id:
            return region
    for region in package.access_regions:
        if region.region_id == region_id:
            return region
    raise KeyError(region_id)


def test_hazard_inventory_is_explicit_bilateral_and_not_physical_guard(package):
    hazard_ids = {region.region_id for region in package.hazard_regions}
    access_ids = {region.region_id for region in package.access_regions}
    assert len(package.hazard_regions) == 13
    assert len(package.access_regions) == 3
    for side in ("LEFT", "RIGHT"):
        assert f"{side}_ADJUSTMENT_MEDIAL_GUIDE_NIP" in hazard_ids
        assert f"{side}_ADJUSTMENT_OUTBOARD_GUIDE_NIP" in hazard_ids
        assert f"{side}_INDEX_PIN_SERVICE_PATH" in hazard_ids
        assert f"{side}_STOP_PIN_CLIP_REGION" in hazard_ids
        assert f"{side}_ROOT_CAPTURE_FUTURE_PINCH_REGION" in hazard_ids
        assert f"{side}_SCALP_HAIR_APPROACH_CORRIDOR" in hazard_ids
        assert f"{side}_INDEX_PIN_SERVICE_ACCESS" in access_ids
    assert "RIGHT_LATCH_CANDIDATE_HAIR_PINCH_REGION" in hazard_ids
    assert "RIGHT_LATCH_EMERGENCY_PULL_ACCESS" in access_ids
    assert all(not region.physical_guard_realized for region in package.hazard_regions)


def test_nip_and_pin_keepouts_cover_the_actual_prompt09_interfaces(package, adjustment):
    for prefix, side in (("LEFT", adjustment.left), ("RIGHT", adjustment.right)):
        medial = _region(package, f"{prefix}_ADJUSTMENT_MEDIAL_GUIDE_NIP")
        outboard = _region(package, f"{prefix}_ADJUSTMENT_OUTBOARD_GUIDE_NIP")
        index = _region(package, f"{prefix}_INDEX_PIN_SERVICE_PATH")
        stop = _region(package, f"{prefix}_STOP_PIN_CLIP_REGION")
        root = _region(package, f"{prefix}_ROOT_CAPTURE_FUTURE_PINCH_REGION")
        hair = _region(package, f"{prefix}_SCALP_HAIR_APPROACH_CORRIDOR")

        assert _intersection_mm3(medial.solid, side.complete_translation_envelope) > 0.0
        assert _intersection_mm3(outboard.solid, side.complete_translation_envelope) > 0.0
        assert _intersection_mm3(index.solid, side.index_pin_retraction_envelope) > 0.0
        assert _intersection_mm3(stop.solid, side.stop_pin) > 0.0
        assert _intersection_mm3(root.solid, side.nominal_successor_yoke) > 0.0
        assert _intersection_mm3(hair.solid, side.nominal_successor_yoke) > 0.0


def test_reference_regions_clear_unrelated_released_geometry(package):
    assert package.clearance_checks
    assert all(check.passes for check in package.clearance_checks)
    assert all(check.intersection_volume_mm3 == 0.0 for check in package.clearance_checks)


def test_right_latch_overlay_is_candidate_only_and_keeps_emergency_pull_access(package):
    manifest = package.manifest()
    overlay = manifest["right_latch_candidate_overlay"]
    assert overlay["source_pr"] == 71
    assert overlay["source_head_sha"] == SOURCE_RIGHT_LATCH_HEAD_SHA
    assert overlay["authority_status"] == "NON_AUTHORITATIVE_UNMERGED_CANDIDATE_OVERLAY"
    assert overlay["runtime_source_imported"] is False
    assert overlay["promotion_requires_live_head_revalidation"] is True
    assert overlay["physical_release_performance_promoted"] is False

    latch_hazard = _region(package, "RIGHT_LATCH_CANDIDATE_HAIR_PINCH_REGION")
    pull_access = _region(package, "RIGHT_LATCH_EMERGENCY_PULL_ACCESS")
    assert latch_hazard.solid.val().isValid()
    assert pull_access.solid.val().isValid()
    assert any(check.check_id.startswith("CLEAR_RIGHT_LATCH_HAZARD_RIGHT_ADJUSTMENT") for check in package.clearance_checks)
    assert any(check.check_id.startswith("CLEAR_RIGHT_LATCH_PULL_ACCESS_RIGHT_ADJUSTMENT") for check in package.clearance_checks)


def test_root_capture_is_reserved_without_inventing_pivot_or_frame_counterpart(package):
    manifest = package.manifest()
    root = manifest["retention_root_semantics"]
    assert root["future_root_capture_hazard_reserved"] is True
    assert root["frame_side_pin_or_clevis_realized"] is False
    assert root["pivot_motion_claimed"] is False


def test_adjustment_service_safety_semantics_remain_unworn_unpowered(package, adjustment):
    manifest = package.manifest()
    semantics = manifest["adjustment_hazard_semantics"]
    assert semantics["continuous_yoke_translation_range_inherited_from_prompt09_mm"] == [-2.0, 2.0]
    assert semantics["adjustment_while_worn_allowed"] is False
    assert semantics["permanent_stop_pin_remains_installed_during_adjustment"] is True

    sequence = adjustment.service_sequence(0.0, worn=False, powered=False)
    assert sequence[0]["action"] == "CONFIRM_MASK_REMOVED_AND_UNPOWERED"
    with pytest.raises(Exception):
        adjustment.service_sequence(0.0, worn=True, powered=False)
    with pytest.raises(Exception):
        adjustment.service_sequence(0.0, worn=False, powered=True)


def test_no_hair_or_pinch_physics_are_fabricated(package):
    manifest = package.manifest()
    assert set(manifest["hair_model"].values()) == {None}
    assert set(manifest["pinch_model"].values()) == {None}
    assert manifest["physical_validation_eligible"] is False
    assert manifest["design_use"]["reference_solids_are_product_material"] is False
    assert manifest["design_use"]["reference_solids_are_physical_guards"] is False
    assert manifest["four_zone_actuation_preserved"] is True


def test_source_binding_fails_closed_when_prompt09_blob_identity_changes(monkeypatch, model, adjustment):
    assert len(SOURCE_RETENTION_FIT_GIT_BLOB_SHA) == 40
    monkeypatch.setattr(hp, "SOURCE_RETENTION_FIT_GIT_BLOB_SHA", "0" * 40)
    with pytest.raises(HairPinchKeepoutError, match="explicit rebind"):
        build_hair_pinch_keepouts(model.authority, model, adjustment)


def test_manifest_is_deterministic(package):
    first = package.manifest()
    second = package.manifest()
    assert first == second
    assert first["package_sha256"] == package.package_sha256
    payload = json.dumps(first, sort_keys=True, allow_nan=False)
    assert "NaN" not in payload
    assert "Infinity" not in payload


def test_export_round_trip_keeps_reference_geometry_as_standalone_artifacts(tmp_path: Path, package):
    outputs = export_hair_pinch_keepouts(tmp_path, package)
    names = {path.name for path in outputs}
    assert "hair_pinch_keepouts_manifest.json" in names
    assert "hair_pinch_right_latch_candidate_hair_pinch_region.step" in names
    assert "hair_pinch_right_latch_emergency_pull_access.step" in names
    assert "hair_pinch_left_adjustment_medial_guide_nip.step" in names
    assert "hair_pinch_right_adjustment_medial_guide_nip.step" in names

    for filename in (
        "hair_pinch_left_adjustment_medial_guide_nip.step",
        "hair_pinch_right_root_capture_future_pinch_region.step",
        "hair_pinch_right_latch_candidate_hair_pinch_region.step",
        "hair_pinch_right_latch_emergency_pull_access.step",
    ):
        imported = cq.importers.importStep(str(tmp_path / filename))
        assert imported.val().isValid()
        assert len(imported.val().Solids()) == 1
        assert float(imported.val().Volume()) > 0.0

    manifest = json.loads((tmp_path / "hair_pinch_keepouts_manifest.json").read_text(encoding="utf-8"))
    assert manifest["package_sha256"] == package.package_sha256
