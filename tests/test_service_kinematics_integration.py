from __future__ import annotations

import json
from pathlib import Path

import pytest

from masck_one.mechanism_state import MechanismState, OperatingMode
from masck_one.service_kinematics_integration import (
    CANDIDATE_SOURCES,
    DIGITAL_ONLY,
    EXPECTED_ABSENT_CURRENT_MAIN_PATHS,
    MOTIONS,
    RELEASED_SOURCE_BLOBS,
    SCHEMA,
    SOURCE_MAIN_SHA,
    CandidateClass,
    ServiceDomain,
    ServiceKinematicsError,
    WholeProductServiceState,
    build_whole_product_service_kinematics,
    export_service_kinematics_manifest,
)


def test_service_integration_binds_released_main_sources_and_absent_producers():
    integration = build_whole_product_service_kinematics()
    assert integration.binding.source_main_sha == SOURCE_MAIN_SHA
    assert integration.binding.released_source_blobs == RELEASED_SOURCE_BLOBS
    assert integration.binding.world_frame_id == "MASCK_ONE_AUTHORITY_WORLD_MM"
    assert all(len(blob) == 40 for _, blob in RELEASED_SOURCE_BLOBS)
    root = Path(__file__).resolve().parents[1]
    assert all(not (root / relative).exists() for relative in EXPECTED_ABSENT_CURRENT_MAIN_PATHS)


def test_registry_covers_every_objective_domain_once_and_all_current_motion_is_blocked():
    integration = build_whole_product_service_kinematics()
    assert integration.motions == MOTIONS
    assert tuple(item.domain for item in integration.motions) == tuple(ServiceDomain)
    assert len(integration.motions) == 7
    assert integration.blocked_motion_count == 7
    assert not any(item.current_main_motion_geometry_available for item in integration.motions)

    emergency = integration.motion_for(ServiceDomain.EMERGENCY_RELEASE)
    assert emergency.released_contract_available is True
    assert emergency.routine_service is False
    assert "STATE_SEMANTICS" in emergency.current_main_maturity

    cartridge = integration.motion_for(ServiceDomain.WASTE_CARTRIDGE)
    assert cartridge.source_interface_id == "WASTE-CARTRIDGE-SERVICE-TRAJECTORY-I27"
    assert "EXPLICITLY_UNRESOLVED" in cartridge.current_main_maturity

    battery = integration.motion_for(ServiceDomain.BATTERY_DOOR)
    cover = integration.motion_for(ServiceDomain.SERVICE_COVER)
    assert battery.released_contract_available is False
    assert cover.released_contract_available is False
    assert "NO_RELEASED_DOOR" in battery.current_main_maturity
    assert "NO_RELEASED_REAR_SERVICE_COVER" in cover.current_main_maturity


def test_candidate_and_legacy_motion_sources_are_provenance_only():
    integration = build_whole_product_service_kinematics()
    assert integration.candidates == CANDIDATE_SOURCES
    assert {item.pr_number for item in integration.candidates} == {63, 64, 71, 75, 78, 80, 83, 87, 89}
    assert all(item.geometry_consumed is False for item in integration.candidates)
    assert all(len(item.head_sha) == 40 and len(item.source_blob_sha) == 40 for item in integration.candidates)
    assert {item.source_class for item in integration.candidates} == {
        CandidateClass.NONAUTHORITATIVE_CANDIDATE,
        CandidateClass.STACKED_NONAUTHORITATIVE_CANDIDATE,
        CandidateClass.LEGACY_DONOR_ONLY,
    }

    manifest = integration.manifest()
    assert all(item["geometry_consumed"] is False for item in manifest["candidate_sources"])
    assert manifest["current_main_motion_geometry_available_count"] == 0
    assert manifest["blocked_motion_count"] == 7


def test_routine_service_session_uses_released_mechanism_transition_contract():
    integration = build_whole_product_service_kinematics()
    idle = integration.removed_idle_state()
    assert idle.device_removed is True
    assert idle.powered is False
    assert idle.mechanism.mode is OperatingMode.IDLE
    assert idle.mechanism.retention_engaged is False

    opened = integration.open_service_session(idle)
    assert opened.mechanism.mode is OperatingMode.SERVICE
    assert opened.mechanism.service_access_open is True
    assert opened.active_domain is None

    selected = integration.select_domain(opened, ServiceDomain.WASTE_CARTRIDGE)
    assert selected.active_domain is ServiceDomain.WASTE_CARTRIDGE
    with pytest.raises(ServiceKinematicsError, match="no released current-main motion geometry"):
        integration.execute_selected_motion(selected)
    with pytest.raises(ServiceKinematicsError, match="only one routine service domain"):
        integration.select_domain(selected, ServiceDomain.WATER_REFILL)

    cleared = integration.clear_domain(selected)
    closed = integration.close_service_session(cleared)
    assert closed.manifest(include_sha=False) == idle.manifest(include_sha=False)


