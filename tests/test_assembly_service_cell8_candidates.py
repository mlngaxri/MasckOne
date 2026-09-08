from __future__ import annotations

import re

from masck_one import assembly_service_inventory as asi


def test_current_inventory_consumes_cell8_guard_parts_as_candidate_only() -> None:
    inventory = asi.build_current_assembly_service_inventory()
    parts = {part["part_id"]: part for part in inventory.candidate_parts}

    assert tuple(parts) == (
        "CELL8_LEFT_ADJUSTMENT_U_SHROUD",
        "CELL8_RIGHT_ADJUSTMENT_U_SHROUD",
        "CELL8_RIGHT_QUICK_RELEASE_U_SHROUD",
    )
    for part in parts.values():
        assert part["producer_pr"] == 109
        assert part["producer_head_sha"] == asi.CELL8_RETENTION_GUARD_HEAD
        assert part["producer_previous_head_sha"] == asi.CELL8_RETENTION_GUARD_PREVIOUS_HEAD
        assert part["producer_rebind_disposition"] == asi.CELL8_REBIND_DISPOSITION
        assert part["producer_source_blob_sha"] == asi.CELL8_RETENTION_GUARD_BLOB
        assert part["authority_status"] == asi.CELL8_CANDIDATE_STATUS
        assert part["semantic_role"] == "PHYSICAL_MATERIAL_CANDIDATE"
        assert part["development_assembly_included"] is False
        assert part["positive_attachment_realized"] is False
        assert part["cell5_dfm_part_family_present"] is False
        assert part["assembly_stage"] is None
        assert part["physical_validation_eligible"] is False


def test_cell8_candidate_factory_installation_motions_are_exact_but_not_service_closure() -> None:
    inventory = asi.build_current_assembly_service_inventory()
    motions = {
        row["part_id"]: row
        for row in inventory.manifest()["candidate_factory_installation_motion_evidence"]
    }

    assert motions["CELL8_LEFT_ADJUSTMENT_U_SHROUD"]["translation_world_mm"] == [-22.0, 0.0, 0.0]
    assert motions["CELL8_LEFT_ADJUSTMENT_U_SHROUD"]["sweep_bounds_world_mm"]["x"] == [-87.5, -54.5]
    assert motions["CELL8_RIGHT_ADJUSTMENT_U_SHROUD"]["translation_world_mm"] == [22.0, 0.0, 0.0]
    assert motions["CELL8_RIGHT_ADJUSTMENT_U_SHROUD"]["sweep_bounds_world_mm"]["x"] == [54.5, 87.5]
    assert motions["CELL8_RIGHT_QUICK_RELEASE_U_SHROUD"]["translation_world_mm"] == [35.0, 0.0, 0.0]
    assert motions["CELL8_RIGHT_QUICK_RELEASE_U_SHROUD"]["sweep_bounds_world_mm"]["x"] == [35.0, 90.0]

    for motion in motions.values():
        assert motion["motion_evidence"] == "EXACT_CLOSED_INTERVAL_PURE_X_BREP_SWEEP_NOT_SAMPLED_WAYPOINTS"
        assert motion["reference_sweep_is_product_material"] is False
        assert motion["wearer_present"] is False
        assert motion["powered"] is False

    findings = inventory.manifest()["reconciliation_findings"]
    assert "POSITIVE_ATTACHMENT" in findings["cell8_guard_factory_motion_disposition"]
    assert "WHOLE_HEAD_REMOVAL_REMAIN_OPEN" in findings["cell8_guard_factory_motion_disposition"]
    assert inventory.manifest()["digital_mvp_service_ready"] is False


def test_cell8_candidate_source_contract_is_exact_and_deterministic() -> None:
    first = asi.build_current_assembly_service_inventory().manifest()
    second = asi.build_current_assembly_service_inventory().manifest()
    assert first == second
    assert re.fullmatch(r"[0-9a-f]{64}", first["inventory_sha256"])

    source = first["source_contracts"]["cell8_retention_hazard_guards"]
    assert source == {
        "pr_number": 109,
        "head_sha": "fb586cc1ea1cde92526417593f9e5aa990d2ae4f",
        "previous_head_sha": "a27757eb4eda54a18b3d89db70f9534e492e588f",
        "rebind_disposition": asi.CELL8_REBIND_DISPOSITION,
        "source_path": "src/masck_one/retention_hazard_guards.py",
        "source_blob_sha": "b497e9154067cef9ee24da4d421ea6c7861c348e",
        "candidate_interface_sha256": "ce2618f872e01733a2031085ccb402bc40b61ae1e9b427456c0da049bcd72061",
        "bound_cell3_retention_pr": 92,
        "bound_cell3_retention_head_sha": "abb806a8e15a1557c8b5a4c754af1bfeea8b6d70",
        "bound_right_release_pr": 71,
        "bound_right_release_head_sha": "0b5a619c6cea344038b0e8b8cc10a50e3d193390",
        "authority_status": asi.CELL8_CANDIDATE_STATUS,
    }


def test_cell3_retention_service_domains_are_rebound_to_semantic_repair_head() -> None:
    inventory = asi.build_current_assembly_service_inventory()
    retention_domains = [
        domain
        for domain in inventory.service_domains
        if domain.candidate is not None and domain.candidate.pr_number == 92
    ]
    assert len(retention_domains) == 2
    assert all(domain.candidate is not None for domain in retention_domains)
    assert all(
        domain.candidate.head_sha == "abb806a8e15a1557c8b5a4c754af1bfeea8b6d70"
        for domain in retention_domains
        if domain.candidate is not None
    )
    finding = inventory.manifest()["reconciliation_findings"]["cell3_retention_service_head_rebind"]
    assert finding["previous_head_sha"] == "e332426526ec4ceb885ad9d35250a89d78b6066c"
    assert finding["current_head_sha"] == "abb806a8e15a1557c8b5a4c754af1bfeea8b6d70"
    assert "SERVICE_BREP_CONSTRUCTION_UNCHANGED" in finding["disposition"]
