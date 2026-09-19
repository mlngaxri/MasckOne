"""Cycle-resolved digital cartridge loading screens.

This module turns the aggregate waste/fluid budget into an explicit service
sequence so reprime timing and the first capacity breach cannot be hidden by a
single end-of-service total. These are synthetic conservation/capacity checks,
not physical fluid validation.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .waste_fluid_accounting import WasteFluidAccountingError, WasteFluidBudget


@dataclass(frozen=True)
class CycleFluidState:
    cycle: int
    prime_events_this_cycle: int
    cumulative_prime_events: int
    cumulative_nominal_mL: float
    cumulative_prime_mL: float
    minimum_recovered_nominal_mL: float
    maximum_cartridge_inflow_mL: float
    occupancy_uncertainty_mL: float
    requirement_margin_mL: float
    capacity_satisfied: bool
    minimum_recovery_capacity_satisfied: bool
    minimum_projected_service_end_inflow_mL: float
    projected_service_end_margin_mL: float
    service_target_feasible: bool


@dataclass(frozen=True)
class ServiceFluidProfile:
    cycles: tuple[CycleFluidState, ...]
    target_cycles: int
    first_overflow_cycle: int | None
    first_mandatory_recovery_overflow_cycle: int | None
    first_target_infeasible_cycle: int | None

    @property
    def capacity_satisfied(self) -> bool:
        return self.first_overflow_cycle is None

    @property
    def mandatory_recovery_capacity_satisfied(self) -> bool:
        return self.first_mandatory_recovery_overflow_cycle is None

    @property
    def service_target_feasible(self) -> bool:
        return self.first_target_infeasible_cycle is None

    @property
    def final(self) -> CycleFluidState:
        return self.cycles[-1]


def screen_service_profile(
    budget: WasteFluidBudget,
    *,
    prime_events_by_cycle: Sequence[int],
    target_cycles: int | None = None,
) -> ServiceFluidProfile:
    """Screen cumulative cartridge loading at every service-cycle boundary.

    ``prime_events_by_cycle`` records actual or assumed reprime counts for each
    observed or planned cycle. Multiple reprimes in one cycle are allowed because
    no authority limit currently constrains their count. Every prime is charged at
    the full authority prime allowance and no recovery, residual, or leakage credit
    is taken in the upper occupancy bound.

    Each state also carries the lower occupancy bound implied by the minimum nominal
    recovery requirement. Prime recovery is deliberately excluded from that lower
    bound because no authority recovery fraction exists for prime liquid. Keeping
    both bounds visible prevents an uncertain occupancy interval from being mistaken
    for a physical retained-volume prediction.

    At each boundary the screen reserves nominal liquid for every cycle still needed
    to reach ``target_cycles``. This catches a reprime-heavy early sequence that has
    not overflowed yet but has already consumed too much capacity to finish the
    intended service life. Future reprimes are not assumed in this projection, so an
    infeasible result is fail-closed even under the best remaining prime case.
    """
    if not prime_events_by_cycle:
        raise WasteFluidAccountingError("service profile must contain at least one cycle")
    if target_cycles is None:
        target_cycles = budget.service_cycles
    if type(target_cycles) is not int or target_cycles <= 0:
        raise WasteFluidAccountingError("target_cycles must be a positive integer")
    if target_cycles < len(prime_events_by_cycle):
        raise WasteFluidAccountingError("target_cycles cannot be less than the profiled cycle count")

    states: list[CycleFluidState] = []
    cumulative_primes = 0
    first_overflow: int | None = None
    first_mandatory_recovery_overflow: int | None = None
    first_target_infeasible: int | None = None

    for cycle, prime_events in enumerate(prime_events_by_cycle, start=1):
        if type(prime_events) is not int or prime_events < 0:
            raise WasteFluidAccountingError("prime_events_by_cycle values must be nonnegative integers")
        cumulative_primes += prime_events
        aggregate = budget.service_capacity_screen(cycles=cycle, prime_events=cumulative_primes)
        remaining_cycles = target_cycles - cycle
        projected_end_inflow = (
            aggregate.maximum_cartridge_inflow_mL
            + remaining_cycles * budget.nominal_introduced_mL_per_cycle
        )
        projected_end_margin = budget.cartridge_retained_capacity_requirement_mL - projected_end_inflow
        target_feasible = projected_end_margin >= -1e-12
        minimum_recovery_capacity_satisfied = (
            aggregate.minimum_recovered_nominal_mL
            <= budget.cartridge_retained_capacity_requirement_mL + 1e-12
        )
        state = CycleFluidState(
            cycle=cycle,
            prime_events_this_cycle=prime_events,
            cumulative_prime_events=cumulative_primes,
            cumulative_nominal_mL=aggregate.nominal_liquid_mL,
            cumulative_prime_mL=aggregate.prime_liquid_mL,
            minimum_recovered_nominal_mL=aggregate.minimum_recovered_nominal_mL,
            maximum_cartridge_inflow_mL=aggregate.maximum_cartridge_inflow_mL,
            occupancy_uncertainty_mL=aggregate.occupancy_uncertainty_mL,
            requirement_margin_mL=aggregate.requirement_margin_mL,
            capacity_satisfied=aggregate.capacity_satisfied,
            minimum_recovery_capacity_satisfied=minimum_recovery_capacity_satisfied,
            minimum_projected_service_end_inflow_mL=projected_end_inflow,
            projected_service_end_margin_mL=projected_end_margin,
            service_target_feasible=target_feasible,
        )
        states.append(state)
        if first_overflow is None and not state.capacity_satisfied:
            first_overflow = cycle
        if first_mandatory_recovery_overflow is None and not state.minimum_recovery_capacity_satisfied:
            first_mandatory_recovery_overflow = cycle
        if first_target_infeasible is None and not state.service_target_feasible:
            first_target_infeasible = cycle

    return ServiceFluidProfile(
        tuple(states),
        target_cycles,
        first_overflow,
        first_mandatory_recovery_overflow,
        first_target_infeasible,
    )
