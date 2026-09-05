from __future__ import annotations

from functools import lru_cache
import json

import pytest

from masck_one.retention_load_path import ATTACHMENT_FEATURE_OPEN
from masck_one.retention_load_path_release import (
    DIGITAL_ONLY,
    SCHEMA,
    SOURCE_RETENTION_LOAD_PATH_GIT_BLOB_SHA,
    RetentionLoadPathReleaseError,
    build_retention_load_path_release,
    export_retention_load_path_release,
)


@lru_cache(maxsize=1)
def _release():
    return build_retention_load_path_release()


def test_release_is_exactly_bound_to_prompt11_geometry_source():
    release = _release()
    manifest = release.manifest()
    assert manifest["schema"] == SCHEMA
    assert manifest["source_retention_load_path_git_blob_sha"] == SOURCE_RETENTION_LOAD_PATH_GIT_BLOB_SHA
    assert manifest["source_retention_load_path_package_sha256"] == release.source.package_sha256
    assert manifest["source_geometry_manifest"]["package_sha256"] == release.source.package_sha256


def test_open_handoff_feature_is_not_mislabelled_as_existing_positive_attachment():
    graph = _release().manifest()["load_path_graph"]
    open_edges = [edge for edge in graph["edges"] if edge["attachment_class"] == ATTACHMENT_FEATURE_OPEN]
    assert len(open_edges) == 4
    for edge in open_edges:
        assert edge["positive_attachment_feature_realized"] is True
        assert edge["mating_counterpart_realized"] is False
        assert edge["positive_attachment"] is False
        assert edge["load_transfer_digitally_closed"] is False

    assert graph["crown_positive_attachment_feature_realized"] is True
    assert graph["crown_to_head_positive_attachment_realized"] is False
    assert graph["crown_to_head_path_closed"] is False
    assert graph["facial_positive_attachment_feature_realized"] is True
    assert graph["facial_reaction_to_front_perimeter_positive_attachment_realized"] is False
    assert graph["facial_reaction_to_front_perimeter_path_closed"] is False
    assert graph["whole_retention_load_path_closed"] is False


def test_closed_local_edges_remain_actual_positive_attachment_or_integral_material():
    graph = _release().manifest()["load_path_graph"]
    closed = [edge for edge in graph["edges"] if edge["load_transfer_digitally_closed"]]
    assert len(closed) == 8
    for edge in closed:
        assert edge["positive_attachment"] is True
        assert edge["positive_attachment_feature_realized"] is True
        assert edge["mating_counterpart_realized"] is True
        assert edge["clearance_only"] is False


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
    assert open_edges
    assert all(edge["positive_attachment"] is False for edge in open_edges)
    assert all(edge["positive_attachment_feature_realized"] is True for edge in open_edges)
