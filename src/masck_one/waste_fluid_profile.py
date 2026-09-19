"""Cycle-resolved digital cartridge loading screens.

This module turns the aggregate waste/fluid budget into an explicit service
sequence so reprime timing and the first capacity breach cannot be hidden by a
single end-of-service total. These are synthetic conservation/capacity checks,
not physical fluid validation.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .waste_fluid_accounting import (
    WasteFluidAccountingError,
    WasteFluidBudget,
)


@dataclass(frozen=True)
class CycleFluidState:
    cycle: int
    prime_events_this_cycle: int
    cumulative_prime_events: int
    cumulative_nominal_mL: float
    cumulative_prime_mL: float
    maximum_cartridge_inflow_mL: float
    requirement_margin_mL: float
    capacity_satisfied: bool


@dataclass(frozen=True)
class ServiceFluidProfile:
    cycles: tuple[CycleFluidState, ...]
    first_overflow_cycle: int | None

    @property
    def capacity_satisfied(self) -> bool:
        return self.first_overflow_cycle is None

    @property
    def final(self) -> CycleFluidState:
        return self.cycles[-1]


def screen_service_profile(
    budget: WasteFluidBudget,
    *,
    prime_events_by_cycle: Sequence[int],
) -> ServiceFluidProfile:
    """Screen cumulative cartridge loading at every service-cycle boundary.

    ``prime_events_by_cycle`` records actual or assumed reprime counts for each
    cycle. Multiple reprimes in one cycle are allowed because no authority limit
    currently constrains their count. Every prime is charged at the full authority
    prime allowance and no recovery, residual, or leakage credit is taken.
    """
    if not prime_events_by_cycle:
        raise WasteFluidAccountingError("service profile must contain at least one cycle")

    states: list[CycleFluidState] = []
    cumulative_primes = 0
    first_overflow: int | None = None

    for cycle, prime_events in enumerate(prime_events_by_cycle, start=1):
        if type(prime_events) is not int or prime_events < 0:
            raise WasteFluidAccountingError(
                "prime_events_by_cycle values must be nonnegative integers"
            )
        cumulative_primes += prime_events
        aggregate = budget.service_capacity_screen(
            cycles=cycle,
            prime_events=cumulative_primes,
        )
        state = CycleFluidState(
            cycle=cycle,
            prime_events_this_cycle=prime_events,
            cumulative_prime_events=cumulative_primes,
            cumulative_nominal_mL=aggregate.nominal_liquid_mL,
            cumulative_prime_mL=aggregate.prime_liquid_mL,
            maximum_cartridge_inflow_mL=aggregate.maximum_cartridge_inflow_mL,
            requirement_margin_mL=aggregate.requirement_margin_mL,
            capacity_satisfied=aggregate.capacity_satisfied,
        )
        states.append(state)
        if first_overflow is None and not state.capacity_satisfied:
            first_overflow = cycle

    return ServiceFluidProfile(tuple(states), first_overflow)
