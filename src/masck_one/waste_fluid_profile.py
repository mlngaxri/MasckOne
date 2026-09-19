"""Cycle-resolved digital cartridge loading screens.

This module turns the aggregate waste/fluid budget into an explicit service
sequence so reprime timing and the first capacity breach cannot be hidden by a
single end-of-service total. These are synthetic conservation/capacity checks,
not physical fluid validation.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
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
    minimum_projected_service_end_recovered_mL: float
    projected_mandatory_recovery_margin_mL: float
    mandatory_recovery_service_target_feasible: bool
    maximum_additional_prime_events_for_target: int | None
    reserved_future_prime_events: int
    reserved_future_prime_mL: float
    minimum_projected_service_end_inflow_mL: float
    projected_service_end_margin_mL: float
    maximum_unreserved_prime_events_after_contingency: int | None
    service_target_feasible: bool


@dataclass(frozen=True)
class ServiceFluidProfile:
    cycles: tuple[CycleFluidState, ...]
    target_cycles: int
    future_prime_events_per_remaining_cycle: int
    first_overflow_cycle: int | None
    first_mandatory_recovery_overflow_cycle: int | None
    first_mandatory_recovery_target_infeasible_cycle: int | None
    first_target_infeasible_cycle: int | None

    @property
    def capacity_satisfied(self) -> bool:
        return self.first_overflow_cycle is None

    @property
    def mandatory_recovery_capacity_satisfied(self) -> bool:
        return self.first_mandatory_recovery_overflow_cycle is None

    @property
    def mandatory_recovery_service_target_feasible(self) -> bool:
        return self.first_mandatory_recovery_target_infeasible_cycle is None

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
    future_prime_events_per_remaining_cycle: int = 0,
) -> ServiceFluidProfile:
    """Screen cumulative cartridge loading at every service-cycle boundary.

    ``prime_events_by_cycle`` records actual or assumed reprime counts for each
    observed or planned cycle. Multiple reprimes in one cycle are allowed because
    no authority limit currently constrains their count. Every prime is charged at
    the full authority prime allowance and no recovery, residual, or leakage credit
    is taken in the upper occupancy bound.

    ``future_prime_events_per_remaining_cycle`` reserves a caller-selected reprime
    contingency for each unprofiled target cycle. Zero remains the default because
    no authority currently mandates a future reprime count.

    ``maximum_additional_prime_events_for_target`` reports raw reprime capacity
    after reserving nominal liquid through the target cycle. The separate
    ``maximum_unreserved_prime_events_after_contingency`` reports spare reprime
    capacity only after the selected future-prime contingency has also been charged.
    Neither value is a control limit or a prediction of reprime demand. ``None``
    means prime volume is zero and therefore does not consume capacity.

    Each state carries the lower occupancy bound implied by minimum nominal
    recovery. Prime recovery is excluded because no authority recovery fraction
    exists for prime liquid. The screen also reserves the mandatory nominal recovery
    for every remaining target cycle. This makes a cartridge that cannot hold the
    waste it is required to recover fail before that physical occupancy is reached.

    The fail-conservative projection reserves all nominal liquid plus the selected
    future-prime contingency for remaining target cycles. The target is bounded by
    the configured cartridge service life so callers cannot silently extrapolate the
    same cartridge beyond its authority service interval. These are digital bounds,
    not retained-volume or recovery predictions.
    """
    budget.validate()
    if not prime_events_by_cycle:
        raise WasteFluidAccountingError("service profile must contain at least one cycle")
    if target_cycles is None:
        target_cycles = budget.service_cycles
    if type(target_cycles) is not int or target_cycles <= 0:
        raise WasteFluidAccountingError("target_cycles must be a positive integer")
    if target_cycles > budget.service_cycles:
        raise WasteFluidAccountingError("target_cycles exceeds configured service life")
    if target_cycles < len(prime_events_by_cycle):
        raise WasteFluidAccountingError("target_cycles cannot be less than the profiled cycle count")
    if type(future_prime_events_per_remaining_cycle) is not int or future_prime_events_per_remaining_cycle < 0:
        raise WasteFluidAccountingError("future_prime_events_per_remaining_cycle must be a nonnegative integer")

    states: list[CycleFluidState] = []
    cumulative_primes = 0
    first_overflow: int | None = None
    first_mandatory_recovery_overflow: int | None = None
    first_mandatory_recovery_target_infeasible: int | None = None
    first_target_infeasible: int | None = None

    for cycle, prime_events in enumerate(prime_events_by_cycle, start=1):
        if type(prime_events) is not int or prime_events < 0:
            raise WasteFluidAccountingError("prime_events_by_cycle values must be nonnegative integers")
        cumulative_primes += prime_events
        aggregate = budget.service_capacity_screen(cycles=cycle, prime_events=cumulative_primes)
        remaining_cycles = target_cycles - cycle

        projected_mandatory_recovery = aggregate.minimum_recovered_nominal_mL + remaining_cycles * budget.minimum_recovered_mL_per_cycle
        projected_mandatory_recovery_margin = budget.cartridge_retained_capacity_requirement_mL - projected_mandatory_recovery
        mandatory_recovery_target_feasible = projected_mandatory_recovery_margin >= -1e-12

        nominal_target_inflow = aggregate.maximum_cartridge_inflow_mL + remaining_cycles * budget.nominal_introduced_mL_per_cycle
        prime_headroom_mL = budget.cartridge_retained_capacity_requirement_mL - nominal_target_inflow
        if budget.maximum_initial_prime_mL_per_cycle == 0.0:
            maximum_additional_primes = None
        else:
            maximum_additional_primes = max(0, math.floor((prime_headroom_mL + 1e-12) / budget.maximum_initial_prime_mL_per_cycle))

        reserved_future_prime_events = remaining_cycles * future_prime_events_per_remaining_cycle
        reserved_future_prime_mL = reserved_future_prime_events * budget.maximum_initial_prime_mL_per_cycle
        projected_end_inflow = nominal_target_inflow + reserved_future_prime_mL
        projected_end_margin = budget.cartridge_retained_capacity_requirement_mL - projected_end_inflow
        target_feasible = projected_end_margin >= -1e-12
        if budget.maximum_initial_prime_mL_per_cycle == 0.0:
            maximum_unreserved_primes = None
        elif target_feasible:
            maximum_unreserved_primes = max(0, math.floor((projected_end_margin + 1e-12) / budget.maximum_initial_prime_mL_per_cycle))
        else:
            maximum_unreserved_primes = 0
        minimum_recovery_capacity_satisfied = aggregate.minimum_recovered_nominal_mL <= budget.cartridge_retained_capacity_requirement_mL + 1e-12
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
            minimum_projected_service_end_recovered_mL=projected_mandatory_recovery,
            projected_mandatory_recovery_margin_mL=projected_mandatory_recovery_margin,
            mandatory_recovery_service_target_feasible=mandatory_recovery_target_feasible,
            maximum_additional_prime_events_for_target=maximum_additional_primes,
            reserved_future_prime_events=reserved_future_prime_events,
            reserved_future_prime_mL=reserved_future_prime_mL,
            minimum_projected_service_end_inflow_mL=projected_end_inflow,
            projected_service_end_margin_mL=projected_end_margin,
            maximum_unreserved_prime_events_after_contingency=maximum_unreserved_primes,
            service_target_feasible=target_feasible,
        )
        states.append(state)
        if first_overflow is None and not state.capacity_satisfied:
            first_overflow = cycle
        if first_mandatory_recovery_overflow is None and not state.minimum_recovery_capacity_satisfied:
            first_mandatory_recovery_overflow = cycle
        if first_mandatory_recovery_target_infeasible is None and not state.mandatory_recovery_service_target_feasible:
            first_mandatory_recovery_target_infeasible = cycle
        if first_target_infeasible is None and not state.service_target_feasible:
            first_target_infeasible = cycle

    return ServiceFluidProfile(tuple(states), target_cycles, future_prime_events_per_remaining_cycle, first_overflow, first_mandatory_recovery_overflow, first_mandatory_recovery_target_infeasible, first_target_infeasible)
