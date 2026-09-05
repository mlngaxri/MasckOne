from __future__ import annotations

from functools import lru_cache
import json
import math

import cadquery as cq
import pytest

import masck_one.retention_load_path as rlp
from masck_one.retention_load_path import (
    ATTACHMENT_CLEARANCE,
    ATTACHMENT_FEATURE_OPEN,
    ATTACHMENT_INTEGRAL,
    ATTACHMENT_PINNED,
    CAPTURE_BORE_RADIUS_MM,
    CAPTURE_CLIP_INNER_RADIUS_MM,
    CAPTURE_PIN_GROOVE_RADIUS_MM,
    CAPTURE_PIN_RADIAL_CLEARANCE_MM,
    CAPTURE_PIN_RADIUS_MM,
    CAPTURE_PIN_SERVICE_WITHDRAWAL_MM,
    CROWN_LUG_CENTER_ABS_X_MM,
    CROWN_LUG_CENTER_Y_MM,
    CROWN_LUG_CENTER_Z_MM,
    LoadPathEdge,
    RetentionLoadPathError,
    SOURCE_CURRENT_MAIN_SHA,
    SOURCE_HAIR_PINCH_GIT_BLOB_SHA,
    SOURCE_PROMPT10_HEAD_SHA,
    SOURCE_RETENTION_FIT_GIT_BLOB_SHA,
    SOURCE_STRUCTURAL_FRAME_GIT_BLOB_SHA,
    build_retention_load_path,
    export_retention_load_path,
)


@lru_cache(maxsize=1)
def _package():
    return build_retention_load_path()


def _bbox(solid: cq.Workplane) -> tuple[float, float, float, float, float, float]:
    bb = solid.val().BoundingBox()
    return (bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax)


def _assert_one_solid(solid: cq.Workplane) -> None:
    shape = solid.val()
    assert shape.isValid()
    assert len(shape.Solids()) == 1
    assert float(shape.Volume()) > 0.0


def _intersection(first: cq.Workplane, second: cq.Workplane) -> float:
    return float(first.val().intersect(second.val()).Volume())


def test_source_bindings_and_four_zone_identity_are_fail_closed():
    package = _package()
    manifest = package.manifest()
    assert manifest["source_current_main_sha"] == SOURCE_CURRENT_MAIN_SHA
    assert manifest["source_prompt10_head_sha"] == SOURCE_PROMPT10_HEAD_SHA
    assert manifest["source_retention_fit_git_blob_sha"] == SOURCE_RETENTION_FIT_GIT_BLOB_SHA
    assert manifest["source_hair_pinch_git_blob_sha"] == SOURCE_HAIR_PINCH_GIT_BLOB_SHA
    assert manifest["source_structural_frame_git_blob_sha"] == SOURCE_STRUCTURAL_FRAME_GIT_BLOB_SHA
    assert manifest["four_zone_actuation_preserved"] is True
    assert manifest["physical_validation_eligible"] is False


def test_bilateral_successor_housings_and_carriers_are_real_connected_solids():
    package = _package()
    for side in (package.left, package.right):
        _assert_one_solid(side.successor_housing.solid)
        _assert_one_solid(side.carrier.solid)
        assert _intersection(side.successor_housing.solid, side.carrier.solid) == pytest.approx(0.0, abs=1e-8)
        distance = float(side.successor_housing.solid.val().distance(side.carrier.solid.val()))
        assert distance > 0.0
        assert distance < 0.5
        assert side.successor_housing.product_material is True
        assert side.carrier.product_material is True

    left = _bbox(package.left.carrier.solid)
    right = _bbox(package.right.carrier.solid)
    assert left[0] == pytest.approx(-right[1], abs=1e-6)
    assert left[1] == pytest.approx(-right[0], abs=1e-6)
    assert left[2:] == pytest.approx(right[2:], abs=1e-6)


