"""Cartridge overflow guard derived from cycle-resolved fluid accounting."""
from __future__ import annotations

import math
from dataclasses import dataclass

from .waste_fluid_accounting import WasteFluidAccountingError, WasteFluidBudget
from .waste_fluid_cycle_routing import CycleResolvedRoutingClosure, screen_cycle_resolved_routing_closure

_TOL = 1e-12


@dataclass(frozen=True)
class CartridgeOverflowGuard:
    """Capacity disposition for an explicit service-cycle reprime schedule.

    Retained and usable capacity are both carried so downstream integration cannot
    silently reinterpret an unavailable-volume reserve as a smaller cartridge.
    """

    routing: CycleResolvedRoutingClosure
    retained_capacity_mL: float
    capacity_reserve_mL: float
    usable_capacity_mL: float
    contractual_required_usable_capacity_mL: float
    conservative_required_usable_capacity_mL: float
    first_unavoidable_overflow_cycle: int | None
    first_conservative_capacity_failure_cycle: int | None
    minimum_overflow_at_failure_mL: float
    conservative_overflow_at_failure_mL: float
    contractual_reserve_headroom_mL: float
    conservative_reserve_headroom_mL: float
    source_capacity_reserve_sha256: str | None = None

    def __post_init__(self) -> None:
        if type(self.routing) is not CycleResolvedRoutingClosure:
            raise WasteFluidAccountingError("overflow guard requires exact CycleResolvedRoutingClosure evidence")
        if not self.routing.cycles:
            raise WasteFluidAccountingError("overflow guard requires at least one routed cycle")
        if self.source_capacity_reserve_sha256 is not None:
            value = self.source_capacity_reserve_sha256
            if type(value) is not str or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
                raise WasteFluidAccountingError("capacity reserve provenance must be a canonical lowercase SHA-256 digest")
        numeric = {
            "retained_capacity_mL": self.retained_capacity_mL,
            "capacity_reserve_mL": self.capacity_reserve_mL,
            "usable_capacity_mL": self.usable_capacity_mL,
            "contractual_required_usable_capacity_mL": self.contractual_required_usable_capacity_mL,
            "conservative_required_usable_capacity_mL": self.conservative_required_usable_capacity_mL,
            "minimum_overflow_at_failure_mL": self.minimum_overflow_at_failure_mL,
            "conservative_overflow_at_failure_mL": self.conservative_overflow_at_failure_mL,
            "contractual_reserve_headroom_mL": self.contractual_reserve_headroom_mL,
            "conservative_reserve_headroom_mL": self.conservative_reserve_headroom_mL,
        }
        for name, value in numeric.items():
            if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)):
                raise WasteFluidAccountingError(f"{name} must be a finite numeric value")
        for name, value in (
            ("first_unavoidable_overflow_cycle", self.first_unavoidable_overflow_cycle),
            ("first_conservative_capacity_failure_cycle", self.first_conservative_capacity_failure_cycle),
        ):
            if value is not None and (type(value) is not int or value < 1):
                raise WasteFluidAccountingError(f"{name} must be None or a positive exact integer cycle")
        if self.retained_capacity_mL <= 0 or self.capacity_reserve_mL < 0 or self.usable_capacity_mL <= 0:
            raise WasteFluidAccountingError("overflow guard retained/reserve/usable capacity is nonphysical")
        if not math.isclose(self.usable_capacity_mL + self.capacity_reserve_mL, self.retained_capacity_mL, rel_tol=0.0, abs_tol=_TOL):
            raise WasteFluidAccountingError("usable capacity plus reserve must equal retained cartridge capacity")

        final = self.routing.cycles[-1]
        contractual_required = final.cumulative_minimum_cartridge_routing_mL
        conservative_required = final.cumulative_maximum_cartridge_inflow_mL
        unavoidable_state = next((s for s in self.routing.cycles if s.cumulative_minimum_cartridge_routing_mL > self.usable_capacity_mL + _TOL), None)
        conservative_state = next((s for s in self.routing.cycles if s.cumulative_maximum_cartridge_inflow_mL > self.usable_capacity_mL + _TOL), None)
        unavoidable_cycle = None if unavoidable_state is None else unavoidable_state.cycle
        conservative_cycle = None if conservative_state is None else conservative_state.cycle
        minimum_overflow = 0.0 if unavoidable_state is None else max(0.0, unavoidable_state.cumulative_minimum_cartridge_routing_mL - self.usable_capacity_mL)
        conservative_overflow = 0.0 if conservative_state is None else max(0.0, conservative_state.cumulative_maximum_cartridge_inflow_mL - self.usable_capacity_mL)
        expected = (
            contractual_required, conservative_required, unavoidable_cycle, conservative_cycle,
            minimum_overflow, conservative_overflow,
            self.usable_capacity_mL - contractual_required,
            self.usable_capacity_mL - conservative_required,
        )
        supplied = (
            self.contractual_required_usable_capacity_mL, self.conservative_required_usable_capacity_mL,
            self.first_unavoidable_overflow_cycle, self.first_conservative_capacity_failure_cycle,
            self.minimum_overflow_at_failure_mL, self.conservative_overflow_at_failure_mL,
            self.contractual_reserve_headroom_mL, self.conservative_reserve_headroom_mL,
        )
        for index, (actual, wanted) in enumerate(zip(supplied, expected)):
            if index in (2, 3):
                if actual != wanted:
                    raise WasteFluidAccountingError("overflow guard cycle disposition is stale or inconsistent with routing evidence")
            elif not math.isclose(float(actual), float(wanted), rel_tol=0.0, abs_tol=_TOL):
                raise WasteFluidAccountingError("overflow guard capacity accounting is stale or inconsistent with routing evidence")
        if contractual_required > conservative_required + _TOL:
            raise WasteFluidAccountingError("contractual required capacity exceeds conservative required capacity")
        if unavoidable_cycle is not None and (conservative_cycle is None or unavoidable_cycle < conservative_cycle):
            raise WasteFluidAccountingError("minimum-routing overflow cannot precede conservative inflow overflow")

    @property
    def sizing_uncertainty_mL(self) -> float:
        return self.conservative_required_usable_capacity_mL - self.contractual_required_usable_capacity_mL

    @property
    def contractual_end_of_service_overflow_mL(self) -> float:
        """Minimum liquid that cannot fit by the end of the screened service profile."""
        return max(0.0, -self.contractual_reserve_headroom_mL)

    @property
    def conservative_end_of_service_overflow_mL(self) -> float:
        """Worst screened capacity shortfall at the end of the service profile."""
        return max(0.0, -self.conservative_reserve_headroom_mL)

    @property
    def unavoidable_overflow(self) -> bool:
        return self.first_unavoidable_overflow_cycle is not None

    @property
    def conservative_fit_unproven(self) -> bool:
        return self.first_conservative_capacity_failure_cycle is not None

    @property
    def capacity_proven_by_conservative_screen(self) -> bool:
        return self.first_conservative_capacity_failure_cycle is None


