from __future__ import annotations

import json
from pathlib import Path

import pytest

import cell20_mvp_release_matrix as rm
from masck_one.mvp_completeness import MvpCompletenessError, RequirementStatus


EXPECTED_CANDIDATES = {
    70, 71, 77, 80, 82, 85, 90, 91, 92, 93, 94, 96, 98, 99, 100, 101,
    103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116,
    117, 118,
}


def test_live_release_matrix_is_deterministic_and_not_freeze_ready() -> None:
    first = rm.live_release_manifest()
    second = rm.live_release_manifest()
    assert first == second
    assert first["schema"] == rm.SCHEMA
    assert first["supersedes_schema"] == rm.SUPERSEDES_SCHEMA
    assert first["source_main_sha"] == rm.SOURCE_MAIN_SHA
    assert first["digital_mvp_freeze_ready"] is False
    assert first["physical_validation_complete"] is False
    assert first["physical_validation_eligible"] is False
    assert first["release_authoritative_candidate_prs"] == []
    assert first["candidate_head_movement_requires_reconstruction"] is True


def test_live_matrix_removes_self_referential_blocker_row() -> None:
    matrix = rm.build_live_release_matrix()
    ids = {row.requirement_id for row in matrix.requirements}
    assert "MVP-021" not in ids
    assert len(ids) == 37
    assert matrix.digital_state_counts == {"CLOSED": 10, "PARTIAL": 7, "BLOCKED": 20}


def test_live_candidate_snapshot_is_complete_unique_and_non_authoritative() -> None:
    matrix = rm.build_live_release_matrix()
    numbers = tuple(item.pr_number for item in matrix.candidate_observations)
    assert numbers == tuple(sorted(numbers))
    assert set(numbers) == EXPECTED_CANDIDATES
    assert len(numbers) == len(EXPECTED_CANDIDATES)
    assert all(item.release_authoritative is False for item in matrix.candidate_observations)
    assert all(item.review_evidence_eligible is False for item in matrix.candidate_observations)
    assert all(item.requires_live_head_revalidation is True for item in matrix.candidate_observations)


def test_rebound_candidate_heads_match_latest_api_snapshot() -> None:
    matrix = rm.build_live_release_matrix()
    heads = {item.pr_number: item.observed_head_sha for item in matrix.candidate_observations}
    assert heads[92] == "abb806a8e15a1557c8b5a4c754af1bfeea8b6d70"
    assert heads[104] == "1b4411fd2759bf92af2eccef4b1325b0897b7f72"
    assert heads[107] == "22d2e5baccbcfa56aa4a70e4e4dd59693e15affd"
    assert heads[108] == "0bf6c73028284ba9a5715ef5235bb2be1c298403"
    assert heads[109] == "fb586cc1ea1cde92526417593f9e5aa990d2ae4f"
    assert heads[111] == "6899b61db8cd549c44a82b12e78fe4028a2e7048"
    assert heads[112] == "abbfa427660a3752cce7d18b86faa44654884936"
    assert heads[114] == "630cc19497661ae834032eb8ea06e28dfd6100b7"
    assert heads[115] == "b61d71433f81e3f3e03307a350334a76e9dbf361"
    assert heads[117] == "6e3e1385f350735731ac08ff107a3c1d0f76189e"
    assert heads[118] == "37e03df4b6abbd222422c8bfd4e70b03a4e5ae07"


def test_current_specialist_candidates_map_to_their_requirements() -> None:
    matrix = rm.build_live_release_matrix()
    rows = {row.requirement_id: row for row in matrix.requirements}
    expected = {
        "ARCH-009": {107},
        "ARCH-012": {115},
        "MVP-003": {117},
        "MVP-004": {118},
        "MVP-010": {111},
        "MVP-011": {113},
        "MVP-012": {110},
        "MVP-016": {116},
        "MVP-017": {108},
        "MVP-019": {103, 112},
    }
    for requirement_id, candidate_ids in expected.items():
        assert candidate_ids.issubset(rows[requirement_id].candidate_prs)


def test_candidate_overlay_cannot_advance_released_maturity() -> None:
    baseline = rm.build_mvp_completeness_matrix()
    live = rm.build_live_release_matrix()
    baseline_rows = {row.requirement_id: row for row in baseline.requirements}
    for row in live.requirements:
        source = baseline_rows[row.requirement_id]
        assert row.digital_state == source.digital_state
        assert row.released_main_evidence == source.released_main_evidence
        assert row.geometry_required_for_closure == source.geometry_required_for_closure


def test_geometry_framework_still_cannot_close_geometry_requirement() -> None:
    with pytest.raises(MvpCompletenessError):
        RequirementStatus(
            requirement_id="TEST-LIVE-GEOMETRY",
            category="digital_mvp_deliverable",
            requirement="real geometry required",
            geometry_required_for_closure=True,
            released_main_evidence="DIGITAL_TOPOLOGY",
            digital_state="CLOSED",
            owner_cells=(20,),
            candidate_prs=(),
            physical_gate_ids=(),
            closure_required="realize the geometry",
        )


def test_all_physical_validation_gates_remain_open() -> None:
    matrix = rm.build_live_release_matrix()
    assert len(matrix.physical_gates) == 9
    assert all(gate.closed is False for gate in matrix.physical_gates)
    assert rm.live_release_manifest()["physical_validation_blocker_count"] == 9


def test_live_manifest_round_trip(tmp_path: Path) -> None:
    output = tmp_path / "cell20_mvp_release_matrix.json"
    written = rm.write_live_release_manifest(output)
    assert written == output.resolve()
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload == rm.live_release_manifest()
    assert len(payload["manifest_sha256"]) == 64
    assert payload["candidate_overlay_evidence_boundary"] == rm.EVIDENCE_BOUNDARY
