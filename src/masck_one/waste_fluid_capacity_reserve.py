"""Explicit cartridge capacity-reserve composition for waste/fluid integration."""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Sequence

from .waste_fluid_accounting import WasteFluidAccountingError, WasteFluidBudget
from .waste_fluid_cycle_evidence import validate_cycle_routing_evidence
from .waste_fluid_overflow_guard import CartridgeOverflowGuard, screen_cartridge_overflow_guard
from .waste_fluid_profile import ServiceFluidProfile, screen_service_profile


@dataclass(frozen=True, slots=True)
class CartridgeCapacityReserve:
    """Explicit unavailable-volume allowances supplied by owning subsystems."""
    fill_sensor_trip_mL: float = 0.0
    foam_allowance_mL: float = 0.0
    manufacturing_tolerance_mL: float = 0.0
    other_integration_mL: float = 0.0

    def validate(self) -> None:
        for name, value in (("fill_sensor_trip_mL", self.fill_sensor_trip_mL), ("foam_allowance_mL", self.foam_allowance_mL), ("manufacturing_tolerance_mL", self.manufacturing_tolerance_mL), ("other_integration_mL", self.other_integration_mL)):
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise WasteFluidAccountingError(f"{name} must be a finite numeric value")
            if not math.isfinite(float(value)) or float(value) < 0.0:
                raise WasteFluidAccountingError(f"{name} must be finite and nonnegative")

    @property
    def total_mL(self) -> float:
        self.validate()
        return float(self.fill_sensor_trip_mL + self.foam_allowance_mL + self.manufacturing_tolerance_mL + self.other_integration_mL)

    @property
    def breakdown_mL(self) -> tuple[tuple[str, float], ...]:
        self.validate()
        return (("fill_sensor_trip_mL", float(self.fill_sensor_trip_mL)), ("foam_allowance_mL", float(self.foam_allowance_mL)), ("manufacturing_tolerance_mL", float(self.manufacturing_tolerance_mL)), ("other_integration_mL", float(self.other_integration_mL)))

    @property
    def evidence_sha256(self) -> str:
        """Canonical identity for reserve composition, not merely its scalar total."""
        payload = {name: value for name, value in self.breakdown_mL}
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True, slots=True)
class CapacityReservedOverflowGuard:
    """Overflow result retaining the exact reserve composition that produced it."""
    reserve: CartridgeCapacityReserve
    guard: CartridgeOverflowGuard

    def __post_init__(self) -> None:
        if type(self.reserve) is not CartridgeCapacityReserve:
            raise WasteFluidAccountingError("reserve evidence must use exact CartridgeCapacityReserve type")
        if type(self.guard) is not CartridgeOverflowGuard:
            raise WasteFluidAccountingError("guard evidence must use exact CartridgeOverflowGuard type")
        self.reserve.validate()
        validate_cycle_routing_evidence(self.guard.routing)
        self.guard.__post_init__()
        if not math.isclose(self.guard.capacity_reserve_mL, self.reserve.total_mL, rel_tol=0.0, abs_tol=1e-12):
            raise WasteFluidAccountingError("overflow guard reserve total does not match typed reserve evidence")
        if self.guard.source_capacity_reserve_sha256 != self.reserve.evidence_sha256:
            raise WasteFluidAccountingError("overflow guard reserve composition does not match typed reserve evidence")


@dataclass(frozen=True, slots=True)
class CapacityReservedServiceProfile:
    """Service profile retaining the exact reserve assumptions that produced it."""
    reserve: CartridgeCapacityReserve
    profile: ServiceFluidProfile

    def __post_init__(self) -> None:
        if type(self.reserve) is not CartridgeCapacityReserve:
            raise WasteFluidAccountingError("reserve evidence must use exact CartridgeCapacityReserve type")
        if type(self.profile) is not ServiceFluidProfile:
            raise WasteFluidAccountingError("profile evidence must use exact ServiceFluidProfile type")
        if not math.isclose(self.profile.capacity_reserve_mL, self.reserve.total_mL, rel_tol=0.0, abs_tol=1e-12):
            raise WasteFluidAccountingError("service profile reserve total does not match typed reserve evidence")


