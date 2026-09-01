from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import math

from .authority import Authority


class PowerThermalContractError(ValueError):
    """Raised when Cell 4 power/thermal evidence semantics fail closed."""


class LoadStatus(StrEnum):
    UNRESOLVED = "UNRESOLVED"
    BOUNDED_MODEL_INPUT = "BOUNDED_MODEL_INPUT"
    MEASURED = "MEASURED"


class ThermalStatus(StrEnum):
    BLOCKED = "BLOCKED"
    BOUNDED_MODEL = "BOUNDED_MODEL"
    MEASURED_CLOSED = "MEASURED_CLOSED"


class EvidenceKind(StrEnum):
    BOUNDED_MODEL_INPUT = "BOUNDED_MODEL_INPUT"
    SUPPLIER_CONTROLLED_DATA = "SUPPLIER_CONTROLLED_DATA"
    CONTROLLED_PRODUCT_MEASUREMENT = "CONTROLLED_PRODUCT_MEASUREMENT"


class ChargingConventionStatus(StrEnum):
    COMMERCIAL_PREFERENCE_ONLY = "COMMERCIAL_PREFERENCE_ONLY"
    ARCHITECTURE_SELECTED = "ARCHITECTURE_SELECTED"
    PHYSICALLY_VERIFIED = "PHYSICALLY_VERIFIED"


LOAD_IDS = (
    "ACTUATOR_ARRAY",
    "WATER_PUMP",
    "CLEANSER_PUMP",
    "WASTE_PUMP",
    "CONTROL_ELECTRONICS",
    "PHYSICAL_HMI",
    "WARM_SUBSYSTEM",
    "COOL_RESERVATION",
    "STANDBY",
)

THERMAL_RISK_IDS = (
    "BATTERY_SELF_HEATING",
    "CHARGING_HEAT",
    "ACTUATOR_HEAT",
    "PUMP_HEAT",
    "CONTROL_ELECTRONICS_HEAT",
    "WARM_SKIN_ADJACENT_HEAT",
    "WET_DRY_BOUNDARY_HEAT_TRANSFER",
    "COOL_CONDENSATION_DEW_POINT",
)

BATTERY_REFERENCE_STATUS = "PACKAGING_BENCHMARK_NOT_PRODUCTION_FREEZE"
ENERGY_BOUND_STATUS = "MODELED_ENERGY_BOUND_ONLY_NOT_RUNTIME_EVIDENCE"
CHARGING_PREFERENCE = "USB_C_PREFERRED_IF_INGRESS_ELECTRICAL_AND_SERVICE_ARCHITECTURE_PERMIT"
CHARGING_PREFERENCE_STATUS = ChargingConventionStatus.COMMERCIAL_PREFERENCE_ONLY


def _text(value: object, *, label: str) -> str:
    if type(value) is not str or not value or value.strip() != value:
        raise PowerThermalContractError(f"{label} must be exact built-in nonblank text")
    return value


def _real(value: object, *, label: str, positive: bool = False, nonnegative: bool = False) -> float:
    if type(value) not in (int, float):
        raise PowerThermalContractError(f"{label} must be an exact finite numeric scalar")
    try:
        result = float(value)
    except (OverflowError, ValueError) as exc:
        raise PowerThermalContractError(f"{label} must be representable as a finite float") from exc
    if not math.isfinite(result):
        raise PowerThermalContractError(f"{label} must be finite")
    if result == 0.0 and math.copysign(1.0, result) < 0.0:
        raise PowerThermalContractError(f"{label} cannot use negative signed zero")
    if positive and result <= 0.0:
        raise PowerThermalContractError(f"{label} must be positive")
    if nonnegative and result < 0.0:
        raise PowerThermalContractError(f"{label} must be non-negative")
    return result


def _exact_tuple(value: object, *, label: str) -> tuple[object, ...]:
    if type(value) is not tuple:
        raise PowerThermalContractError(f"{label} must be an immutable exact tuple")
    return value


def _evidence_ids(value: object, *, label: str) -> tuple[str, ...]:
    items = _exact_tuple(value, label=label)
    if any(type(item) is not str or not item or item.strip() != item for item in items):
        raise PowerThermalContractError(f"{label} entries must be exact built-in nonblank strings")
    if len(set(items)) != len(items):
        raise PowerThermalContractError(f"{label} entries must be unique")
    return tuple(items)