def test_dual_pin_clevis_is_positive_capture_not_friction_or_raw_overlap():
    package = _package()
    assert CAPTURE_BORE_RADIUS_MM - CAPTURE_PIN_RADIUS_MM == pytest.approx(0.15, abs=1e-12)
    assert CAPTURE_PIN_RADIAL_CLEARANCE_MM == pytest.approx(0.15, abs=1e-12)
    assert CAPTURE_PIN_GROOVE_RADIUS_MM < CAPTURE_CLIP_INNER_RADIUS_MM < CAPTURE_PIN_RADIUS_MM

    for side in (package.left, package.right):
        assert len(side.capture_pins) == 2
        assert len(side.capture_clips) == 2
        for pin, clip in zip(side.capture_pins, side.capture_clips):
            _assert_one_solid(pin.solid)
            _assert_one_solid(clip.solid)
            assert _intersection(pin.solid, side.successor_housing.solid) == pytest.approx(0.0, abs=1e-8)
            assert _intersection(pin.solid, side.carrier.solid) == pytest.approx(0.0, abs=1e-8)
            assert _intersection(pin.solid, clip.solid) == pytest.approx(0.0, abs=1e-8)
            assert _intersection(clip.solid, side.successor_housing.solid) == pytest.approx(0.0, abs=1e-8)
            assert _intersection(clip.solid, side.carrier.solid) == pytest.approx(0.0, abs=1e-8)


def test_load_path_graph_distinguishes_closed_positive_edges_from_open_counterparts():
    manifest = _package().manifest()["load_path_graph"]
    edges = {edge["edge_id"]: edge for edge in manifest["edges"]}

    for prefix in ("LEFT", "RIGHT"):
        yoke_to_housing = edges[f"{prefix}_YOKE_TO_FIXED_HOUSING"]
        housing_to_carrier = edges[f"{prefix}_FIXED_HOUSING_TO_LOCAL_CARRIER"]
        carrier_to_crown = edges[f"{prefix}_LOCAL_CARRIER_TO_CROWN_LUG"]
        carrier_to_facial = edges[f"{prefix}_LOCAL_CARRIER_TO_FACIAL_HANDOFF"]
        crown_open = edges[f"{prefix}_CROWN_LUG_TO_CROWN_MEMBER"]
        facial_open = edges[f"{prefix}_FACIAL_HANDOFF_TO_FRONT_REACTION_LOOP"]

        assert yoke_to_housing["attachment_class"] == ATTACHMENT_PINNED
        assert housing_to_carrier["attachment_class"] == ATTACHMENT_PINNED
        assert carrier_to_crown["attachment_class"] == ATTACHMENT_INTEGRAL
        assert carrier_to_facial["attachment_class"] == ATTACHMENT_INTEGRAL
        for edge in (yoke_to_housing, housing_to_carrier, carrier_to_crown, carrier_to_facial):
            assert edge["positive_attachment"] is True
            assert edge["clearance_only"] is False
            assert edge["load_transfer_digitally_closed"] is True

        for edge in (crown_open, facial_open):
            assert edge["attachment_class"] == ATTACHMENT_FEATURE_OPEN
            assert edge["positive_attachment"] is True
            assert edge["clearance_only"] is False
            assert edge["load_transfer_digitally_closed"] is False

    assert manifest["occipital_to_local_carrier_positive_path_closed"] is True
    assert manifest["crown_to_head_path_closed"] is False
    assert manifest["facial_reaction_to_front_perimeter_path_closed"] is False
    assert manifest["whole_retention_load_path_closed"] is False


def test_clearance_semantics_cannot_masquerade_as_load_transfer():
    with pytest.raises(RetentionLoadPathError):
        LoadPathEdge(
            "BAD_CLEARANCE_LOAD_EDGE",
            "A",
            "B",
            ATTACHMENT_CLEARANCE,
            False,
            True,
            True,
            "invalid",
        )
    with pytest.raises(RetentionLoadPathError):
        LoadPathEdge(
            "BAD_OPEN_COUNTERPART_EDGE",
            "A",
            "B",
            ATTACHMENT_FEATURE_OPEN,
            True,
            False,
            True,
            "invalid",
        )


def test_crown_lugs_are_inside_existing_crown_corridor_but_do_not_claim_crown_member():
    package = _package()
    for side in (package.left, package.right):
        x, y, z = side.crown_lug_center_xyz_mm
        assert abs(x) == pytest.approx(CROWN_LUG_CENTER_ABS_X_MM, abs=1e-12)
        assert y == pytest.approx(CROWN_LUG_CENTER_Y_MM, abs=1e-12)
        assert z == pytest.approx(CROWN_LUG_CENTER_Z_MM, abs=1e-12)
        # Prompt 08 crown reservation: X [-68,68], Y [56,90], Z [-54,-40].
        assert -68.0 <= x <= 68.0
        assert 56.0 <= y <= 90.0
        assert -54.0 <= z <= -40.0
        _assert_one_solid(side.crown_clearance_reference)

    manifest = package.manifest()
    assert manifest["attachment_geometry"]["crown_lug_bore_realized"] is True
    assert manifest["attachment_geometry"]["crown_counterpart_realized"] is False