def _validated_total_reserve_mL(budget: WasteFluidBudget, reserve: CartridgeCapacityReserve) -> float:
    budget.validate()
    if type(reserve) is not CartridgeCapacityReserve:
        raise WasteFluidAccountingError("reserve must use the exact CartridgeCapacityReserve type")
    total = reserve.total_mL
    if total >= budget.cartridge_retained_capacity_requirement_mL:
        raise WasteFluidAccountingError("composed capacity reserve must be smaller than cartridge retained-capacity requirement")
    return total


def screen_cartridge_capacity_reserve(budget: WasteFluidBudget, reserve: CartridgeCapacityReserve, *, prime_events_by_cycle: tuple[int, ...] | list[int], prime_recovery_ratio_contract: float | None = None, prime_residual_ratio_contract: float | None = None, prime_external_leakage_ratio_contract: float | None = None) -> CartridgeOverflowGuard:
    total = _validated_total_reserve_mL(budget, reserve)
    return screen_cartridge_overflow_guard(budget, prime_events_by_cycle=prime_events_by_cycle, prime_recovery_ratio_contract=prime_recovery_ratio_contract, prime_residual_ratio_contract=prime_residual_ratio_contract, prime_external_leakage_ratio_contract=prime_external_leakage_ratio_contract, capacity_reserve_mL=total, source_capacity_reserve_sha256=reserve.evidence_sha256)


def screen_cartridge_capacity_reserve_evidence(budget: WasteFluidBudget, reserve: CartridgeCapacityReserve, *, prime_events_by_cycle: tuple[int, ...] | list[int], prime_recovery_ratio_contract: float | None = None, prime_residual_ratio_contract: float | None = None, prime_external_leakage_ratio_contract: float | None = None) -> CapacityReservedOverflowGuard:
    """Return overflow accounting with source-bound reserve composition."""
    guard = screen_cartridge_capacity_reserve(budget, reserve, prime_events_by_cycle=prime_events_by_cycle, prime_recovery_ratio_contract=prime_recovery_ratio_contract, prime_residual_ratio_contract=prime_residual_ratio_contract, prime_external_leakage_ratio_contract=prime_external_leakage_ratio_contract)
    return CapacityReservedOverflowGuard(reserve=reserve, guard=guard)


def screen_service_profile_with_capacity_reserve(budget: WasteFluidBudget, reserve: CartridgeCapacityReserve, *, prime_events_by_cycle: Sequence[int], target_cycles: int | None = None, future_prime_events_per_remaining_cycle: int = 0) -> ServiceFluidProfile:
    """Run service-life accounting using an explicit composed capacity reserve."""
    total = _validated_total_reserve_mL(budget, reserve)
    return screen_service_profile(budget, prime_events_by_cycle=prime_events_by_cycle, target_cycles=target_cycles, future_prime_events_per_remaining_cycle=future_prime_events_per_remaining_cycle, capacity_reserve_mL=total)


def screen_service_profile_with_capacity_reserve_evidence(budget: WasteFluidBudget, reserve: CartridgeCapacityReserve, *, prime_events_by_cycle: Sequence[int], target_cycles: int | None = None, future_prime_events_per_remaining_cycle: int = 0) -> CapacityReservedServiceProfile:
    """Return service accounting together with source-bound reserve composition."""
    profile = screen_service_profile_with_capacity_reserve(budget, reserve, prime_events_by_cycle=prime_events_by_cycle, target_cycles=target_cycles, future_prime_events_per_remaining_cycle=future_prime_events_per_remaining_cycle)
    return CapacityReservedServiceProfile(reserve=reserve, profile=profile)
