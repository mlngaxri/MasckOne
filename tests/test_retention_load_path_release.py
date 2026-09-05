from __future__ import annotations

from functools import lru_cache
import json

import pytest

from masck_one.occipital_stabilizer import SOURCE_AUTHORITY_BLOB_SHA
from masck_one.retention_load_path import (
    ATTACHMENT_FEATURE_OPEN,
    ATTACHMENT_INTEGRAL,
    ATTACHMENT_PINNED,
)
from masck_one.retention_load_path_release import (
    DIGITAL_ONLY,
    SCHEMA,
    SOURCE_MODEL_GIT_BLOB_SHA,
    SOURCE_RETENTION_LOAD_PATH_GIT_BLOB_SHA,
    RetentionLoadPathReleaseError,
    build_retention_load_path_release,
    export_retention_load_path_release,
)


@lru_cache(maxsize=1)
def _release():
    return build_retention_load_path_release()


def test_release_is_exactly_bound_to_prompt11_geometry_model_and_authority_sources():
    release = _release()
    manifest = release.manifest()
    assert manifest["schema"] == SCHEMA
    assert manifest["source_retention_load_path_git_blob_sha"] == SOURCE_RETENTION_LOAD_PATH_GIT_BLOB_SHA
    assert manifest["source_model_git_blob_sha"] == SOURCE_MODEL_GIT_BLOB_SHA
    assert manifest["source_authority_git_blob_sha"] == SOURCE_AUTHORITY_BLOB_SHA
    assert manifest["source_retention_load_path_package_sha256"] == release.source.package_sha256
    assert manifest["source_geometry_binding"]["package_sha256"] == release.source.package_sha256
    assert manifest["source_geometry_binding"]["v1_geometry_bytes_modified_by_v2"] is False
    assert manifest["source_geometry_binding"]["release_facing_semantics_owned_by_this_v2_contract"] is True


def test_open_handoff_feature_is_not_mislabelled_as_existing_positive_attachment():
    graph = _release().manifest()["load_path_graph"]
    open_edges = [edge for edge in graph["edges"] if edge["attachment_class"] == ATTACHMENT_FEATURE_OPEN]
    assert len(open_edges) == 4
    for edge in open_edges:
        assert edge["positive_attachment_feature_realized"] is True
        assert edge["mating_counterpart_realized"] is False
        assert edge["integral_material_continuity"] is False
        assert edge["positive_attachment"] is False
        assert edge["load_transfer_digitally_closed"] is False

    assert graph["crown_positive_attachment_feature_realized"] is True
    assert graph["crown_to_head_positive_attachment_realized"] is False
    assert graph["crown_to_head_path_closed"] is False
    assert graph["facial_positive_attachment_feature_realized"] is True
    assert graph["facial_reaction_to_front_perimeter_positive_attachment_realized"] is False
    assert graph["facial_reaction_to_front_perimeter_path_closed"] is False
    assert graph["whole_retention_load_path_closed"] is False


def test_retained_pin_edges_are_positive_attachments_and_integral_edges_are_not():
    graph = _release().manifest()["load_path_graph"]
    edges = graph["edges"]

    pinned = [edge for edge in edges if edge["attachment_class"] == ATTACHMENT_PINNED]
    integral = [edge for edge in edges if edge["attachment_class"] == ATTACHMENT_INTEGRAL]
    assert len(pinned) == 4
    assert len(integral) == 4

    for edge in pinned:
        assert edge["load_transfer_digitally_closed"] is True
        assert edge["positive_attachment"] is True
        assert edge["positive_attachment_feature_realized"] is True
        assert edge["mating_counterpart_realized"] is True
        assert edge["integral_material_continuity"] is False
        assert edge["clearance_only"] is False

    for edge in integral:
        assert edge["load_transfer_digitally_closed"] is True
        assert edge["positive_attachment"] is False
        assert edge["positive_attachment_feature_realized"] is False
        assert edge["mating_counterpart_realized"] is None
        assert edge["integral_material_continuity"] is True
        assert edge["clearance_only"] is False

    assert set(graph["positive_attachment_edge_ids"]) == {edge["edge_id"] for edge in pinned}
    assert set(graph["integral_material_continuity_edge_ids"]) == {
        edge["edge_id"] for edge in integral
    }
    assert len(graph["digitally_closed_edge_ids"]) == 8
    assert graph["crown_lug_integral_to_local_carrier"] is True
    assert graph["facial_handoff_lug_integral_to_local_carrier"] is True


def test_carriers_have_strict_separating_plane_from_prompt08_central_rear_package():
    rear = _release().manifest()["rear_packaging_discipline"]
    assert rear["source_keepout_center_xyz_mm"] == [0.0, 0.0, -36.0]
    assert rear["source_keepout_xyz_mm"] == [68.0, 104.0, 24.0]
    assert rear["strict_x_separating_plane_proof"] is True
    assert rear["clearance_is_load_transfer"] is False
    assert rear["carrier_x_separation_mm"]["wearer_left_mm"] == pytest.approx(22.0, abs=1e-6)
    assert rear["carrier_x_separation_mm"]["wearer_right_mm"] == pytest.approx(22.0, abs=1e-6)


