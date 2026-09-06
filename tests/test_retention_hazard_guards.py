from __future__ import annotations

import json
from pathlib import Path

import cadquery as cq
import pytest

import masck_one.retention_hazard_guards as rhg
from masck_one.retention_hazard_guards import (
    CANDIDATE_INTERFACE_SHA256,
    SOURCE_CELL3_RETENTION_HEAD_SHA,
    SOURCE_MAIN_SHA,
    SOURCE_RIGHT_RELEASE_HEAD_SHA,
    RetentionHazardGuardError,
    build_retention_hazard_guards,
    export_retention_hazard_guard_review,
)
from masck_one.model import build_model


@pytest.fixture(scope="module")
def model():
    return build_model()


@pytest.fixture(scope="module")
def package(model):
    return build_retention_hazard_guards(model.authority, model)


def _bbox(solid: cq.Workplane):
    bb = solid.val().BoundingBox()
    return (bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax)


def test_guard_inventory_is_compact_physical_candidate_geometry(package):
    guards = {guard.part_id: guard for guard in package.guards}
    assert set(guards) == {
        "CELL8_RIGHT_QUICK_RELEASE_U_SHROUD",
        "CELL8_LEFT_ADJUSTMENT_U_SHROUD",
        "CELL8_RIGHT_ADJUSTMENT_U_SHROUD",
    }

    quick = guards["CELL8_RIGHT_QUICK_RELEASE_U_SHROUD"]
    left = guards["CELL8_LEFT_ADJUSTMENT_U_SHROUD"]
    right = guards["CELL8_RIGHT_ADJUSTMENT_U_SHROUD"]

    assert _bbox(quick.solid) == pytest.approx((70.0, 90.0, -8.5, 8.5, -25.0, -10.0))
    assert _bbox(right.solid) == pytest.approx((76.5, 87.5, -1.5, 29.0, -37.5, -25.75))
    assert _bbox(left.solid) == pytest.approx((-87.5, -76.5, -1.5, 29.0, -37.5, -25.75))
    assert float(quick.solid.val().Volume()) == pytest.approx(1112.5)
    assert float(right.solid.val().Volume()) == pytest.approx(708.125)
    assert float(left.solid.val().Volume()) == pytest.approx(708.125)
    assert all(guard.solid.val().isValid() and len(guard.solid.val().Solids()) == 1 for guard in package.guards)


def test_factory_install_sweeps_are_exact_complete_axis_translation_bounds(package):
    quick = package.right_quick_release_guard
    left = package.left_adjustment_guard
    right = package.right_adjustment_guard

    assert _bbox(quick.exact_factory_install_sweep) == pytest.approx(
        (35.0, 90.0, -8.5, 8.5, -25.0, -10.0)
    )
    assert _bbox(right.exact_factory_install_sweep) == pytest.approx(
        (54.5, 87.5, -1.5, 29.0, -37.5, -25.75)
    )
    assert _bbox(left.exact_factory_install_sweep) == pytest.approx(
        (-87.5, -54.5, -1.5, 29.0, -37.5, -25.75)
    )
    assert float(quick.exact_factory_install_sweep.val().Volume()) == pytest.approx(3059.375)
    assert float(right.exact_factory_install_sweep.val().Volume()) == pytest.approx(2124.375)
    assert float(left.exact_factory_install_sweep.val().Volume()) == pytest.approx(2124.375)


def test_source_hazards_access_released_packages_and_protected_regions_all_clear(package):
    assert package.clearance_checks
    assert all(check.passes for check in package.clearance_checks)
    assert all(check.intersection_volume_mm3 == 0.0 for check in package.clearance_checks)

    by_id = {check.check_id: check for check in package.clearance_checks}
    assert by_id["RIGHT_QUICK_GUARD_CLEAR_LATCH_HAZARD"].minimum_distance_mm == pytest.approx(0.75)
    assert by_id["RIGHT_QUICK_GUARD_CLEAR_EMERGENCY_PULL_ACCESS"].minimum_distance_mm > 1.0
    assert by_id["RIGHT_ADJUST_GUARD_CLEAR_SOURCE_HAZARD_1"].minimum_distance_mm == pytest.approx(0.5)
    assert by_id["RIGHT_ADJUST_GUARD_CLEAR_SCALP_HAIR_APPROACH_CORRIDOR"].minimum_distance_mm == pytest.approx(0.5)

    assert any("_CLEAR_RELEASED_RIGID_SHELL" in check.check_id for check in package.clearance_checks)
    assert any("_INSTALL_SWEEP_CLEAR_RELEASED_RIGID_SHELL" in check.check_id for check in package.clearance_checks)
    assert any("_CLEAR_PROTECTED_" in check.check_id for check in package.clearance_checks)


def test_right_emergency_pull_access_is_preserved_by_strict_x_plane(package):
    quick_bounds = _bbox(package.right_quick_release_guard.solid)
    assert quick_bounds[1] == pytest.approx(90.0)
    assert rhg.RIGHT_LATCH_EMERGENCY_PULL_ACCESS_BOUNDS_MM[0] == pytest.approx(91.0)
    assert rhg.RIGHT_LATCH_EMERGENCY_PULL_ACCESS_BOUNDS_MM[0] - quick_bounds[1] == pytest.approx(1.0)