def _validate_model_evidence_kind(kind: EvidenceKind | None, *, label: str) -> None:
    if type(kind) is not EvidenceKind or kind not in {
        EvidenceKind.BOUNDED_MODEL_INPUT,
        EvidenceKind.SUPPLIER_CONTROLLED_DATA,
    }:
        raise PowerThermalContractError(
            f"{label} requires BOUNDED_MODEL_INPUT or SUPPLIER_CONTROLLED_DATA provenance"
        )


def _validate_measurement_evidence_kind(kind: EvidenceKind | None, *, label: str) -> None:
    if type(kind) is not EvidenceKind or kind is not EvidenceKind.CONTROLLED_PRODUCT_MEASUREMENT:
        raise PowerThermalContractError(
            f"{label} requires CONTROLLED_PRODUCT_MEASUREMENT provenance"
        )


@dataclass(frozen=True, slots=True)
class BatteryPackagingBenchmark:
    candidate: str
    nominal_voltage_V: float
    capacity_mAh: float
    envelope_mm: tuple[float, float, float]
    mass_g: float
    status: str
    production_selected: bool = False
    runtime_claim_eligible: bool = False

    def __post_init__(self) -> None:
        _text(self.candidate, label="battery benchmark candidate")
        object.__setattr__(
            self,
            "nominal_voltage_V",
            _real(self.nominal_voltage_V, label="battery benchmark nominal voltage", positive=True),
        )
        object.__setattr__(
            self,
            "capacity_mAh",
            _real(self.capacity_mAh, label="battery benchmark capacity", positive=True),
        )
        envelope = _exact_tuple(self.envelope_mm, label="battery benchmark envelope")
        if len(envelope) != 3:
            raise PowerThermalContractError("battery benchmark envelope must contain exactly three dimensions")
        clean_envelope = tuple(
            _real(item, label=f"battery benchmark envelope[{index}]", positive=True)
            for index, item in enumerate(envelope)
        )
        object.__setattr__(self, "envelope_mm", clean_envelope)
        object.__setattr__(
            self,
            "mass_g",
            _real(self.mass_g, label="battery benchmark mass", positive=True),
        )
        if type(self.status) is not str or self.status != BATTERY_REFERENCE_STATUS:
            raise PowerThermalContractError("battery reference must retain packaging-benchmark status")
        if type(self.production_selected) is not bool or self.production_selected:
            raise PowerThermalContractError("battery packaging benchmark cannot be promoted to production-selected")
        if type(self.runtime_claim_eligible) is not bool or self.runtime_claim_eligible:
            raise PowerThermalContractError("battery packaging benchmark cannot authorize runtime claims")

    @property
    def nominal_reference_energy_Wh(self) -> float:
        """Electrical nameplate arithmetic for packaging comparison only."""
        return self.nominal_voltage_V * self.capacity_mAh / 1000.0


