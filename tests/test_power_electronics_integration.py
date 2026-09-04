from dataclasses import replace

import pytest

from masck_one.authority import load_authority
from masck_one.power_electronics_integration import (
    CURRENT_MAIN_SHA,
    CURRENT_MANUAL_A_HEAD_SHA,
    DIGITAL_ONLY,
    PowerElectronicsIntegrationError,
    build_power_electronics_integration,
)


@pytest.fixture(scope="module")
def built():
    authority = load_authority()
    return authority, build_power_electronics_integration(authority)


def test_exact_head_identity_supersedes_historical_v1_source_label(built):
    _, integration = built
    assert integration.current_main_sha == CURRENT_MAIN_SHA
    assert integration.current_manual_a_head_sha == CURRENT_MANUAL_A_HEAD_SHA
    assert integration.base_package.source_manual_a_head_sha != integration.current_manual_a_head_sha
    assert len(integration.manual_a_realization_sha256) == 64
    assert integration.physical_validation_eligible is False
    assert integration.evidence_status == DIGITAL_ONLY


def test_latest_manual_a_quick_release_guard_is_explicitly_checked(built):
    _, integration = built
    checks = [item for item in integration.exact_head_clearances if item.obstacle_id == "QUICK-RELEASE-GUARD"]
    assert checks
    assert any(item.moving_or_package_id == "BATTERY_REFERENCE" for item in checks)
    assert any(item.moving_or_package_id.startswith("HARNESS-") for item in checks)
    assert any(item.moving_or_package_id == "HMI-CLEAN" for item in checks)
    assert all(item.passes for item in checks)


def test_current_release_and_cartridge_sweeps_are_replayed_against_all_manual_b_geometry(built):
    _, integration = built
    release = [item for item in integration.exact_head_clearances if item.state_id.startswith("QUICK-RELEASE-OUTBOARD-WITHDRAWAL-S")]
    cartridge = [item for item in integration.exact_head_clearances if item.state_id.startswith("CARTRIDGE-DOWNWARD-REMOVAL-S")]
    assert release
    assert cartridge
    assert all(item.passes for item in release + cartridge)
    ids = {item.moving_or_package_id for item in release}
    assert "DRY_BAY_SHELL" in ids
    assert "HARNESS-PCB-HMI" in ids
    assert "HMI-CLEAN" in ids


def test_battery_and_dry_bay_door_service_are_clear_of_release_guard(built):
    _, integration = built
    battery = [item for item in integration.exact_head_clearances if item.check_id.startswith("CLEAR-BATTERY_REFERENCE-SERVICE")]
    door = [item for item in integration.exact_head_clearances if item.check_id.startswith("CLEAR-DRY_BAY_DOOR-SERVICE")]
    assert len(battery) == len(integration.base_package.battery_service_trajectory_xyz_mm)
    assert len(door) == len(integration.base_package.door_service_trajectory_xyz_mm)
    assert all(item.passes for item in battery + door)


def test_buried_electronics_are_clear_of_released_shell_and_hmi_is_explicit_interface(built):
    _, integration = built
    buried = [item for item in integration.shell_integration_records if item.relationship == "REQUIRED_CLEAR_FROM_RELEASED_SHELL_SOLID"]
    assert buried
    assert all(item.shell_intersection_volume_mm3 == pytest.approx(0.0, abs=1e-9) for item in buried)
    hmi = [item for item in integration.shell_integration_records if item.item_id.startswith("HMI-")]
    assert {item.item_id for item in hmi} == {"HMI-CLEAN", "HMI-POWER", "HMI-WARM", "HMI-COOL"}
    assert all(item.relationship == "INTENTIONAL_SIDE_CONTROL_SHELL_INTERFACE" for item in hmi)
    assert all("EXTERIOR" in item.status for item in hmi)


def test_cross_lane_blockers_are_not_hidden(built):
    _, integration = built
    blockers = integration.remaining_cross_lane_blockers
    assert any("EXTERIOR_PR_62" in blocker for blocker in blockers)
    assert any("FLUID_PR_61" in blocker for blocker in blockers)
    assert any("BATTERY_SUPPLIER" in blocker for blocker in blockers)
    assert any("PHYSICAL_INGRESS" in blocker for blocker in blockers)


def test_integration_manifest_is_deterministic(built):
    authority, integration = built
    second = build_power_electronics_integration(authority)
    assert integration.manifest() == second.manifest()
    assert integration.integration_sha256 == second.integration_sha256


def test_stale_exact_head_and_physical_promotion_fail_closed(built):
    _, integration = built
    with pytest.raises(PowerElectronicsIntegrationError, match="Manual A source identity is stale"):
        replace(integration, current_manual_a_head_sha="0" * 40)
    with pytest.raises(PowerElectronicsIntegrationError, match="cannot be physical validation"):
        replace(integration, physical_validation_eligible=True)
