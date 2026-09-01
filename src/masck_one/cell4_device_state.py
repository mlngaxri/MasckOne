from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .power_thermal_contract import PowerThermalEvidenceContract


class Cell4DeviceStateError(ValueError):
    """Raised when simulated Cell 4 consumer-state semantics become misleading."""


class TransportMode(StrEnum):
    SIMULATED_ONLY = "SIMULATED_ONLY"


class OperationState(StrEnum):
    SIMULATED_IDLE = "SIMULATED_IDLE"
    SIMULATED_WET_CYCLE_ACTIVE = "SIMULATED_WET_CYCLE_ACTIVE"
    SIMULATED_SERVICE = "SIMULATED_SERVICE"
    SIMULATED_STORAGE = "SIMULATED_STORAGE"
    SIMULATED_FAULT = "SIMULATED_FAULT"


class BatteryState(StrEnum):
    SIMULATED_UNKNOWN = "SIMULATED_UNKNOWN"
    SIMULATED_READY = "SIMULATED_READY"
    SIMULATED_LOW = "SIMULATED_LOW"
    SIMULATED_CHARGING = "SIMULATED_CHARGING"
    SIMULATED_FAULT = "SIMULATED_FAULT"


class ChargingState(StrEnum):
    SIMULATED_UNKNOWN = "SIMULATED_UNKNOWN"
    SIMULATED_DISCONNECTED = "SIMULATED_DISCONNECTED"
    SIMULATED_CONNECTED = "SIMULATED_CONNECTED"
    SIMULATED_CHARGING = "SIMULATED_CHARGING"
    SIMULATED_COMPLETE = "SIMULATED_COMPLETE"
    SIMULATED_FAULT = "SIMULATED_FAULT"


class CartridgeState(StrEnum):
    SIMULATED_UNKNOWN = "SIMULATED_UNKNOWN"
    SIMULATED_NOT_INSTALLED = "SIMULATED_NOT_INSTALLED"
    SIMULATED_INSTALLED = "SIMULATED_INSTALLED"
    SIMULATED_SERVICE_REQUIRED = "SIMULATED_SERVICE_REQUIRED"
    SIMULATED_FAULT = "SIMULATED_FAULT"


class ServiceState(StrEnum):
    SIMULATED_NORMAL = "SIMULATED_NORMAL"
    SIMULATED_SERVICE_REQUIRED = "SIMULATED_SERVICE_REQUIRED"
    SIMULATED_FAULT = "SIMULATED_FAULT"


class FluidAnimationState(StrEnum):
    BLOCKED_PENDING_RELEASED_ROUTING = "BLOCKED_PENDING_RELEASED_ROUTING"


STATE_CONTRACT_REVISION = "CELL4_DEVICE_STATE_V1_2026_09_01"
FLUID_ANIMATION_BLOCK_REASON = (
    "BLOCKED_UNTIL_A_RELEASED_FLUID_ROUTING_CONTRACT_PROVIDES_EXACT_ROUTE_SOURCE_DESTINATION_PHASE_PROVENANCE"
)


def _text(value: object, *, label: str) -> str:
    if type(value) is not str or not value or value.strip() != value:
        raise Cell4DeviceStateError(f"{label} must be exact built-in nonblank text")
    return value


