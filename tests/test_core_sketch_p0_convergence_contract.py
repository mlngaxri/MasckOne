import json
from pathlib import Path


CONTRACT_PATH = Path(__file__).parents[1] / "docs" / "contracts" / "core_sketch_p0_convergence_v1.json"


def load_contract():
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def test_contract_is_explicitly_non_engineering_authority():
    data = load_contract()
    assert data["status"] == "CORE_SKETCH_CONCEPT_CONTRACT_NON_ENGINEERING_AUTHORITY"
    boundary = data["authority_boundary"]
    assert boundary["may_define_product_logic"] is True
    assert boundary["may_claim_physical_validation"] is False
    assert boundary["may_override_engineering_authority"] is False
    assert boundary["may_override_protected_anatomy"] is False


def test_contract_consumes_existing_backlog_contract_ids_instead_of_competing_with_them():
    data = load_contract()
    assert data["canonical_backlog_contracts"] == {
        "CS-015": "REQUIRED_REGION_COMPLETION",
        "CS-016": "PREPARED_SESSION_VALIDITY_INTERRUPTION",
        "CS-017": "PRODUCT_PRESERVATION_DOCK_SESSION_STORAGE",
        "CS-018": "ALL_CONTACT_SUPPORT_FILM_PRESERVING_TRANSITION",
    }
    ids = {item["id"] for item in data["p0_items"]}
    assert {"CS-015", "CS-016", "CS-017", "CS-018"} <= ids


def test_constraint_snapshot_records_current_reconciled_mass_set_but_is_not_release_binding():
    data = load_contract()
    snapshot = data["authority_snapshot"]
    assert snapshot["purpose"] == "CONSTRAINT_RECONCILIATION_ONLY_NOT_A_RELEASE_BINDING"
    assert snapshot["dry_target_max_g"] == 215.0
    assert snapshot["loaded_absolute_max_g"] == 255.0
    assert snapshot["cg_z_max_mm"] == 27.9
    assert snapshot["pitch_torque_max_Nm"] == 0.070
    assert snapshot["refresh_before_engineering_action"] is True
    assert "CURRENT_AUTHORITY_CONSTRAINTS_MUST_BE_REFRESHED_BEFORE_ENGINEERING_ACTION" in data["invariants"]


def test_complete_routine_cannot_hide_blocking_region_states():
    data = load_contract()
    blocking = set(data["blocking_completion_states"])
    assert {"UNREACHABLE", "UNSUPPORTED", "INTERRUPTED", "UNKNOWN"} <= blocking
    assert "COMPLETE" not in blocking
    assert "REQUIRED_REGION_BLOCKING_STATE_PREVENTS_STAGE_COMPLETE" in data["invariants"]


def test_contact_contract_covers_all_face_facing_classes_and_blocks_unresolved_occlusion():
    data = load_contract()
    expected = {
        "PERIMETER_SEAL",
        "SUPPORT_PAD",
        "RETENTION_REACTION_INTERFACE",
        "TREATMENT_ISLAND",
        "THERMAL_CONTACT",
        "OPTICAL_FACE_ADJACENT_CARRIER",
        "FLUID_DISTRIBUTION_INTERFACE",
        "OTHER_FACE_FACING_SUPPORT",
    }
    assert expected == set(data["face_contact_classes"])
    rules = data["occlusion_rules"]
    assert rules["required_region_occluded_at_leave_on_requires_strategy"] is True
    assert rules["persistent_unresolved_occlusion_blocks_complete"] is True
    assert rules["emergency_release_overrides_film_preservation"] is True
    assert len(rules["allowed_strategies"]) >= 4


def test_ready_is_bound_to_real_session_resources_and_offline_data():
    data = load_contract()
    bindings = set(data["prepared_session_required_bindings"])
    required = {
        "ROUTINE_ID_VERSION",
        "REQUIRED_STAGES",
        "PRODUCT_IDENTITIES",
        "PRODUCT_EVIDENCE_STATE",
        "PREPARED_DOSE_STATE",
        "CHANGEOVER_CONTAMINATION_STATE",
        "WATER_SUFFICIENCY",
        "WASTE_CAPACITY",
        "ENERGY_SUFFICIENCY",
        "SERVICE_CLEANING_STATE",
        "FAULT_STATE",
        "LOCAL_OFFLINE_EXECUTION_DATA",
    }
    assert required <= bindings
    assert data["network_loss_alone_invalidates_ready"] is False
    assert "INVALID_PREPARED_SESSION_PREVENTS_READY" in data["invariants"]


def test_product_identity_characterisation_compatibility_contamination_and_validation_are_separate():
    data = load_contract()
    assert data["product_truth_dimensions"] == [
        "IDENTITY",
        "PHYSICAL_CHARACTERISATION",
        "COMPATIBILITY",
        "CONTAMINATION_STATE",
        "APPLICATION_VALIDATION",
    ]
    assert set(data["product_evidence_states"]) == {
        "KNOWN",
        "CHARACTERISED",
        "VALIDATED",
        "RESTRICTED_OR_UNSUPPORTED",
    }
    assert data["community_data_may_auto_promote_to_validated"] is False
    assert "UNSUPPORTED_REQUIRED_PRODUCT_PREVENTS_ROUTINE_COMPLETE" in data["invariants"]


def test_resource_envelope_is_whole_routine_not_cleanser_only():
    data = load_contract()
    variables = set(data["resource_variables"])
    required = {
        "V_WATER",
        "V_CLEANSER",
        "V_LEAVEON_I",
        "V_MOIST",
        "V_SPF",
        "V_PURGE",
        "V_RECOVERED",
        "V_RESIDUAL",
        "M_LOADED",
        "CG_LOADED",
        "TAU_HEAD",
        "E_ELECTRICAL",
        "E_THERMAL",
        "T_ROUTINE",
        "N_BULK_SLOTS",
        "V_SESSION_STORAGE",
        "V_WASTE_REQUIRED",
    }
    assert required <= variables
    assert data["planning_scenarios"] == ["MINIMUM_SUPPORTED", "NORMAL_PM", "DEMANDING_AM"]


def test_shared_interfaces_have_one_canonical_writing_owner():
    data = load_contract()
    lanes = set(data["top_level_lanes"])
    owners = data["shared_contract_writing_owners"]
    assert owners
    assert len(owners) == len(set(owners))
    assert all(owner in lanes for owner in owners.values())
    assert owners["STAGE_BY_REGION_COMPLETION"] == "L1"
    assert owners["PREPARED_SESSION_VALIDITY"] == "L4"
    assert owners["COMPLETE_ROUTINE_RESOURCE_ENVELOPE"] == "L5"
    assert "SHARED_INTERFACE_HAS_ONE_CANONICAL_WRITING_OWNER" in data["invariants"]


def test_physical_evidence_firewall_and_p0_routing_remain_explicit():
    data = load_contract()
    assert "DOC_OR_DIGITAL_EVIDENCE_CANNOT_PROMOTE_PHYSICAL_VALIDATION" in data["invariants"]
    assert "GREEN_SUBSYSTEM_CI_CANNOT_CLOSE_P0_PHYSICAL_PROOF" in data["invariants"]
    p0 = data["p0_items"]
    assert p0
    assert all(item["lane"] in data["top_level_lanes"] for item in p0)
    assert any("BENCH" in item["evidence"] for item in p0)
    assert any("HUMAN" in item["evidence"] for item in p0)
    assert any("REG_CLAIM" in item["evidence"] for item in p0)