def screen_cartridge_overflow_guard(
    budget: WasteFluidBudget, *, prime_events_by_cycle: tuple[int, ...] | list[int],
    prime_recovery_ratio_contract: float | None = None,
    prime_residual_ratio_contract: float | None = None,
    prime_external_leakage_ratio_contract: float | None = None,
    capacity_reserve_mL: float = 0.0,
    source_capacity_reserve_sha256: str | None = None,
) -> CartridgeOverflowGuard:
    """Classify cartridge capacity without granting unsupported sink credit."""
    budget.validate()
    if not isinstance(capacity_reserve_mL, (int, float)) or isinstance(capacity_reserve_mL, bool):
        raise WasteFluidAccountingError("capacity_reserve_mL must be a finite numeric value")
    capacity_reserve_mL = float(capacity_reserve_mL)
    if not math.isfinite(capacity_reserve_mL) or capacity_reserve_mL < 0:
        raise WasteFluidAccountingError("capacity_reserve_mL must be finite and nonnegative")
    if source_capacity_reserve_sha256 is not None:
        if type(source_capacity_reserve_sha256) is not str or len(source_capacity_reserve_sha256) != 64 or any(c not in "0123456789abcdef" for c in source_capacity_reserve_sha256):
            raise WasteFluidAccountingError("capacity reserve provenance must be a canonical lowercase SHA-256 digest")
    retained_capacity = budget.cartridge_retained_capacity_requirement_mL
    if capacity_reserve_mL >= retained_capacity:
        raise WasteFluidAccountingError("capacity_reserve_mL must be smaller than cartridge retained-capacity requirement")

    routing = screen_cycle_resolved_routing_closure(
        budget, prime_events_by_cycle=prime_events_by_cycle,
        prime_recovery_ratio_contract=prime_recovery_ratio_contract,
        prime_residual_ratio_contract=prime_residual_ratio_contract,
        prime_external_leakage_ratio_contract=prime_external_leakage_ratio_contract,
    )
    usable_capacity = retained_capacity - capacity_reserve_mL
    unavoidable_state = next((s for s in routing.cycles if s.cumulative_minimum_cartridge_routing_mL > usable_capacity + _TOL), None)
    conservative_state = next((s for s in routing.cycles if s.cumulative_maximum_cartridge_inflow_mL > usable_capacity + _TOL), None)
    unavoidable_cycle = None if unavoidable_state is None else unavoidable_state.cycle
    conservative_cycle = None if conservative_state is None else conservative_state.cycle
    if unavoidable_cycle is not None and (conservative_cycle is None or unavoidable_cycle < conservative_cycle):
        raise WasteFluidAccountingError("invalid capacity ordering: minimum-routing overflow precedes conservative inflow overflow")

    minimum_overflow = 0.0 if unavoidable_state is None else max(0.0, unavoidable_state.cumulative_minimum_cartridge_routing_mL - usable_capacity)
    conservative_overflow = 0.0 if conservative_state is None else max(0.0, conservative_state.cumulative_maximum_cartridge_inflow_mL - usable_capacity)
    final = routing.cycles[-1]
    contractual_required = final.cumulative_minimum_cartridge_routing_mL
    conservative_required = final.cumulative_maximum_cartridge_inflow_mL

    return CartridgeOverflowGuard(
        routing=routing, retained_capacity_mL=retained_capacity,
        capacity_reserve_mL=capacity_reserve_mL, usable_capacity_mL=usable_capacity,
        contractual_required_usable_capacity_mL=contractual_required,
        conservative_required_usable_capacity_mL=conservative_required,
        first_unavoidable_overflow_cycle=unavoidable_cycle,
        first_conservative_capacity_failure_cycle=conservative_cycle,
        minimum_overflow_at_failure_mL=minimum_overflow,
        conservative_overflow_at_failure_mL=conservative_overflow,
        contractual_reserve_headroom_mL=usable_capacity - contractual_required,
        conservative_reserve_headroom_mL=usable_capacity - conservative_required,
        source_capacity_reserve_sha256=source_capacity_reserve_sha256,
    )