@dataclass(frozen=True, slots=True)
class PowerLoadWindow:
    load_id: str
    status: LoadStatus
    minimum_power_W: float | None = None
    maximum_power_W: float | None = None
    minimum_duration_s: float | None = None
    maximum_duration_s: float | None = None
    evidence_kind: EvidenceKind | None = None
    evidence_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if type(self.load_id) is not str or self.load_id not in LOAD_IDS:
            raise PowerThermalContractError("power load ID is not controlled")
        if type(self.status) is not LoadStatus:
            raise PowerThermalContractError("power load status must use the exact controlled enum")
        evidence = _evidence_ids(self.evidence_ids, label=f"{self.load_id} evidence_ids")
        object.__setattr__(self, "evidence_ids", evidence)

        values = (
            self.minimum_power_W,
            self.maximum_power_W,
            self.minimum_duration_s,
            self.maximum_duration_s,
        )
        if self.status is LoadStatus.UNRESOLVED:
            if any(value is not None for value in values) or evidence or self.evidence_kind is not None:
                raise PowerThermalContractError(
                    "UNRESOLVED power load cannot carry numeric inputs or evidence"
                )
            return

        if any(value is None for value in values):
            raise PowerThermalContractError(
                "bounded/measured power load requires complete power and duration bounds"
            )
        min_power = _real(
            self.minimum_power_W,
            label=f"{self.load_id} minimum power",
            nonnegative=True,
        )
        max_power = _real(
            self.maximum_power_W,
            label=f"{self.load_id} maximum power",
            nonnegative=True,
        )
        min_duration = _real(
            self.minimum_duration_s,
            label=f"{self.load_id} minimum duration",
            nonnegative=True,
        )
        max_duration = _real(
            self.maximum_duration_s,
            label=f"{self.load_id} maximum duration",
            nonnegative=True,
        )
        if min_power > max_power:
            raise PowerThermalContractError("minimum power cannot exceed maximum power")
        if min_duration > max_duration:
            raise PowerThermalContractError("minimum duration cannot exceed maximum duration")
        if not evidence:
            raise PowerThermalContractError(
                "bounded/measured power load requires explicit evidence provenance"
            )
        if self.status is LoadStatus.BOUNDED_MODEL_INPUT:
            _validate_model_evidence_kind(self.evidence_kind, label="bounded power load")
        elif self.status is LoadStatus.MEASURED:
            _validate_measurement_evidence_kind(self.evidence_kind, label="measured power load")
        object.__setattr__(self, "minimum_power_W", min_power)
        object.__setattr__(self, "maximum_power_W", max_power)
        object.__setattr__(self, "minimum_duration_s", min_duration)
        object.__setattr__(self, "maximum_duration_s", max_duration)

    @property
    def minimum_energy_Wh(self) -> float:
        if self.status is LoadStatus.UNRESOLVED:
            raise PowerThermalContractError("unresolved load has no computable energy bound")
        assert self.minimum_power_W is not None and self.minimum_duration_s is not None
        return self.minimum_power_W * self.minimum_duration_s / 3600.0

    @property
    def maximum_energy_Wh(self) -> float:
        if self.status is LoadStatus.UNRESOLVED:
            raise PowerThermalContractError("unresolved load has no computable energy bound")
        assert self.maximum_power_W is not None and self.maximum_duration_s is not None
        return self.maximum_power_W * self.maximum_duration_s / 3600.0


@dataclass(frozen=True, slots=True)
class PowerBudget:
    loads: tuple[PowerLoadWindow, ...]
    result_status: str
    runtime_claim_eligible: bool = False

    def __post_init__(self) -> None:
        loads = _exact_tuple(self.loads, label="power loads")
        if any(type(item) is not PowerLoadWindow for item in loads):
            raise PowerThermalContractError(
                "power loads must contain exact PowerLoadWindow records"
            )
        ids = tuple(item.load_id for item in loads)
        if ids != LOAD_IDS:
            raise PowerThermalContractError(
                "power load ledger must contain the complete controlled load set in canonical order"
            )
        if type(self.result_status) is not str or self.result_status != ENERGY_BOUND_STATUS:
            raise PowerThermalContractError("power budget result status must remain modeled-only")
        if type(self.runtime_claim_eligible) is not bool or self.runtime_claim_eligible:
            raise PowerThermalContractError("power budget cannot authorize runtime claims")
        object.__setattr__(self, "loads", tuple(loads))

    @property
    def complete_for_energy_bounds(self) -> bool:
        return all(item.status is not LoadStatus.UNRESOLVED for item in self.loads)

    def energy_bounds_Wh(self) -> tuple[float, float]:
        if not self.complete_for_energy_bounds:
            raise PowerThermalContractError(
                "power budget cannot close while any load remains unresolved"
            )
        minimum = sum(item.minimum_energy_Wh for item in self.loads)
        maximum = sum(item.maximum_energy_Wh for item in self.loads)
        return minimum, maximum