@dataclass(frozen=True, slots=True)
class DeviceStateSnapshot:
    contract_revision: str
    authority_revision: str
    transport: TransportMode
    operation: OperationState
    battery: BatteryState
    charging: ChargingState
    cartridge: CartridgeState
    service: ServiceState
    fluid_animation: FluidAnimationState
    fluid_animation_block_reason: str
    hardware_telemetry_available: bool = False
    ble_transport_available: bool = False
    battery_sensor_capability_claimed: bool = False
    cartridge_sensor_capability_claimed: bool = False
    physical_validation_eligible: bool = False

    def __post_init__(self) -> None:
        if type(self.contract_revision) is not str or self.contract_revision != STATE_CONTRACT_REVISION:
            raise Cell4DeviceStateError("device-state contract revision is not controlled")
        _text(self.authority_revision, label="device-state authority revision")
        for label, value, enum_type in (
            ("transport", self.transport, TransportMode),
            ("operation", self.operation, OperationState),
            ("battery", self.battery, BatteryState),
            ("charging", self.charging, ChargingState),
            ("cartridge", self.cartridge, CartridgeState),
            ("service", self.service, ServiceState),
            ("fluid_animation", self.fluid_animation, FluidAnimationState),
        ):
            if type(value) is not enum_type:
                raise Cell4DeviceStateError(f"{label} must use the exact controlled enum")
        if self.transport is not TransportMode.SIMULATED_ONLY:
            raise Cell4DeviceStateError("Cell 4 device state must remain explicitly simulated")
        if self.fluid_animation is not FluidAnimationState.BLOCKED_PENDING_RELEASED_ROUTING:
            raise Cell4DeviceStateError("fluid animation cannot activate without released routing provenance")
        if (
            type(self.fluid_animation_block_reason) is not str
            or self.fluid_animation_block_reason != FLUID_ANIMATION_BLOCK_REASON
        ):
            raise Cell4DeviceStateError("fluid animation block reason must remain exact")
        for label, value in (
            ("hardware_telemetry_available", self.hardware_telemetry_available),
            ("ble_transport_available", self.ble_transport_available),
            ("battery_sensor_capability_claimed", self.battery_sensor_capability_claimed),
            ("cartridge_sensor_capability_claimed", self.cartridge_sensor_capability_claimed),
            ("physical_validation_eligible", self.physical_validation_eligible),
        ):
            if type(value) is not bool:
                raise Cell4DeviceStateError(f"{label} must be an exact bool")
            if value:
                raise Cell4DeviceStateError(f"{label} cannot be promoted by simulated state")

        self._validate_cross_state_semantics()

    def _validate_cross_state_semantics(self) -> None:
        if self.battery is BatteryState.SIMULATED_CHARGING:
            if self.charging is not ChargingState.SIMULATED_CHARGING:
                raise Cell4DeviceStateError(
                    "simulated battery charging requires matching simulated charging state"
                )
        if self.charging is ChargingState.SIMULATED_CHARGING:
            if self.battery is not BatteryState.SIMULATED_CHARGING:
                raise Cell4DeviceStateError(
                    "simulated charging state requires matching simulated battery state"
                )
            if self.operation is OperationState.SIMULATED_WET_CYCLE_ACTIVE:
                raise Cell4DeviceStateError(
                    "simulated charging cannot overlap an active wet cycle"
                )
        if self.cartridge is CartridgeState.SIMULATED_SERVICE_REQUIRED:
            if self.service is not ServiceState.SIMULATED_SERVICE_REQUIRED:
                raise Cell4DeviceStateError(
                    "simulated cartridge service requirement must propagate to service state"
                )
        fault_present = any(
            (
                self.operation is OperationState.SIMULATED_FAULT,
                self.battery is BatteryState.SIMULATED_FAULT,
                self.charging is ChargingState.SIMULATED_FAULT,
                self.cartridge is CartridgeState.SIMULATED_FAULT,
            )
        )
        if fault_present and self.service is not ServiceState.SIMULATED_FAULT:
            raise Cell4DeviceStateError(
                "simulated subsystem fault must propagate to simulated service fault"
            )
        if self.service is ServiceState.SIMULATED_FAULT and not fault_present:
            raise Cell4DeviceStateError(
                "simulated service fault requires an explicit simulated subsystem fault"
            )

    def consumer_payload(self) -> dict[str, object]:
        """Return a deterministic consumer payload with explicit simulation/firewall fields."""
        self.__post_init__()
        return {
            "contract_revision": self.contract_revision,
            "authority_revision": self.authority_revision,
            "transport": self.transport.value,
            "operation": self.operation.value,
            "battery": self.battery.value,
            "charging": self.charging.value,
            "cartridge": self.cartridge.value,
            "service": self.service.value,
            "fluid_animation": self.fluid_animation.value,
            "fluid_animation_block_reason": self.fluid_animation_block_reason,
            "hardware_telemetry_available": self.hardware_telemetry_available,
            "ble_transport_available": self.ble_transport_available,
            "battery_sensor_capability_claimed": self.battery_sensor_capability_claimed,
            "cartridge_sensor_capability_claimed": self.cartridge_sensor_capability_claimed,
            "physical_validation_eligible": self.physical_validation_eligible,
        }


def build_simulated_cell4_device_state(
    power_thermal: PowerThermalEvidenceContract,
    *,
    operation: OperationState = OperationState.SIMULATED_IDLE,
    battery: BatteryState = BatteryState.SIMULATED_UNKNOWN,
    charging: ChargingState = ChargingState.SIMULATED_UNKNOWN,
    cartridge: CartridgeState = CartridgeState.SIMULATED_UNKNOWN,
    service: ServiceState = ServiceState.SIMULATED_NORMAL,
) -> DeviceStateSnapshot:
    if type(power_thermal) is not PowerThermalEvidenceContract:
        raise Cell4DeviceStateError(
            "power/thermal source must use the exact controlled contract type"
        )
    power_thermal.__post_init__()
    return DeviceStateSnapshot(
        contract_revision=STATE_CONTRACT_REVISION,
        authority_revision=power_thermal.authority_revision,
        transport=TransportMode.SIMULATED_ONLY,
        operation=operation,
        battery=battery,
        charging=charging,
        cartridge=cartridge,
        service=service,
        fluid_animation=FluidAnimationState.BLOCKED_PENDING_RELEASED_ROUTING,
        fluid_animation_block_reason=FLUID_ANIMATION_BLOCK_REASON,
    )
