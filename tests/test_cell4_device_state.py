from dataclasses import replace

import pytest

from masck_one.authority import load_authority
from masck_one.cell4_device_state import (
    FLUID_ANIMATION_BLOCK_REASON,
    STATE_CONTRACT_REVISION,
    BatteryState,
    CartridgeState,
    Cell4DeviceStateError,
    ChargingState,
    FluidAnimationState,
    OperationState,
    ServiceState,
    TransportMode,
    build_simulated_cell4_device_state,
)
from masck_one.power_thermal_contract import build_cell4_power_thermal_contract


def built_state(**kwargs):
    authority = load_authority()
    power = build_cell4_power_thermal_contract(authority)
    return build_simulated_cell4_device_state(power, authority, **kwargs)


def test_default_payload_is_explicit_simulation_with_no_fake_transport_or_sensors() -> None:
    authority = load_authority()
    power = build_cell4_power_thermal_contract(authority)
    state = build_simulated_cell4_device_state(power, authority)
    payload = state.consumer_payload()
    assert payload["contract_revision"] == STATE_CONTRACT_REVISION
    assert payload["authority_revision"] == authority.get("project", "authority_revision")
    assert payload["source_power_thermal_sha256"] == power.contract_sha256
    assert len(payload["source_power_thermal_sha256"]) == 64
    assert payload["transport"] == "SIMULATED_ONLY"
    assert payload["hardware_telemetry_available"] is False
    assert payload["ble_transport_available"] is False
    assert payload["battery_sensor_capability_claimed"] is False
    assert payload["cartridge_sensor_capability_claimed"] is False
    assert payload["physical_validation_eligible"] is False
    assert payload["fluid_animation"] == "BLOCKED_PENDING_RELEASED_ROUTING"
    assert payload["fluid_animation_block_reason"] == FLUID_ANIMATION_BLOCK_REASON


def test_fluid_animation_cannot_activate_without_released_routing_source() -> None:
    state = built_state()
    with pytest.raises(Cell4DeviceStateError, match="fluid animation"):
        replace(state, fluid_animation="ACTIVE")
    with pytest.raises(Cell4DeviceStateError, match="block reason"):
        replace(state, fluid_animation_block_reason="ROUTES_AVAILABLE")


def test_simulated_charging_requires_bidirectional_state_consistency() -> None:
    charging = built_state(
        battery=BatteryState.SIMULATED_CHARGING,
        charging=ChargingState.SIMULATED_CHARGING,
    )
    assert charging.battery is BatteryState.SIMULATED_CHARGING
    with pytest.raises(Cell4DeviceStateError, match="battery charging"):
        built_state(
            battery=BatteryState.SIMULATED_CHARGING,
            charging=ChargingState.SIMULATED_CONNECTED,
        )
    with pytest.raises(Cell4DeviceStateError, match="matching simulated battery"):
        built_state(
            battery=BatteryState.SIMULATED_READY,
            charging=ChargingState.SIMULATED_CHARGING,
        )


def test_simulated_charging_cannot_overlap_active_wet_cycle() -> None:
    with pytest.raises(Cell4DeviceStateError, match="cannot overlap"):
        built_state(
            operation=OperationState.SIMULATED_WET_CYCLE_ACTIVE,
            battery=BatteryState.SIMULATED_CHARGING,
            charging=ChargingState.SIMULATED_CHARGING,
        )


def test_cartridge_service_requirement_must_propagate() -> None:
    state = built_state(
        cartridge=CartridgeState.SIMULATED_SERVICE_REQUIRED,
        service=ServiceState.SIMULATED_SERVICE_REQUIRED,
    )
    assert state.service is ServiceState.SIMULATED_SERVICE_REQUIRED
    with pytest.raises(Cell4DeviceStateError, match="propagate"):
        built_state(
            cartridge=CartridgeState.SIMULATED_SERVICE_REQUIRED,
            service=ServiceState.SIMULATED_NORMAL,
        )


