from __future__ import annotations

import re

import pytest

from masck_one import assembly_service_inventory as asi


def test_current_inventory_reconciles_released_instances_dfm_parts_and_service_domains() -> None:
    inventory = asi.build_current_assembly_service_inventory()

    assert len(inventory.released_instances) == 14
    assert len(inventory.dfm_donor_parts) == 47
    assert len(inventory.service_domains) == 14
    assert inventory.physical_validation_eligible is False
    assert inventory.evidence_status == asi.EVIDENCE_STATUS

    manifest = inventory.manifest()
    assert manifest["schema"] == asi.SCHEMA
    assert manifest["source_main_sha"] == asi.SOURCE_MAIN_SHA
    assert manifest["authority_blob_sha"] == asi.AUTHORITY_BLOB_SHA
    assert manifest["coordinate_frame_id"] == asi.WORLD_FRAME_ID
    assert re.fullmatch(r"[0-9a-f]{64}", manifest["inventory_sha256"])


def test_current_main_reference_material_partition_gap_is_explicit_and_exact() -> None:
    inventory = asi.build_current_assembly_service_inventory()
    assert inventory.current_reference_instances_in_development_assembly == (
        "MASCK_ONE-ASM-ACTUATOR-REFERENCE-01",
        "MASCK_ONE-ASM-ACTUATOR-REFERENCE-02",
        "MASCK_ONE-ASM-ACTUATOR-REFERENCE-03",
        "MASCK_ONE-ASM-ACTUATOR-REFERENCE-04",
        "MASCK_ONE-ASM-BATTERY-REFERENCE",
        "MASCK_ONE-ASM-NASAL-LOBE-REFERENCE",
        "MASCK_ONE-ASM-WATER-REFERENCE",
    )

    by_name = {item.source_name: item for item in inventory.released_instances}
    assert by_name["rigid_shell"].semantic_role == asi.ROLE_PHYSICAL_MATERIAL
    assert by_name["rigid_shell"].development_assembly_included is True
    assert by_name["waste_cartridge_envelope"].semantic_role == asi.ROLE_PACKAGE_REFERENCE
    assert by_name["waste_cartridge_envelope"].development_assembly_included is False
    assert all(
        item.development_assembly_included is False
        for item in inventory.released_instances
        if item.semantic_role == asi.ROLE_PROTECTED_KEEPOUT
    )


def test_reconciliation_exposes_three_component_registry_pumps_missing_from_dfm_donor() -> None:
    inventory = asi.build_current_assembly_service_inventory()
    findings = inventory.manifest()["reconciliation_findings"]
    assert findings["cell5_dfm_missing_component_registry_pump_part_families"] == [
        "MASCK_ONE-COMP-CLEANSER-PUMP",
        "MASCK_ONE-COMP-WASTE-PUMP",
        "MASCK_ONE-COMP-WATER-PUMP",
    ]

    donor_ids = {item.part_id for item in inventory.dfm_donor_parts}
    assert "MASCK_ONE-DFM-CLEANSER-PUMP" not in donor_ids
    assert "MASCK_ONE-DFM-WASTE-PUMP" not in donor_ids
    assert "MASCK_ONE-DFM-WATER-PUMP" not in donor_ids


def test_all_current_service_domains_fail_closed_without_released_motion_producer() -> None:
    inventory = asi.build_current_assembly_service_inventory()
    assert inventory.missing_released_motion_domain_ids == tuple(
        sorted(item.domain_id for item in inventory.service_domains)
    )
    assert all(
        item.released_motion_status == asi.MOTION_MISSING_RELEASED_PRODUCER
        for item in inventory.service_domains
    )
    assert inventory.manifest()["digital_mvp_service_ready"] is False


def test_candidate_motion_evidence_never_promotes_to_release_authority() -> None:
    inventory = asi.build_current_assembly_service_inventory()
    by_id = {item.domain_id: item for item in inventory.service_domains}

    quick_release = by_id["MASCK_ONE-SERVICE-RIGHT-EMERGENCY-RELEASE"]
    assert quick_release.candidate_motion_status == asi.MOTION_CANDIDATE_EXACT
    assert quick_release.candidate is not None
    assert quick_release.candidate.pr_number == 71
    assert quick_release.candidate.source_blob_sha == "d9be83d27deef9afd7e98dcbb874ebed1d1ab360"
    assert quick_release.candidate.manifest()["authority_status"] == "UNMERGED_CANDIDATE_NOT_RELEASE_AUTHORITY"

    cleanser = by_id["MASCK_ONE-SERVICE-CLEANSER-REFILL-AND-MODULE-REMOVAL"]
    assert cleanser.candidate_motion_status == asi.MOTION_CANDIDATE_CONSERVATIVE
    assert cleanser.candidate is not None
    assert cleanser.candidate.pr_number == 80
    assert cleanser.candidate.source_blob_sha == "1944487af9baa1c9fe27004eceed52eeb8a08167"

    for domain_id in (
        "MASCK_ONE-SERVICE-WATER-PUMP-REPLACEMENT",
        "MASCK_ONE-SERVICE-CLEANSER-PUMP-REPLACEMENT",
        "MASCK_ONE-SERVICE-WASTE-PUMP-REPLACEMENT",
        "MASCK_ONE-SERVICE-PASSIVE-BACKFLOW-REPLACEMENT",
    ):
        assert by_id[domain_id].candidate_motion_status == asi.MOTION_CANDIDATE_STATIONARY


