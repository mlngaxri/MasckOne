"""Cartridge overflow guard derived from cycle-resolved fluid accounting."""
from __future__ import annotations

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
    cartridge requirement. ``conservative_fit_unproven`` means minimum routing
    fits but the fail-conservative introduced-volume bound does not. Neither is
    a physical retained-volume prediction.
    """

    routing: CycleResolvedRoutingClosure
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
) -> CartridgeOverflowGuard:
    """Classify cartridge capacity without granting unsupported sink credit."""
    routing = screen_cycle_resolved_routing_closure(
        budget,
        prime_events_by_cycle=prime_events_by_cycle,
        prime_recovery_ratio_contract=prime_recovery_ratio_contract,
        prime_residual_ratio_contract=prime_residual_ratio_contract,
        prime_external_leakage_ratio_contract=prime_external_leakage_ratio_contract,
    )
    unavoidable_cycle = routing.first_unavoidable_cartridge_capacity_exceeded_cycle
    conservative_cycle = routing.first_cartridge_capacity_exceeded_cycle

    if unavoidable_cycle is not None and conservative_cycle is None:
        raise WasteFluidAccountingError(
            "invalid capacity state: contractual minimum routing exceeds capacity while conservative inflow does not"
        )
    if unavoidable_cycle is not None and conservative_cycle is not None and unavoidable_cycle < conservative_cycle:
        raise WasteFluidAccountingError(
            "invalid capacity ordering: minimum-routing overflow precedes conservative inflow overflow"
        )

    minimum_overflow = 0.0
    if unavoidable_cycle is not None:
        minimum_overflow = max(
            0.0,
            -routing.cycles[unavoidable_cycle - 1].minimum_routing_capacity_margin_mL,
        )

    conservative_overflow = 0.0
    if conservative_cycle is not None:
        conservative_overflow = max(
            0.0,
            -routing.cycles[conservative_cycle - 1].cartridge_capacity_margin_mL,
        )

    return CartridgeOverflowGuard(
        routing=routing,
        first_unavoidable_overflow_cycle=unavoidable_cycle,
        first_conservative_capacity_failure_cycle=conservative_cycle,
        minimum_overflow_at_failure_mL=minimum_overflow,
        conservative_overflow_at_failure_mL=conservative_overflow,
    )