def test_fault_states_must_propagate_to_service_fault() -> None:
    state = built_state(
        battery=BatteryState.SIMULATED_FAULT,
        service=ServiceState.SIMULATED_FAULT,
    )
    assert state.service is ServiceState.SIMULATED_FAULT
    with pytest.raises(Cell4DeviceStateError, match="propagate"):
        built_state(battery=BatteryState.SIMULATED_FAULT)
    with pytest.raises(Cell4DeviceStateError, match="requires an explicit"):
        built_state(service=ServiceState.SIMULATED_FAULT)


def test_simulated_state_cannot_promote_real_transport_sensor_or_physical_evidence() -> None:
    state = built_state()
    for field in (
        "hardware_telemetry_available",
        "ble_transport_available",
        "battery_sensor_capability_claimed",
        "cartridge_sensor_capability_claimed",
        "physical_validation_eligible",
    ):
        with pytest.raises(Cell4DeviceStateError, match="cannot be promoted"):
            replace(state, **{field: True})


def test_state_contract_rejects_raw_string_enum_aliases() -> None:
    state = built_state()
    with pytest.raises(Cell4DeviceStateError, match="exact controlled enum"):
        replace(state, transport="SIMULATED_ONLY")
    with pytest.raises(Cell4DeviceStateError, match="exact controlled enum"):
        replace(state, operation="SIMULATED_IDLE")
    with pytest.raises(Cell4DeviceStateError, match="exact controlled enum"):
        replace(state, battery="SIMULATED_UNKNOWN")


def test_state_contract_revision_authority_and_source_sha_are_fail_closed() -> None:
    state = built_state()
    with pytest.raises(Cell4DeviceStateError, match="revision is not controlled"):
        replace(state, contract_revision="CELL4_DEVICE_STATE_V2")
    with pytest.raises(Cell4DeviceStateError, match="nonblank text"):
        replace(state, authority_revision=" stale ")
    with pytest.raises(Cell4DeviceStateError, match="canonical lowercase SHA-256"):
        replace(state, source_power_thermal_sha256="not-a-sha")


def test_builder_requires_current_authority_and_rejects_stale_power_source() -> None:
    authority = load_authority()
    power = build_cell4_power_thermal_contract(authority)
    stale = replace(power, authority_revision="STALE")
    with pytest.raises(Cell4DeviceStateError, match="current-authority provenance"):
        build_simulated_cell4_device_state(stale, authority)
    with pytest.raises(Cell4DeviceStateError, match="exact controlled Authority type"):
        build_simulated_cell4_device_state(power, object())


def test_consumer_payload_revalidates_post_construction_corruption() -> None:
    state = built_state()
    object.__setattr__(state, "ble_transport_available", True)
    with pytest.raises(Cell4DeviceStateError, match="cannot be promoted"):
        state.consumer_payload()


def test_source_power_identity_changes_when_power_semantics_change() -> None:
    authority = load_authority()
    power = build_cell4_power_thermal_contract(authority)
    first = build_simulated_cell4_device_state(power, authority)
    assert first.source_power_thermal_sha256 == power.contract_sha256

    object.__setattr__(power.battery, "mass_g", 23.0)
    with pytest.raises(Cell4DeviceStateError, match="current-authority provenance"):
        build_simulated_cell4_device_state(power, authority)


def test_all_consumer_states_remain_visibly_simulated() -> None:
    assert all(item.value.startswith("SIMULATED_") for item in OperationState)
    assert all(item.value.startswith("SIMULATED_") for item in BatteryState)
    assert all(item.value.startswith("SIMULATED_") for item in ChargingState)
    assert all(item.value.startswith("SIMULATED_") for item in CartridgeState)
    assert all(item.value.startswith("SIMULATED_") for item in ServiceState)
    assert tuple(TransportMode) == (TransportMode.SIMULATED_ONLY,)
    assert tuple(FluidAnimationState) == (
        FluidAnimationState.BLOCKED_PENDING_RELEASED_ROUTING,
    )
