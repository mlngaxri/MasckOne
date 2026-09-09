from masck_one.integration_contract import integration_contract_manifest


def test_integration_contract_is_navigation_not_physical_authority() -> None:
    manifest = integration_contract_manifest()

    assert manifest["schema"] == "MASCK_ONE_AUTONOMOUS_SPRINT_INTEGRATION_CONTRACT_V1"
    assert manifest["live_github_supersedes_snapshot"] is True
    assert manifest["released_main_sha"] == "42fa11818184cde998c6df25d7c46d4fb0e4c3eb"
    assert "physical" in manifest["evidence_firewall"].lower()


def test_integration_lane_does_not_claim_subsystem_implementation() -> None:
    manifest = integration_contract_manifest()
    integration_paths = set(manifest["integration_lane"]["owns"])

    forbidden_exact = {
        "src/masck_one/realized_waste_cartridge.py",
        "src/masck_one/retention_load_path.py",
        "src/masck_one/primary_control_haptic.py",
        "src/masck_one/warm_cool_package.py",
        "src/masck_one/rear_service_skin.py",
    }
    assert integration_paths.isdisjoint(forbidden_exact)
    assert all("treatment_" not in path for path in integration_paths)
    assert all("structural_frame_" not in path for path in integration_paths)
    assert all("wet_electrical_" not in path for path in integration_paths)
    assert all("exterior_" not in path for path in integration_paths)


def test_live_owner_heads_and_paths_are_pinned() -> None:
    lanes = integration_contract_manifest()["owner_lanes"]

    assert lanes["structural_frame"]["pr"] == 117
    assert lanes["structural_frame"]["head_sha"] == "2d5ace19e2f87a8bd92f4620d8e6b225ba3826be"
    assert lanes["treatment_mechanics"]["pr"] == 135
    assert lanes["treatment_mechanics"]["head_sha"] == "ee02c102ab6122123d805e4e3aa74163078b96bf"
    assert lanes["primary_hmi"]["head_sha"] == "5c2b5f030f8d205e108a828fed53d43293f518f4"
    assert lanes["exterior"]["head_sha"] == "152312fe6eced419eef4e1e58c33df09fd0710ea"
    assert lanes["wet_dry_source_graph"]["head_sha"] == "484f25e0f04bba9aa27a598155dcf6d701b2a2ef"
    assert lanes["warm_cool_package"]["head_sha"] == "61b4da28f8fbd45fc1a9885db4366f8506d2043e"
    assert lanes["waste_cartridge"]["upstream_pr"] == 115
    assert lanes["retention_quick_release"]["upstream_pr"] == 92

    for lane in lanes.values():
        assert lane["implementation_paths"]
