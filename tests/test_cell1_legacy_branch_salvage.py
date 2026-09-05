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


def test_live_salvage_map_is_internally_release_safe() -> None:
    data = load_salvage_map()
    validate_salvage_map(data)

    assert data["reconstructed_main_sha"] == "5fce2a43a34d8be49256677a35af60c906dc1653"
    assert _entry(data, 62)["classification"] == "PORTABLE"
    assert _entry(data, 63)["classification"] == "PORTABLE"
    assert _entry(data, 64)["classification"] == "PORTABLE"
    assert _entry(data, 65)["classification"] == "REJECT"
    assert _entry(data, 66)["classification"] == "SUPERSEDED"
    assert _entry(data, 68)["classification"] == "PORTABLE"


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
        if isinstance(item, dict) and item.get("producer") == "MANUAL_A_PR_63_V2_INTEGRATION_SOURCE"
    )
    manual_a["digest_status"] = "OLD_DIGEST_ACCEPTED"

    with pytest.raises(SalvageMapError, match="digest recomputation"):
        validate_salvage_map(data)


def test_digital_salvage_map_cannot_claim_physical_validation() -> None:
    data = deepcopy(load_salvage_map())
    _entry(data, 63)["physical_validation_status"] = "VALIDATED"

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
            "source_bindings": [],
            "exact_head_ci": {"run_id": 1, "conclusion": "SUCCESS", "attribution": "INVALID"},
            "independent_review": "APPROVED",
            "physical_validation_status": "NOT_CLAIMED",
            "blockers": [],
        }
    )

    with pytest.raises(SalvageMapError, match="released PR"):
        validate_salvage_map(data)