def test_adjustment_guards_do_not_claim_root_or_scalp_corridor_closure(package):
    manifest = package.manifest()
    coverage = manifest["guard_coverage"]
    assert coverage["bilateral_adjustment_guide_index_stop_shrouds_realized_digitally"] is True
    assert coverage["bilateral_root_capture_guard_closed"] is False
    assert coverage["bilateral_scalp_hair_corridor_guard_closed"] is False
    assert coverage["physical_hair_or_pinch_safety_validated"] is False

    unresolved = set(manifest["unresolved_digital_requirements"])
    assert "BILATERAL_ROOT_CAPTURE_GUARD_OR_EDGE_TREATMENT" in unresolved
    assert "BILATERAL_SCALP_HAIR_APPROACH_GUARD_OR_CONTROLLED_SOFT_INTERFACE" in unresolved


def test_candidate_sources_are_exact_and_explicitly_non_authoritative(package):
    manifest = package.manifest()
    assert manifest["source_main_sha"] == SOURCE_MAIN_SHA
    assert manifest["candidate_interface_status"] == "NON_AUTHORITATIVE_UNMERGED_CANDIDATE_INTERFACE"
    assert manifest["candidate_interface_sha256"] == CANDIDATE_INTERFACE_SHA256
    assert manifest["candidate_interface"]["source_cell3_retention_head_sha"] == SOURCE_CELL3_RETENTION_HEAD_SHA
    assert manifest["candidate_interface"]["source_right_release_head_sha"] == SOURCE_RIGHT_RELEASE_HEAD_SHA
    assert manifest["promotion_requires_live_candidate_head_revalidation"] is True


def test_candidate_interface_mutation_fails_closed(monkeypatch):
    original = rhg.RIGHT_LATCH_EMERGENCY_PULL_ACCESS_BOUNDS_MM
    monkeypatch.setattr(
        rhg,
        "RIGHT_LATCH_EMERGENCY_PULL_ACCESS_BOUNDS_MM",
        (original[0], original[1] - 0.5, *original[2:]),
    )
    with pytest.raises(RetentionHazardGuardError, match="source revalidation"):
        rhg._assert_candidate_interface_contract()


def test_released_source_identity_mutation_fails_closed(monkeypatch):
    monkeypatch.setattr(rhg, "SOURCE_MODEL_GIT_BLOB_SHA", "0" * 40)
    with pytest.raises(RetentionHazardGuardError, match="released-source rebind"):
        rhg._assert_released_source_blobs()


def test_nonfinite_or_boolean_geometry_inputs_fail_closed():
    with pytest.raises(RetentionHazardGuardError, match="exact numeric scalar"):
        rhg._box_from_bounds((True, 1.0, 0.0, 1.0, 0.0, 1.0))
    with pytest.raises(RetentionHazardGuardError, match="finite"):
        rhg._box_from_bounds((0.0, float("nan"), 0.0, 1.0, 0.0, 1.0))


def test_attachment_and_physical_evidence_firewall_remains_open(package):
    manifest = package.manifest()
    semantics = manifest["assembly_semantics"]
    assert semantics["positive_guard_attachment_realized"] is False
    assert semantics["friction_only_attachment_allowed"] is False
    assert semantics["overlap_as_attachment_allowed"] is False
    assert semantics["reference_sweeps_are_product_material"] is False
    assert manifest["physical_validation_eligible"] is False

    for guard in manifest["guards"]:
        assert guard["positive_attachment_realized"] is False
        assert guard["assembly_in_development_compound"] is False
        assert guard["material"] is None
        assert guard["mass_g"] is None

    physical = set(manifest["unresolved_physical_gates"])
    assert "WET_ONE_HAND_RELEASE_FORCE_5_TO_12_N" in physical
    assert "WET_ONE_HAND_RELEASE_TIME_LE_2_S" in physical
    assert "HAIR_ENTRAPMENT_AND_PINCH_SAFETY" in physical


def test_manifest_is_deterministic_and_finite(package):
    first = package.manifest()
    second = package.manifest()
    assert first == second
    assert first["package_sha256"] == package.package_sha256
    encoded = json.dumps(first, sort_keys=True, allow_nan=False)
    assert "NaN" not in encoded
    assert "Infinity" not in encoded


def test_step_review_export_round_trips_parts_and_exact_sweeps(tmp_path: Path, package):
    outputs = export_retention_hazard_guard_review(tmp_path, package)
    names = {path.name for path in outputs}
    expected = {
        "cell8_right_quick_release_u_shroud.step",
        "cell8_right_quick_release_u_shroud_exact_factory_install_sweep_reference.step",
        "cell8_left_adjustment_u_shroud.step",
        "cell8_left_adjustment_u_shroud_exact_factory_install_sweep_reference.step",
        "cell8_right_adjustment_u_shroud.step",
        "cell8_right_adjustment_u_shroud_exact_factory_install_sweep_reference.step",
        "retention_hazard_guards_manifest.json",
    }
    assert names == expected

    for filename in expected - {"retention_hazard_guards_manifest.json"}:
        imported = cq.importers.importStep(str(tmp_path / filename))
        assert imported.val().isValid()
        assert len(imported.val().Solids()) == 1
        assert float(imported.val().Volume()) > 0.0

    manifest = json.loads(
        (tmp_path / "retention_hazard_guards_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["package_sha256"] == package.package_sha256
