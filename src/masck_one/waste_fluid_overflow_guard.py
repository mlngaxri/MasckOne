"""Cartridge overflow guard derived from cycle-resolved fluid accounting."""
from __future__ import annotations

import math
from dataclasses import dataclass

from .waste_fluid_accounting import WasteFluidAccountingError, WasteFluidBudget
from .waste_fluid_cycle_routing import (
    CycleResolvedRoutingClosure,
    screen_cycle_resolved_routing_closure,
)


@dataclass(frozen=True)
class CartridgeOverflowGuard:
    """Capacity disposition for an explicit service-cycle reprime schedule.

    ``unavoidable_overflow`` means contractual minimum routing alone exceeds the
    usable cartridge capacity after an explicit reserve. ``conservative_fit_unproven``
    means minimum routing fits but the fail-conservative introduced-volume bound does
    not. Neither is a physical retained-volume prediction.
    """

    routing: CycleResolvedRoutingClosure
    capacity_reserve_mL: float
    usable_capacity_mL: float
    first_unavoidable_overflow_cycle: int | None
    first_conservative_capacity_failure_cycle: int | None
    minimum_overflow_at_failure_mL: float
    conservative_overflow_at_failure_mL: float

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
    budget: WasteFluidBudget,
    *,
    prime_events_by_cycle: tuple[int, ...] | list[int],
    prime_recovery_ratio_contract: float | None = None,
    prime_residual_ratio_contract: float | None = None,
    prime_external_leakage_ratio_contract: float | None = None,
    capacity_reserve_mL: float = 0.0,
) -> CartridgeOverflowGuard:
    """Classify cartridge capacity without granting unsupported sink credit.

    ``capacity_reserve_mL`` removes explicitly unavailable volume from the nominal
    retained-capacity requirement. It can represent a separately justified fill
    limit, sensor trip reserve, foam allowance, manufacturing tolerance, or other
    integration reserve. The default is zero so this screen does not invent one.
    """
    budget.validate()
    if not isinstance(capacity_reserve_mL, (int, float)) or isinstance(capacity_reserve_mL, bool):
        raise WasteFluidAccountingError("capacity_reserve_mL must be a finite numeric value")
    capacity_reserve_mL = float(capacity_reserve_mL)
    if not math.isfinite(capacity_reserve_mL) or capacity_reserve_mL < 0:
        raise WasteFluidAccountingError("capacity_reserve_mL must be finite and nonnegative")
    if capacity_reserve_mL >= budget.cartridge_retained_capacity_requirement_mL:
        raise WasteFluidAccountingError(
            "capacity_reserve_mL must be smaller than cartridge retained-capacity requirement"
        )

    routing = screen_cycle_resolved_routing_closure(
        budget,
        prime_events_by_cycle=prime_events_by_cycle,
        prime_recovery_ratio_contract=prime_recovery_ratio_contract,
        prime_residual_ratio_contract=prime_residual_ratio_contract,
        prime_external_leakage_ratio_contract=prime_external_leakage_ratio_contract,
    )
    usable_capacity = budget.cartridge_retained_capacity_requirement_mL - capacity_reserve_mL

    unavoidable_cycle = next(
        (
            state.cycle
            for state in routing.cycles
            if state.cumulative_minimum_cartridge_routing_mL > usable_capacity + 1e-12
        ),
        None,
    )
    conservative_cycle = next(
        (
            state.cycle
            for state in routing.cycles
            if state.cumulative_maximum_cartridge_inflow_mL > usable_capacity + 1e-12
        ),
        None,
    )

    if unavoidable_cycle is not None and conservative_cycle is None:
        raise WasteFluidAccountingError(
            "invalid capacity state: contractual minimum routing exceeds usable capacity while conservative inflow does not"
        )
    if unavoidable_cycle is not None and conservative_cycle is not None and unavoidable_cycle < conservative_cycle:
        raise WasteFluidAccountingError(
            "invalid capacity ordering: minimum-routing overflow precedes conservative inflow overflow"
        )

    minimum_overflow = 0.0
    if unavoidable_cycle is not None:
        state = routing.cycles[unavoidable_cycle - 1]
        minimum_overflow = max(0.0, state.cumulative_minimum_cartridge_routing_mL - usable_capacity)

    conservative_overflow = 0.0
    if conservative_cycle is not None:
        state = routing.cycles[conservative_cycle - 1]
        conservative_overflow = max(0.0, state.cumulative_maximum_cartridge_inflow_mL - usable_capacity)

    return CartridgeOverflowGuard(
        routing=routing,
        capacity_reserve_mL=capacity_reserve_mL,
        usable_capacity_mL=usable_capacity,
        first_unavoidable_overflow_cycle=unavoidable_cycle,
        first_conservative_capacity_failure_cycle=conservative_cycle,
        minimum_overflow_at_failure_mL=minimum_overflow,
        conservative_overflow_at_failure_mL=conservative_overflow,
    )
