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
        "src/masck_one/cartridge_fusion_handoff.py",
        "src/masck_one/mechanical_interface_graph.py",
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
    assert lanes["treatment_mechanics"]["head_sha"] == "43c3866eea56801696068ad4e417d5b21498682d"
    assert lanes["primary_hmi"]["head_sha"] == "5c2b5f030f8d205e108a828fed53d43293f518f4"
    assert lanes["exterior"]["head_sha"] == "152312fe6eced419eef4e1e58c33df09fd0710ea"
    assert lanes["wet_dry_source_graph"]["head_sha"] == "484f25e0f04bba9aa27a598155dcf6d701b2a2ef"
    assert lanes["warm_cool_package"]["head_sha"] == "61b4da28f8fbd45fc1a9885db4366f8506d2043e"

    assert lanes["waste_cartridge"]["pr"] == 140
    assert lanes["waste_cartridge"]["head_sha"] == "7bf392eb2c5fb7e6b2c3a23c86bbbdfb1cc7f94f"
    assert lanes["waste_cartridge"]["supersedes_pr"] == 115
    assert "src/masck_one/cartridge_fusion_handoff.py" in lanes["waste_cartridge"]["implementation_paths"]

    assert lanes["retention_quick_release"]["pr"] == 141
    assert lanes["retention_quick_release"]["head_sha"] == "331c2ad246cffe3828feb9f4f1f9c067d4d99d24"
    assert lanes["retention_quick_release"]["stacked_on_pr"] == 117
    assert lanes["retention_quick_release"]["donor_pr"] == 92
    assert lanes["retention_quick_release"]["shared_owner_binding_paths"] == [
        "src/masck_one/structural_frame_retention_roots.py"
    ]

    for lane in lanes.values():
        assert lane["implementation_paths"]