def test_facial_handoff_is_real_bore_but_front_frame_counterpart_remains_open():
    package = _package()
    for side in (package.left, package.right):
        _assert_one_solid(side.facial_clearance_reference)
        assert side.facial_handoff_center_xyz_mm[2] < 0.0
    manifest = package.manifest()
    assert manifest["attachment_geometry"]["facial_handoff_bore_realized"] is True
    assert manifest["attachment_geometry"]["front_perimeter_counterpart_realized"] is False
    assert "FRONT_PERIMETER_REACTION_FRAME_3D_COUNTERPART_AT_FACIAL_HANDOFF_LUGS" in manifest["unresolved_digital_requirements"]


def test_service_is_unworn_unpowered_and_preserves_positive_reset_semantics():
    package = _package()
    with pytest.raises(RetentionLoadPathError):
        package.service_sequence(worn=True, powered=False)
    with pytest.raises(RetentionLoadPathError):
        package.service_sequence(worn=False, powered=True)
    sequence = package.service_sequence(worn=False, powered=False)
    assert sequence[2]["travel_mm"] == pytest.approx(CAPTURE_PIN_SERVICE_WITHDRAWAL_MM)
    assert sequence[-1]["action"] == "REASSEMBLE_REVERSE_AND_RESEAT_BOTH_C_CLIPS"


def test_all_required_world_frame_clearance_checks_pass_and_do_not_claim_load():
    package = _package()
    assert package.clearance_checks
    assert all(check.passes for check in package.clearance_checks)
    manifest_checks = package.manifest()["clearance_checks"]
    assert all(check["relation_class"] == ATTACHMENT_CLEARANCE for check in manifest_checks)
    assert all(check["load_transfer_allowed"] is False for check in manifest_checks)
    assert all(check["intersection_volume_mm3"] == pytest.approx(0.0, abs=1e-8) for check in manifest_checks)


def test_manifest_is_deterministic_and_keeps_physical_gates_open():
    package = _package()
    first = package.manifest()
    second = package.manifest()
    assert first == second
    raw = json.dumps(package.manifest(include_sha=False), sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    import hashlib
    assert hashlib.sha256(raw).hexdigest() == package.package_sha256
    assert first["assembly_in_development_compound"] is False
    assert first["physical_validation_eligible"] is False
    assert "RETENTION_LOAD_CAPACITY_STIFFNESS_AND_STRUCTURAL_MARGIN" in first["unresolved_physical_gates"]
    assert "WET_ONE_HAND_RELEASE_FORCE_5_TO_12_N_AND_TIME_LE_2_S" in first["unresolved_physical_gates"]


def test_exported_representative_solids_round_trip(tmp_path):
    package = _package()
    outputs = export_retention_load_path(tmp_path, package)
    names = {path.name for path in outputs}
    expected = {
        "retention_load_path_left_successor_housing.step",
        "retention_load_path_right_successor_housing.step",
        "retention_load_path_left_carrier.step",
        "retention_load_path_right_carrier.step",
        "retention_load_path_left_capture_pin_1.step",
        "retention_load_path_right_capture_clip_2.step",
        "retention_load_path_left_crown_counterpart_clearance_reference.step",
        "retention_load_path_right_facial_counterpart_clearance_reference.step",
        "retention_load_path_manifest.json",
    }
    assert expected <= names

    for filename, source in (
        ("retention_load_path_right_successor_housing.step", package.right.successor_housing.solid),
        ("retention_load_path_right_carrier.step", package.right.carrier.solid),
        ("retention_load_path_right_capture_pin_1.step", package.right.capture_pins[0].solid),
        ("retention_load_path_right_capture_clip_1.step", package.right.capture_clips[0].solid),
    ):
        imported = cq.importers.importStep(str(tmp_path / filename))
        _assert_one_solid(imported)
        assert float(imported.val().Volume()) == pytest.approx(float(source.val().Volume()), rel=0.0, abs=1e-4)
        assert _bbox(imported) == pytest.approx(_bbox(source), abs=1e-5)