@dataclass(frozen=True, slots=True)
class ThermalRiskGate:
    risk_id: str
    status: ThermalStatus
    model_bounds: tuple[float, float] | None = None
    unit: str | None = None
    evidence_kind: EvidenceKind | None = None
    evidence_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if type(self.risk_id) is not str or self.risk_id not in THERMAL_RISK_IDS:
            raise PowerThermalContractError("thermal risk ID is not controlled")
        if type(self.status) is not ThermalStatus:
            raise PowerThermalContractError("thermal status must use the exact controlled enum")
        evidence = _evidence_ids(self.evidence_ids, label=f"{self.risk_id} evidence_ids")
        object.__setattr__(self, "evidence_ids", evidence)

        if self.status is ThermalStatus.BLOCKED:
            if (
                self.model_bounds is not None
                or self.unit is not None
                or evidence
                or self.evidence_kind is not None
            ):
                raise PowerThermalContractError(
                    "BLOCKED thermal gate cannot carry model bounds or closure evidence"
                )
            return

        bounds = _exact_tuple(self.model_bounds, label=f"{self.risk_id} model bounds")
        if len(bounds) != 2:
            raise PowerThermalContractError(
                "thermal model bounds must contain exactly two values"
            )
        lower = _real(bounds[0], label=f"{self.risk_id} lower bound")
        upper = _real(bounds[1], label=f"{self.risk_id} upper bound")
        if lower > upper:
            raise PowerThermalContractError("thermal lower bound cannot exceed upper bound")
        if type(self.unit) is not str or not self.unit or self.unit.strip() != self.unit:
            raise PowerThermalContractError(
                "bounded thermal gate requires an exact nonblank unit"
            )
        if not evidence:
            raise PowerThermalContractError(
                "bounded/measured thermal gate requires evidence provenance"
            )
        if self.status is ThermalStatus.BOUNDED_MODEL:
            _validate_model_evidence_kind(self.evidence_kind, label="bounded thermal gate")
        elif self.status is ThermalStatus.MEASURED_CLOSED:
            _validate_measurement_evidence_kind(
                self.evidence_kind,
                label="measured thermal gate",
            )
        object.__setattr__(self, "model_bounds", (lower, upper))


@dataclass(frozen=True, slots=True)
class ChargingArchitectureBoundary:
    convention: str
    status: ChargingConventionStatus
    active_wet_cycle_charging_allowed: bool
    app_required_for_charge_recovery: bool
    ingress_architecture_verified: bool
    electrical_protection_verified: bool

    def __post_init__(self) -> None:
        if type(self.convention) is not str or self.convention != CHARGING_PREFERENCE:
            raise PowerThermalContractError(
                "charging convention must remain the controlled commercial preference"
            )
        if (
            type(self.status) is not ChargingConventionStatus
            or self.status is not CHARGING_PREFERENCE_STATUS
        ):
            raise PowerThermalContractError(
                "charging convention is not yet architecture-selected or verified"
            )
        for label, value in (
            ("active_wet_cycle_charging_allowed", self.active_wet_cycle_charging_allowed),
            ("app_required_for_charge_recovery", self.app_required_for_charge_recovery),
            ("ingress_architecture_verified", self.ingress_architecture_verified),
            ("electrical_protection_verified", self.electrical_protection_verified),
        ):
            if type(value) is not bool:
                raise PowerThermalContractError(f"{label} must be an exact bool")
        if self.active_wet_cycle_charging_allowed:
            raise PowerThermalContractError(
                "charging during an active wet cycle is not authorized by current evidence"
            )
        if self.app_required_for_charge_recovery:
            raise PowerThermalContractError(
                "core charge fault recovery cannot be app-only in the current architecture"
            )
        if self.ingress_architecture_verified or self.electrical_protection_verified:
            raise PowerThermalContractError(
                "charging ingress/protection cannot be promoted before physical/electrical evidence"
            )


