from copy import deepcopy

import pytest

from masck_one import integration_contract
from masck_one.integration_contract import (
    IntegrationContractError,
    integration_contract_manifest,
)


def test_contract_is_edit_ownership_not_physical_authority() -> None:
    manifest = integration_contract_manifest()

    assert manifest["schema"] == "MASCK_ONE_SPRINT_EDIT_OWNERSHIP_V2"
    assert manifest["live_github_is_authoritative_for_pr_and_branch_state"] is True
    assert "physical" in manifest["evidence_firewall"].lower()


def test_no_volatile_pull_request_state_is_compiled_into_the_contract() -> None:
    """Live PR/branch heads belong to GitHub, not to a Python literal.

    A copy pinned here goes stale within hours and is emitted into
    build_report.json, which would ship false provenance in released evidence.
    """

    manifest = integration_contract_manifest()
    forbidden = {"pr", "head_sha", "base_sha", "stacked_on_pr", "donor_pr", "supersedes_pr"}

    for name, lane in manifest["owner_lanes"].items():
        leaked = forbidden.intersection(lane)
        assert not leaked, f"lane {name} pins volatile GitHub state: {sorted(leaked)}"


def test_only_immutable_merged_commits_may_be_pinned() -> None:
    manifest = integration_contract_manifest()
    pinned = {"released_main_sha"}
    for lane in manifest["owner_lanes"].values():
        pinned.update(field for field in lane if field.endswith("_sha"))

    # Every retained SHA field must name an already-merged release point.
    assert pinned == {"released_main_sha", "released_merge_sha"}


def test_integration_lane_does_not_claim_subsystem_implementation() -> None:
    manifest = integration_contract_manifest()
    integration_paths = set(manifest["integration_lane"]["owns"])

    forbidden_exact = {
        "src/masck_one/realized_waste_cartridge.py",
        "src/masck_one/cartridge_fusion_handoff.py",
        "src/masck_one/mechanical_interface_graph.py",
        "src/masck_one/primary_control_haptic.py",
        "src/masck_one/warm_cool_package.py",
        "src/masck_one/rear_service_skin.py",
    }
    assert integration_paths.isdisjoint(forbidden_exact)
    for prefix in ("treatment_", "structural_frame_", "wet_electrical_", "exterior_"):
        assert all(prefix not in path for path in integration_paths)


def test_every_lane_declares_implementation_paths() -> None:
    for name, lane in integration_contract_manifest()["owner_lanes"].items():
        assert lane["implementation_paths"], f"lane {name} owns nothing"


def test_declared_lane_dependencies_resolve() -> None:
    manifest = integration_contract_manifest()
    lanes = manifest["owner_lanes"]

    # These two lanes stack on the structural frame; that dependency is the
    # program's critical path and must stay explicit.
    assert lanes["treatment_mechanics"]["depends_on_lane"] == "structural_frame"
    assert lanes["retention_quick_release"]["depends_on_lane"] == "structural_frame"

    for name, lane in lanes.items():
        dependency = lane.get("depends_on_lane")
        assert dependency is None or dependency in lanes, f"lane {name} dangling dependency"


def test_subsystem_lanes_claim_disjoint_implementation_paths() -> None:
    manifest = integration_contract_manifest()
    release_lanes = integration_contract._RELEASE_INFRASTRUCTURE_LANES

    owner_of: dict[str, str] = {}
    for name, lane in manifest["owner_lanes"].items():
        if name in release_lanes:
            continue
        for path in lane["implementation_paths"]:
            assert path not in owner_of, (
                f"{path} claimed by both {owner_of[path]} and {name}"
            )
            owner_of[path] = name


def test_colliding_lane_ownership_fails_closed(monkeypatch) -> None:
    """A path claimed by two subsystem lanes is a silent-overwrite hazard."""

    contract = deepcopy(integration_contract._CONTRACT)
    contract["owner_lanes"]["primary_hmi"]["implementation_paths"] = [
        "src/masck_one/warm_cool_package.py"
    ]
    monkeypatch.setattr(integration_contract, "_CONTRACT", contract)

    with pytest.raises(IntegrationContractError, match="claimed by both"):
        integration_contract_manifest()


def test_integration_lane_claiming_subsystem_paths_fails_closed(monkeypatch) -> None:
    contract = deepcopy(integration_contract._CONTRACT)
    contract["integration_lane"]["owns"] = list(contract["integration_lane"]["owns"]) + [
        "src/masck_one/warm_cool_package.py"
    ]
    monkeypatch.setattr(integration_contract, "_CONTRACT", contract)

    with pytest.raises(IntegrationContractError, match="claims subsystem implementation"):
        integration_contract_manifest()


def test_dangling_lane_dependency_fails_closed(monkeypatch) -> None:
    contract = deepcopy(integration_contract._CONTRACT)
    contract["owner_lanes"]["primary_hmi"]["depends_on_lane"] = "lane_that_does_not_exist"
    monkeypatch.setattr(integration_contract, "_CONTRACT", contract)

    with pytest.raises(IntegrationContractError, match="depends on unknown lane"):
        integration_contract_manifest()


def test_malformed_pinned_sha_fails_closed(monkeypatch) -> None:
    contract = deepcopy(integration_contract._CONTRACT)
    contract["owner_lanes"]["brand_identity"]["released_merge_sha"] = "not-a-sha"
    monkeypatch.setattr(integration_contract, "_CONTRACT", contract)

    with pytest.raises(IntegrationContractError, match="malformed released_merge_sha"):
        integration_contract_manifest()