def test_service_maturity_does_not_promote_pin_bound_into_complete_carrier_removal():
    manifest = _release().manifest()
    service = manifest["service_maturity"]
    assert service["capture_pin_withdrawal_travel_mm"] == pytest.approx(14.0)
    assert service["capture_pin_motion_proof"] == (
        "CONSERVATIVE_TWO_STATE_AXIS_ALIGNED_BOUND_OVER_COMPLETE_PURE_Y_TRANSLATION"
    )
    assert service["capture_pin_motion_is_exact_swept_brep"] is False
    assert service["carrier_separation_trajectory_realized"] is False
    assert service["carrier_separation_clearance_validated"] is False
    assert service["wearer_service_allowed"] is False
    assert service["powered_service_allowed"] is False
    assert service["reset_requires_both_capture_pins_and_both_clips_reseated"] is True

    sequence = manifest["service_sequence_release_semantics"]
    assert sequence[2]["action"] == "WITHDRAW_BOTH_CAPTURE_PINS_POSITIVE_Y_WITHIN_CONTROLLED_BOUND"
    assert sequence[3]["action"] == "CARRIER_SEPARATION_TRAJECTORY_UNRESOLVED"
    assert sequence[3]["service_clearance_validated"] is False
    assert "CARRIER_NONTELEPORTING_SEPARATION_AND_REASSEMBLY_TRAJECTORY" in manifest[
        "unresolved_digital_requirements"
    ]


def test_clearance_evidence_remains_nonload_and_physical_gates_remain_open():
    manifest = _release().manifest()
    assert manifest["clearance_checks"]
    assert all(check["relation_class"] == "CLEARANCE_ONLY_DOES_NOT_CARRY_LOAD" for check in manifest["clearance_checks"])
    assert all(check["load_transfer_allowed"] is False for check in manifest["clearance_checks"])
    assert manifest["four_zone_actuation_preserved"] is True
    assert manifest["assembly_in_development_compound"] is False
    assert manifest["physical_validation_eligible"] is False
    assert manifest["evidence_status"] == DIGITAL_ONLY
    assert "RETENTION_LOAD_CAPACITY_STIFFNESS_AND_STRUCTURAL_MARGIN" in manifest[
        "unresolved_physical_gates"
    ]
    assert "WET_ONE_HAND_RELEASE_FORCE_5_TO_12_N_AND_TIME_LE_2_S" in manifest[
        "unresolved_physical_gates"
    ]


def test_release_manifest_is_deterministic():
    release = _release()
    first = release.manifest()
    second = release.manifest()
    assert first == second
    raw = json.dumps(
        release.manifest(include_sha=False),
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    import hashlib

    assert hashlib.sha256(raw).hexdigest() == release.release_sha256


def test_release_source_blob_tamper_fails_closed(monkeypatch):
    import masck_one.retention_load_path_release as module

    monkeypatch.setattr(module, "SOURCE_RETENTION_LOAD_PATH_GIT_BLOB_SHA", "0" * 40)
    with pytest.raises(RetentionLoadPathReleaseError, match="requires explicit rebind"):
        module.build_retention_load_path_release(_release().source)


def test_release_model_blob_tamper_fails_closed(monkeypatch):
    import masck_one.retention_load_path_release as module

    monkeypatch.setattr(module, "SOURCE_MODEL_GIT_BLOB_SHA", "0" * 40)
    with pytest.raises(RetentionLoadPathReleaseError, match="requires explicit rebind"):
        module.build_retention_load_path_release(_release().source)


def test_release_export_preserves_geometry_files_and_replaces_manifest_semantics(tmp_path):
    release = _release()
    outputs = export_retention_load_path_release(tmp_path, release)
    names = {path.name for path in outputs}
    assert "retention_load_path_right_carrier.step" in names
    assert "retention_load_path_left_successor_housing.step" in names
    assert "retention_load_path_manifest.json" in names

    payload = json.loads((tmp_path / "retention_load_path_manifest.json").read_text(encoding="utf-8"))
    assert payload["schema"] == SCHEMA
    assert payload["release_sha256"] == release.release_sha256
    assert payload["load_path_graph"]["whole_retention_load_path_closed"] is False

    open_edges = [
        edge
        for edge in payload["load_path_graph"]["edges"]
        if edge["attachment_class"] == ATTACHMENT_FEATURE_OPEN
    ]
    integral_edges = [
        edge
        for edge in payload["load_path_graph"]["edges"]
        if edge["attachment_class"] == ATTACHMENT_INTEGRAL
    ]
    assert open_edges and integral_edges
    assert all(edge["positive_attachment"] is False for edge in open_edges)
    assert all(edge["positive_attachment_feature_realized"] is True for edge in open_edges)
    assert all(edge["positive_attachment"] is False for edge in integral_edges)
    assert all(edge["integral_material_continuity"] is True for edge in integral_edges)
