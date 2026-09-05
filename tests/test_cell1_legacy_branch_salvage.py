from __future__ import annotations

from copy import deepcopy

import pytest

from scripts.validate_cell1_legacy_branch_salvage import (
    SalvageMapError,
    load_salvage_map,
    validate_salvage_map,
)


def _entry(data: dict[str, object], pr: int) -> dict[str, object]:
    entries = data["entries"]
    assert isinstance(entries, list)
    return next(item for item in entries if isinstance(item, dict) and item.get("pr") == pr)


def _relation(
    data: dict[str, object], legacy_pr: int, candidate_pr: int
) -> dict[str, object]:
    relations = data["successor_relations"]
    assert isinstance(relations, list)
    return next(
        item
        for item in relations
        if isinstance(item, dict)
        and item.get("legacy_pr") == legacy_pr
        and item.get("candidate_pr") == candidate_pr
    )


def test_live_salvage_map_is_internally_release_safe() -> None:
    data = load_salvage_map()
    validate_salvage_map(data)

    assert data["reconstructed_main_sha"] == "5fce2a43a34d8be49256677a35af60c906dc1653"
    assert _entry(data, 62)["classification"] == "SUPERSEDED"
    assert _entry(data, 62)["superseded_by_pr"] == 70
    assert _entry(data, 63)["classification"] == "PORTABLE"
    assert _entry(data, 64)["classification"] == "PORTABLE"
    assert _entry(data, 65)["classification"] == "REJECT"
    assert _entry(data, 66)["classification"] == "SUPERSEDED"
    assert _entry(data, 68)["classification"] == "PORTABLE"
    assert _entry(data, 70)["classification"] == "PORTABLE"
    assert _entry(data, 71)["classification"] == "PORTABLE"
    assert _entry(data, 72)["classification"] == "SUPERSEDED"
    assert _entry(data, 72)["superseded_by_pr"] == 68
    assert _relation(data, 62, 70)["coverage"] == "FULL_PORT"
    assert _relation(data, 63, 71)["coverage"] == "PARTIAL_PORT"
    assert _relation(data, 72, 68)["coverage"] == "FULL_PORT"


def test_stale_mechanical_source_cannot_be_promoted_to_mergeable() -> None:
    data = deepcopy(load_salvage_map())
    pr64 = _entry(data, 64)
    pr64["classification"] = "MERGEABLE"
    pr64["release_disposition"] = "ELIGIBLE_FOR_RELEASE"
    pr64["blockers"] = []
    pr64["independent_review"] = "APPROVED"
    ci = pr64["exact_head_ci"]
    assert isinstance(ci, dict)
    ci["conclusion"] = "SUCCESS"

    with pytest.raises(SalvageMapError, match="stale main base|stale geometry bindings"):
        validate_salvage_map(data)


def test_stale_geometry_binding_requires_digest_recomputation() -> None:
    data = deepcopy(load_salvage_map())
    pr64 = _entry(data, 64)
    bindings = pr64["source_bindings"]
    assert isinstance(bindings, list)
    manual_a = next(
        item
        for item in bindings
        if isinstance(item, dict)
        and item.get("producer") == "MANUAL_A_PR_63_V2_INTEGRATION_SOURCE"
    )
    manual_a["digest_status"] = "OLD_DIGEST_ACCEPTED"

    with pytest.raises(SalvageMapError, match="digest recomputation"):
        validate_salvage_map(data)


def test_non_release_safe_exact_source_cannot_be_promoted_to_mergeable() -> None:
    data = deepcopy(load_salvage_map())
    pr68 = _entry(data, 68)
    bindings = pr68["source_bindings"]
    assert isinstance(bindings, list)
    binding = bindings[0]
    assert isinstance(binding, dict)
    binding["release_safe"] = False
    pr68["classification"] = "MERGEABLE"
    pr68["release_disposition"] = "ELIGIBLE_FOR_RELEASE"
    pr68["blockers"] = []
    pr68["independent_review"] = "APPROVED"
    ci = pr68["exact_head_ci"]
    assert isinstance(ci, dict)
    ci["conclusion"] = "SUCCESS"

    with pytest.raises(SalvageMapError, match="non-release-safe source bindings"):
        validate_salvage_map(data)