@dataclass(frozen=True, slots=True)
class PowerThermalEvidenceContract:
    authority_revision: str
    battery: BatteryPackagingBenchmark
    power_budget: PowerBudget
    thermal_gates: tuple[ThermalRiskGate, ...]
    charging: ChargingArchitectureBoundary
    physical_validation_eligible: bool = False

    def __post_init__(self) -> None:
        _text(self.authority_revision, label="power/thermal authority revision")
        if type(self.battery) is not BatteryPackagingBenchmark:
            raise PowerThermalContractError(
                "battery benchmark must use the exact controlled type"
            )
        if type(self.power_budget) is not PowerBudget:
            raise PowerThermalContractError(
                "power budget must use the exact controlled type"
            )
        gates = _exact_tuple(self.thermal_gates, label="thermal gates")
        if any(type(item) is not ThermalRiskGate for item in gates):
            raise PowerThermalContractError(
                "thermal gates must contain exact ThermalRiskGate records"
            )
        ids = tuple(item.risk_id for item in gates)
        if ids != THERMAL_RISK_IDS:
            raise PowerThermalContractError(
                "thermal gate ledger must contain the complete controlled risk set in canonical order"
            )
        if type(self.charging) is not ChargingArchitectureBoundary:
            raise PowerThermalContractError(
                "charging boundary must use the exact controlled type"
            )
        if type(self.physical_validation_eligible) is not bool or self.physical_validation_eligible:
            raise PowerThermalContractError(
                "digital power/thermal contract is not physical validation evidence"
            )
        object.__setattr__(self, "thermal_gates", tuple(gates))

    def validate_current_authority(self, authority: Authority) -> None:
        if type(authority) is not Authority:
            raise PowerThermalContractError(
                "authority must use the exact controlled Authority type"
            )
        revision = authority.get("project", "authority_revision")
        if type(revision) is not str or revision != self.authority_revision:
            raise PowerThermalContractError(
                "power/thermal contract is stale for current authority revision"
            )
        raw = authority.get("battery_reference")
        if type(raw) is not dict:
            raise PowerThermalContractError(
                "battery reference authority must be an exact mapping"
            )
        raw_envelope = raw.get("envelope_mm")
        expected = BatteryPackagingBenchmark(
            candidate=raw.get("candidate"),
            nominal_voltage_V=raw.get("nominal_voltage_V"),
            capacity_mAh=raw.get("capacity_mAh"),
            envelope_mm=(
                tuple(raw_envelope)
                if type(raw_envelope) is list
                else raw_envelope
            ),
            mass_g=raw.get("mass_g"),
            status=raw.get("status"),
        )
        if self.battery != expected:
            raise PowerThermalContractError(
                "battery packaging benchmark is stale for current authority"
            )


def build_cell4_power_thermal_contract(authority: Authority) -> PowerThermalEvidenceContract:
    if type(authority) is not Authority:
        raise PowerThermalContractError(
            "authority must use the exact controlled Authority type"
        )
    revision = authority.get("project", "authority_revision")
    _text(revision, label="authority revision")
    raw = authority.get("battery_reference")
    if type(raw) is not dict:
        raise PowerThermalContractError(
            "battery reference authority must be an exact mapping"
        )
    envelope = raw.get("envelope_mm")
    if type(envelope) is not list or len(envelope) != 3:
        raise PowerThermalContractError(
            "battery authority envelope must be an exact three-item list"
        )
    battery = BatteryPackagingBenchmark(
        candidate=raw.get("candidate"),
        nominal_voltage_V=raw.get("nominal_voltage_V"),
        capacity_mAh=raw.get("capacity_mAh"),
        envelope_mm=tuple(envelope),
        mass_g=raw.get("mass_g"),
        status=raw.get("status"),
    )
    power_budget = PowerBudget(
        loads=tuple(
            PowerLoadWindow(load_id, LoadStatus.UNRESOLVED)
            for load_id in LOAD_IDS
        ),
        result_status=ENERGY_BOUND_STATUS,
    )
    thermal_gates = tuple(
        ThermalRiskGate(risk_id=risk_id, status=ThermalStatus.BLOCKED)
        for risk_id in THERMAL_RISK_IDS
    )
    charging = ChargingArchitectureBoundary(
        convention=CHARGING_PREFERENCE,
        status=CHARGING_PREFERENCE_STATUS,
        active_wet_cycle_charging_allowed=False,
        app_required_for_charge_recovery=False,
        ingress_architecture_verified=False,
        electrical_protection_verified=False,
    )
    contract = PowerThermalEvidenceContract(
        authority_revision=revision,
        battery=battery,
        power_budget=power_budget,
        thermal_gates=thermal_gates,
        charging=charging,
    )
    contract.validate_current_authority(authority)
    return contract
