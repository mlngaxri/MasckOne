from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

import pytest

import cell20_merge_dependency_plan as mp

EXPECTED_SEQUENCE_PRS = {
    70, 92, 104, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116,
    117, 118, 120, 121, 123, 124, 125,
}
EXPECTED_GREEN_PRS = {107, 108, 109, 110, 112, 114, 116, 117, 118, 120, 121}


def test_plan_is_deterministic_and_draft_root_is_fail_closed() -> None:
    first = mp.merge_dependency_manifest()
    second = mp.merge_dependency_manifest()
    assert first == second
    assert first["schema"] == mp.SCHEMA
    assert first["source_main_sha"] == mp.SOURCE_MAIN_SHA
    assert first["world_frame_id"] == "MASCK_ONE_AUTHORITY_WORLD_MM"
    assert first["next_release_root_pr"] == 121
    assert first["next_release_expected_head_sha"] == mp.ROOT_HEAD_SHA
    assert first["next_release_root_evidence_complete"] is True
    assert first["next_release_pr_is_draft"] is True
    assert first["merge_permitted_now_prs"] == []
    assert first["required_owner_transition"] == "MARK_PR_121_READY_FOR_REVIEW_WITHOUT_MOVING_ITS_HEAD"
    assert first["downstream_merge_hold"] is True
    assert len(first["manifest_sha256"]) == 64


def test_verified_root_evidence_is_exact_and_retained() -> None:
    evidence = mp.merge_dependency_manifest()["verified_root_evidence"]
    assert evidence["workflow_run_id"] == 34010264572
    assert evidence["artifact_id"] == 9982589534
    assert evidence["artifact_sha256"] == "1dac6d1933e0b09b746e5fa1917792eb1acbb65625bab00551932eac5e13cf94"
    assert evidence["tested_tree_sha"] == "862eb97560228e619d82202fc4728715ee5fa13a"
    assert evidence["source_base_is_ancestor_of_source_head"] is True
    assert evidence["source_head_tree_equals_tested_tree"] is True


def test_sequence_contains_current_dependency_candidates_once() -> None:
    rows = mp.validate_plan()
    numbers = [row.pr_number for row in rows]
    assert set(numbers) == EXPECTED_SEQUENCE_PRS
    assert len(numbers) == len(set(numbers))
    assert 105 not in numbers
    assert {row.pr_number for row in rows if row.exact_head_green} == EXPECTED_GREEN_PRS


def test_every_dependency_is_in_an_earlier_phase_and_no_merge_is_permitted() -> None:
    rows = mp.validate_plan()
    by_pr = {row.pr_number: row for row in rows}
    root = by_pr[121]
    assert root.phase == 0
    assert root.release_evidence_complete is True
    assert root.merge_permitted_now is False
    assert by_pr[120].depends_on == (121,)
    assert all(not row.merge_permitted_now for row in rows)
    for row in rows:
        for dependency in row.depends_on:
            assert by_pr[dependency].phase < row.phase


def test_collision_audit_runs_after_service_inventory() -> None:
    rows = {row.pr_number: row for row in mp.validate_plan()}
    assert 114 in rows[112].depends_on
    assert rows[114].phase < rows[112].phase


def test_exterior_failure_is_not_promotable() -> None:
    row = {item.pr_number: item for item in mp.CANDIDATES}[70]
    assert row.ci_state == mp.CI_FAILURE
    assert row.exact_head_green is False
    assert row.action == mp.ACTION_REPAIR_REBASE_RETEST
    assert row.merge_permitted_now is False
    assert any("invalid solid" in blocker for blocker in row.blockers)


def test_guard_yoke_interference_forces_repair_after_yoke() -> None:
    row = {item.pr_number: item for item in mp.CANDIDATES}[109]
    assert 123 in row.depends_on
    assert row.action == mp.ACTION_REPAIR_REBASE_RETEST
    assert any("39.840676" in blocker for blocker in row.blockers)


def test_cartridge_capacity_and_shell_collision_force_redesign_hold() -> None:
    row = {item.pr_number: item for item in mp.CANDIDATES}[115]
    assert row.action == mp.ACTION_HOLD_REDESIGN
    joined = " ".join(row.blockers)
    assert "331.73801062482534" in joined
    assert "27.401629" in joined
    assert "34.887932" in joined
    assert row.merge_permitted_now is False


def test_mechanical_graph_red_head_is_late_repair_not_green() -> None:
    row = {item.pr_number: item for item in mp.CANDIDATES}[124]
    assert row.ci_state == mp.CI_FAILURE
    assert row.exact_head_green is False
    assert row.action == mp.ACTION_REPAIR_REBASE_RETEST
    joined = " ".join(row.blockers)
    assert "34010753193" in joined
    assert "stale #123" in joined
    assert "3 tests" in joined


def test_legacy_chain_collapse_is_explicit_and_quick_release_is_preserved() -> None:
    groups = {(group.source_prs, group.successor_pr): group.action for group in mp.COLLAPSE_GROUPS}
    assert groups[((83, 87, 89), 92)] == "CLOSE_AS_EXACT_ANCESTORS"
    assert groups[((75, 78), 107)] == "CLOSE_AFTER_CURRENT_MAIN_PORT"
    assert groups[((80,), 125)] == "CLOSE_AFTER_CURRENT_MAIN_PORT"
    assert groups[((105,), 104)] == "CONSOLIDATE_SOURCE_RECEIPT_THEN_CLOSE"
    assert groups[((85, 94, 96, 100), None)] == "PORT_USEFUL_PACKAGE_GEOMETRY_THEN_CLOSE"
    assert groups[((63, 64), None)] == "DONOR_ONLY_NEVER_MERGE"
    assert mp.PRESERVE_SEPARATELY == (71,)


def test_same_phase_dependency_is_rejected() -> None:
    rows = list(mp.CANDIDATES)
    idx = next(i for i, row in enumerate(rows) if row.pr_number == 120)
    rows[idx] = replace(rows[idx], phase=0)
    with pytest.raises(mp.MergePlanError):
        mp.validate_plan(rows)


def test_duplicate_candidate_is_rejected() -> None:
    with pytest.raises(mp.MergePlanError):
        mp.validate_plan((*mp.CANDIDATES, mp.CANDIDATES[0]))


def test_nonroot_release_evidence_promotion_is_rejected() -> None:
    candidate = next(row for row in mp.CANDIDATES if row.pr_number == 120)
    with pytest.raises(mp.MergePlanError):
        replace(candidate, release_evidence_complete=True)


def test_draft_root_merge_permission_is_rejected() -> None:
    root = next(row for row in mp.CANDIDATES if row.pr_number == 121)
    with pytest.raises(mp.MergePlanError):
        replace(root, merge_permitted_now=True)


def test_root_loses_evidence_eligibility_if_exact_head_or_green_state_changes() -> None:
    root = next(row for row in mp.CANDIDATES if row.pr_number == 121)
    with pytest.raises(mp.MergePlanError):
        replace(root, head_sha="0" * 40)
    with pytest.raises(mp.MergePlanError):
        replace(root, ci_state=mp.CI_FAILURE)


def test_manifest_round_trip(tmp_path: Path) -> None:
    output = tmp_path / "cell20_merge_dependency_plan.json"
    written = mp.write_manifest(output)
    assert written == output.resolve()
    assert json.loads(output.read_text(encoding="utf-8")) == mp.merge_dependency_manifest()
