from __future__ import annotations

import json
from pathlib import Path

import pytest

import masck_one.mvp_completeness as mc


def test_matrix_is_deterministic_and_explicitly_not_a_freeze() -> None:
    first = mc.build_mvp_completeness_matrix()
    second = mc.build_mvp_completeness_matrix()

    assert first.manifest() == second.manifest()
    assert first.manifest_sha256 == second.manifest_sha256
    assert first.digital_mvp_freeze_ready is False
    assert first.physical_validation_complete is False
    assert first.physical_validation_eligible is False
    manifest = first.manifest()
    assert manifest["source_main_sha"] == mc.SOURCE_MAIN_SHA
    assert manifest["source_package_tree_sha"] == mc.SOURCE_PACKAGE_TREE_SHA
    assert manifest["candidate_snapshot_release_authoritative"] is False
    assert manifest["candidate_snapshot_review_evidence_eligible"] is False


def test_geometry_required_row_cannot_be_closed_by_framework_or_reference() -> None:
    for evidence in (
        "AUTHORITY_CONTRACT",
        "DIGITAL_TOPOLOGY",
        "REFERENCE_ENVELOPE",
        "DFM_GATE_ONLY",
        "ABSENT",
    ):
        with pytest.raises(mc.MvpCompletenessError):
            mc.RequirementStatus(
                requirement_id="TEST-GEOMETRY",
                category="digital_mvp_deliverable",
                requirement="real geometry is required",
                geometry_required_for_closure=True,
                released_main_evidence=evidence,
                digital_state="CLOSED",
                owner_cells=(20,),
                candidate_prs=(),
                physical_gate_ids=(),
                closure_required="realize the missing geometry",
            )


def test_every_closed_geometry_row_has_realized_geometry_evidence() -> None:
    matrix = mc.build_mvp_completeness_matrix()
    closing = {"REALIZED_BREP", "REALIZED_CENTERLINE"}
    for item in matrix.requirements:
        if item.geometry_required_for_closure and item.digital_state == "CLOSED":
            assert item.released_main_evidence in closing


def test_candidate_observations_cannot_be_promoted_into_release_truth() -> None:
    with pytest.raises(mc.MvpCompletenessError):
        mc.CandidateObservation(
            pr_number=999,
            observed_head_sha="0" * 40,
            role="test",
            release_authoritative=True,
        )
    with pytest.raises(mc.MvpCompletenessError):
        mc.CandidateObservation(
            pr_number=999,
            observed_head_sha="0" * 40,
            role="test",
            review_evidence_eligible=True,
        )
    with pytest.raises(mc.MvpCompletenessError):
        mc.CandidateObservation(
            pr_number=999,
            observed_head_sha="0" * 40,
            role="test",
            requires_live_head_revalidation=False,
        )


def test_physical_gate_cannot_be_closed_by_digital_manifest() -> None:
    with pytest.raises(mc.MvpCompletenessError):
        mc.PhysicalGate(
            gate_id="PVAL-TEST",
            controlled_requirement="physical requirement",
            authority_status="VALIDATION_GATED",
            evidence_required="controlled physical evidence",
            owner_cells=(20,),
            closed=True,
        )


def test_candidate_snapshot_is_complete_and_unique() -> None:
    matrix = mc.build_mvp_completeness_matrix()
    numbers = tuple(item.pr_number for item in matrix.candidate_observations)
    assert numbers == tuple(sorted(numbers))
    assert len(numbers) == len(set(numbers))
    assert set(numbers) == {
        70, 71, 77, 80, 82, 85, 90, 91, 92, 93, 94, 96, 98, 99, 100, 101
    }
    assert all(item.release_authoritative is False for item in matrix.candidate_observations)
    assert all(item.review_evidence_eligible is False for item in matrix.candidate_observations)
    assert all(item.requires_live_head_revalidation is True for item in matrix.candidate_observations)


def test_all_physical_gates_remain_open() -> None:
    matrix = mc.build_mvp_completeness_matrix()
    assert matrix.physical_gates
    assert all(item.closed is False for item in matrix.physical_gates)
    assert matrix.manifest()["physical_validation_complete"] is False


def test_source_tree_movement_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(mc, "_released_package_tree_sha", lambda: "0" * 40)
    with pytest.raises(mc.MvpCompletenessError, match="producer tree moved"):
        mc.build_mvp_completeness_matrix()


def test_manifest_write_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "mvp_completeness.json"
    written = mc.write_mvp_completeness_manifest(path)
    assert written == path.resolve()

    matrix = mc.build_mvp_completeness_matrix()
    payload = json.loads(path.read_text(encoding="utf-8"))
    expected = matrix.manifest()
    expected["manifest_sha256"] = matrix.manifest_sha256
    assert payload == expected
    assert payload["schema"] == mc.SCHEMA
    assert payload["manifest_sha256"] == matrix.manifest_sha256
    assert payload["digital_mvp_freeze_ready"] is False
    assert payload["physical_validation_complete"] is False


def test_state_counts_match_rows() -> None:
    matrix = mc.build_mvp_completeness_matrix()
    counts = matrix.manifest()["digital_state_counts"]
    assert counts == {
        state: sum(item.digital_state == state for item in matrix.requirements)
        for state in ("CLOSED", "PARTIAL", "BLOCKED")
    }
    assert sum(counts.values()) == len(matrix.requirements)
    assert counts["BLOCKED"] > 0