def test_source_contracts_keep_stale_donors_and_current_candidate_separate() -> None:
    inventory = asi.build_current_assembly_service_inventory()
    contracts = inventory.manifest()["source_contracts"]

    registry = contracts["cell1_component_registry"]
    assert registry["pr_number"] == 74
    assert registry["head_sha"] == asi.CELL1_COMPONENT_REGISTRY_HEAD
    assert registry["authority_status"] == "STALE_UNMERGED_DONOR_NOT_RELEASE_AUTHORITY"

    dfm = contracts["cell5_dfm_part_architecture"]
    assert dfm["pr_number"] == 77
    assert dfm["head_sha"] == asi.CELL5_DFM_HEAD
    assert dfm["authority_status"] == "STALE_UNMERGED_DONOR_NOT_RELEASE_AUTHORITY"

    boundary = contracts["cell1_current_main_assembly_boundary"]
    assert boundary["pr_number"] == 101
    assert boundary["head_sha"] == asi.CELL1_ASSEMBLY_BOUNDARY_HEAD
    assert boundary["authority_status"] == "CURRENT_MAIN_BOUND_CANDIDATE_NOT_RELEASE_AUTHORITY"


def test_manifest_is_deterministic() -> None:
    first = asi.build_current_assembly_service_inventory().manifest()
    second = asi.build_current_assembly_service_inventory().manifest()
    assert first == second


def test_hostile_bad_candidate_head_fails_closed() -> None:
    with pytest.raises(asi.AssemblyServiceInventoryError, match="candidate head"):
        asi.CandidateBinding(71, "not-a-sha", "EXACT_SWEEP")


def test_hostile_partial_candidate_source_binding_fails_closed() -> None:
    with pytest.raises(asi.AssemblyServiceInventoryError, match="supplied together"):
        asi.CandidateBinding(
            71,
            "0b5a619c6cea344038b0e8b8cc10a50e3d193390",
            "EXACT_SWEEP",
            source_path="src/masck_one/right_quick_release_sweep.py",
        )


def test_hostile_bool_assembly_stage_fails_closed() -> None:
    with pytest.raises(asi.AssemblyServiceInventoryError, match="assembly stage"):
        asi.DfmDonorPart(
            "MASCK_ONE-DFM-TEST",
            True,
            asi.SERVICE_NONUSER_FIXED,
            asi.PATH_NOT_APPLICABLE,
            asi.M_UNRESOLVED_REQUIRED,
        )


def test_hostile_removable_part_without_service_path_fails_closed() -> None:
    with pytest.raises(asi.AssemblyServiceInventoryError, match="require an explicit service path"):
        asi.DfmDonorPart(
            "MASCK_ONE-DFM-TEST",
            1,
            asi.SERVICE_USER_REMOVABLE,
            asi.PATH_NOT_APPLICABLE,
            asi.M_UNRESOLVED_REQUIRED,
        )


def test_hostile_candidate_cannot_claim_released_motion() -> None:
    with pytest.raises(asi.AssemblyServiceInventoryError, match="no accepted complete service-motion"):
        asi.ServiceDomain(
            "MASCK_ONE-SERVICE-TEST",
            "CELL_15_INTEGRATION",
            ("MASCK_ONE-DFM-TEST",),
            asi.MOTION_CANDIDATE_EXACT,
            asi.MOTION_NO_CANDIDATE,
            "test blocker",
        )


def test_hostile_moved_released_source_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    path = "src/masck_one/model.py"
    monkeypatch.setitem(asi.SOURCE_GIT_BLOB_BY_PATH, path, "0" * 40)
    with pytest.raises(asi.AssemblyServiceInventoryError, match="released source moved"):
        asi.validate_released_source_bindings()