def test_mismatched_sha_cannot_be_marked_release_safe() -> None:
    data = deepcopy(load_salvage_map())
    pr63 = _entry(data, 63)
    bindings = pr63["source_bindings"]
    assert isinstance(bindings, list)
    main_binding = bindings[0]
    assert isinstance(main_binding, dict)
    main_binding["release_safe"] = True

    with pytest.raises(SalvageMapError, match="mismatched SHAs cannot be release-safe"):
        validate_salvage_map(data)


def test_full_port_successor_requires_legacy_superseded() -> None:
    data = deepcopy(load_salvage_map())
    legacy = _entry(data, 62)
    legacy["classification"] = "PORTABLE"
    legacy["blockers"] = ["INVALID_TEST_BLOCKER"]

    with pytest.raises(SalvageMapError, match="FULL_PORT successor requires legacy PR #62"):
        validate_salvage_map(data)


def test_partial_port_successor_preserves_remaining_legacy_work() -> None:
    data = deepcopy(load_salvage_map())
    legacy = _entry(data, 63)
    legacy["classification"] = "SUPERSEDED"
    legacy["superseded_by_pr"] = 71
    legacy["blockers"] = []

    with pytest.raises(SalvageMapError, match="PARTIAL_PORT successor requires legacy PR #63"):
        validate_salvage_map(data)


def test_successor_candidate_must_be_rebuilt_on_current_main() -> None:
    data = deepcopy(load_salvage_map())
    candidate = _entry(data, 70)
    candidate["base_sha"] = "2348fd74e63870f707bb8ce7a9f96a0c4d83d916"

    with pytest.raises(SalvageMapError, match="successor PR #70 must be rebuilt"):
        validate_salvage_map(data)


def test_successor_candidate_cannot_be_rejected_or_superseded() -> None:
    data = deepcopy(load_salvage_map())
    candidate = _entry(data, 71)
    candidate["classification"] = "REJECT"
    candidate["release_disposition"] = "DO_NOT_MERGE_INVALID_TEST"

    with pytest.raises(SalvageMapError, match="successor PR #71 must remain an active release candidate"):
        validate_salvage_map(data)


def test_consumed_verification_branch_cannot_be_reactivated_as_parallel_truth() -> None:
    data = deepcopy(load_salvage_map())
    consumed = _entry(data, 72)
    consumed["classification"] = "PORTABLE"
    consumed["release_disposition"] = "HOLD_INVALID_PARALLEL_TRUTH"
    consumed["blockers"] = ["INVALID_PARALLEL_TRUTH"]

    with pytest.raises(SalvageMapError, match="FULL_PORT successor requires legacy PR #72"):
        validate_salvage_map(data)


def test_digital_salvage_map_cannot_claim_physical_validation() -> None:
    data = deepcopy(load_salvage_map())
    _entry(data, 71)["physical_validation_status"] = "VALIDATED"

    with pytest.raises(SalvageMapError, match="physical validation"):
        validate_salvage_map(data)


def test_released_repair_cannot_be_reclassified_as_legacy_work() -> None:
    data = deepcopy(load_salvage_map())
    released = data["released_and_skipped"]
    entries = data["entries"]
    assert isinstance(released, list) and isinstance(entries, list)
    released_pr = released[0]
    assert isinstance(released_pr, dict)
    entries.append(
        {
            "pr": released_pr["pr"],
            "title": "invalid duplicate release",
            "head_ref": "invalid",
            "head_sha": released_pr["head_sha"],
            "base_ref": "main",
            "base_sha": data["reconstructed_main_sha"],
            "classification": "MERGEABLE",
            "release_disposition": "ELIGIBLE_FOR_RELEASE",
            "unique_work": ["INVALID"],
            "source_bindings": [
                {
                    "producer": "INVALID",
                    "geometry_dependency": False,
                    "observed_sha": data["reconstructed_main_sha"],
                    "required_sha": data["reconstructed_main_sha"],
                    "status": "CURRENT_EXACT_BASE",
                    "digest_status": "INVALID_TEST_BINDING",
                    "release_safe": True,
                }
            ],
            "exact_head_ci": {
                "run_id": 1,
                "conclusion": "SUCCESS",
                "attribution": "INVALID",
            },
            "independent_review": "APPROVED",
            "physical_validation_status": "NOT_CLAIMED",
            "blockers": [],
        }
    )

    with pytest.raises(SalvageMapError, match="released PR"):
        validate_salvage_map(data)