def test_every_routine_domain_can_be_selected_but_not_executed_on_current_main():
    integration = build_whole_product_service_kinematics()
    opened = integration.open_service_session(integration.removed_idle_state())
    routine_domains = tuple(domain for domain in ServiceDomain if domain is not ServiceDomain.EMERGENCY_RELEASE)
    assert len(routine_domains) == 6
    for domain in routine_domains:
        selected = integration.select_domain(opened, domain)
        assert selected.active_domain is domain
        with pytest.raises(ServiceKinematicsError):
            integration.execute_selected_motion(selected)

    with pytest.raises(ServiceKinematicsError, match="emergency release"):
        integration.select_domain(opened, ServiceDomain.EMERGENCY_RELEASE)


def test_conservative_service_interlocks_reject_worn_powered_or_active_cycle_contexts():
    integration = build_whole_product_service_kinematics()
    provenance = integration.kinematics_sha256

    worn_idle = WholeProductServiceState(
        MechanismState(OperatingMode.IDLE, False, False, False, False, False, provenance),
        device_removed=False,
        powered=False,
    )
    with pytest.raises(ServiceKinematicsError, match="removed, unpowered idle"):
        integration.open_service_session(worn_idle)

    powered_removed = WholeProductServiceState(
        MechanismState(OperatingMode.IDLE, False, False, False, False, False, provenance),
        device_removed=True,
        powered=True,
    )
    with pytest.raises(ServiceKinematicsError, match="removed, unpowered idle"):
        integration.open_service_session(powered_removed)

    with pytest.raises(ServiceKinematicsError, match="active cycle cannot coexist with unpowered"):
        WholeProductServiceState(
            MechanismState(OperatingMode.CLEAN, True, True, False, False, False, provenance),
            device_removed=False,
            powered=False,
        )


def test_emergency_release_remains_separate_semantic_transition_without_geometry_promotion():
    integration = build_whole_product_service_kinematics()
    retained = integration.worn_retained_unpowered_idle_state()
    released = integration.emergency_release_reference_state(retained)
    assert retained.device_removed is False
    assert retained.powered is False
    assert retained.mechanism.retention_engaged is True
    assert released.mechanism.retention_engaged is False
    assert released.mechanism.quick_release_open is True
    assert released.active_domain is None

    motion = integration.motion_for(ServiceDomain.EMERGENCY_RELEASE)
    assert motion.current_main_motion_geometry_available is False
    assert "CELL3_RIGHT_RELEASE_PR71" in motion.candidate_source_ids
    assert "ONE_HAND_WET_REQUIREMENT_REMAINS_PHYSICAL_VALIDATION_GATED" in motion.required_conditions


def test_manifest_is_deterministic_and_preserves_evidence_firewall():
    integration = build_whole_product_service_kinematics()
    first = integration.manifest()
    second = integration.manifest()
    assert first == second
    assert first["schema"] == SCHEMA
    assert len(first["kinematics_sha256"]) == 64
    assert first["kinematics_sha256"] == integration.kinematics_sha256
    assert first["physical_validation_eligible"] is False
    assert first["evidence_status"] == DIGITAL_ONLY
    assert first["routine_service_policy"]["simultaneous_active_domains_max"] == 1
    assert first["authority_quick_release_boundary"]["time_status"] == "FROZEN_SAFETY_REQUIREMENT"
    assert first["authority_quick_release_boundary"]["force_status"] == "VALIDATION_GATED"


def test_stale_source_and_evidence_promotions_fail_closed(tmp_path: Path):
    integration = build_whole_product_service_kinematics()
    source_root = Path(__file__).resolve().parents[1]
    with pytest.raises(ServiceKinematicsError, match="released source missing"):
        integration.validate_current_sources(repo_root=tmp_path)

    from dataclasses import replace

    with pytest.raises(ServiceKinematicsError, match="cannot become physical validation"):
        replace(integration, physical_validation_eligible=True).validate_current_sources(repo_root=source_root)


def test_service_manifest_export_round_trip(tmp_path: Path):
    integration = build_whole_product_service_kinematics()
    path = export_service_kinematics_manifest(tmp_path, integration)
    assert path.name == "whole_product_service_kinematics_v1.json"
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded == integration.manifest()
    assert loaded["blocked_motion_count"] == 7
    assert loaded["current_main_motion_geometry_available_count"] == 0
