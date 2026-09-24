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
    capacity_reserve_mL: float
    usable_capacity_mL: float
    first_overflow_cycle: int | None
    first_mandatory_recovery_overflow_cycle: int | None
    first_mandatory_recovery_target_infeasible_cycle: int | None
    first_target_infeasible_cycle: int | None
    source_capacity_reserve_sha256: str | None = None

    def __post_init__(self) -> None:
        if self.source_capacity_reserve_sha256 is not None:
            value = self.source_capacity_reserve_sha256
            if type(value) is not str or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
                raise WasteFluidAccountingError("capacity reserve provenance must be a canonical lowercase SHA-256 digest")

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
    capacity_reserve_mL: float = 0.0,
    source_capacity_reserve_sha256: str | None = None,
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

    ``capacity_reserve_mL`` removes explicitly unavailable volume from the retained
    capacity requirement. It is applied to every current and projected capacity
    decision in this profile, including mandatory-recovery feasibility and reprime
    headroom. The default is zero because no physical fill/foam/tolerance reserve is
    assumed here. This keeps service-life projections consistent with the overflow
    guard when an integration reserve is supplied.

    ``source_capacity_reserve_sha256`` optionally binds a typed reserve composition
    to this scalar capacity screen. It is provenance only and does not change any
    volume calculation.

    These are digital bounds, not retained-volume or recovery predictions.
    """
    budget.validate()
    if not isinstance(capacity_reserve_mL, (int, float)) or isinstance(capacity_reserve_mL, bool):
        raise WasteFluidAccountingError("capacity_reserve_mL must be a finite numeric value")
    capacity_reserve_mL = float(capacity_reserve_mL)
    if not math.isfinite(capacity_reserve_mL) or capacity_reserve_mL < 0:
        raise WasteFluidAccountingError("capacity_reserve_mL must be finite and nonnegative")
    if capacity_reserve_mL >= budget.cartridge_retained_capacity_requirement_mL:
        raise WasteFluidAccountingError("capacity_reserve_mL must be smaller than cartridge retained-capacity requirement")
    if source_capacity_reserve_sha256 is not None:
        if type(source_capacity_reserve_sha256) is not str or len(source_capacity_reserve_sha256) != 64 or any(c not in "0123456789abcdef" for c in source_capacity_reserve_sha256):
            raise WasteFluidAccountingError("capacity reserve provenance must be a canonical lowercase SHA-256 digest")
    usable_capacity = budget.cartridge_retained_capacity_requirement_mL - capacity_reserve_mL

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
    first_overflow = first_mandatory_recovery_overflow = None
    first_mandatory_recovery_target_infeasible = first_target_infeasible = None

    for cycle, prime_events in enumerate(prime_events_by_cycle, start=1):
        if type(prime_events) is not int or prime_events < 0:
            raise WasteFluidAccountingError("prime_events_by_cycle values must be nonnegative integers")
        cumulative_primes += prime_events
        aggregate = budget.service_capacity_screen(cycles=cycle, prime_events=cumulative_primes)
        remaining_cycles = target_cycles - cycle
        current_margin = usable_capacity - aggregate.maximum_cartridge_inflow_mL
        current_capacity_satisfied = current_margin >= -1e-12
        minimum_recovery_capacity_satisfied = aggregate.minimum_recovered_nominal_mL <= usable_capacity + 1e-12
        projected_mandatory_recovery = aggregate.minimum_recovered_nominal_mL + remaining_cycles * budget.minimum_recovered_mL_per_cycle
        projected_mandatory_recovery_margin = usable_capacity - projected_mandatory_recovery
        mandatory_recovery_target_feasible = projected_mandatory_recovery_margin >= -1e-12
        nominal_target_inflow = aggregate.maximum_cartridge_inflow_mL + remaining_cycles * budget.nominal_introduced_mL_per_cycle
        prime_headroom_mL = usable_capacity - nominal_target_inflow
        maximum_additional_primes = None if budget.maximum_initial_prime_mL_per_cycle == 0.0 else max(0, math.floor((prime_headroom_mL + 1e-12) / budget.maximum_initial_prime_mL_per_cycle))
        reserved_future_prime_events = remaining_cycles * future_prime_events_per_remaining_cycle
        reserved_future_prime_mL = reserved_future_prime_events * budget.maximum_initial_prime_mL_per_cycle
        projected_end_inflow = nominal_target_inflow + reserved_future_prime_mL
        projected_end_margin = usable_capacity - projected_end_inflow
        target_feasible = projected_end_margin >= -1e-12
        if budget.maximum_initial_prime_mL_per_cycle == 0.0:
            maximum_unreserved_primes = None
        elif target_feasible:
            maximum_unreserved_primes = max(0, math.floor((projected_end_margin + 1e-12) / budget.maximum_initial_prime_mL_per_cycle))
        else:
            maximum_unreserved_primes = 0
        state = CycleFluidState(cycle, prime_events, cumulative_primes, aggregate.nominal_liquid_mL, aggregate.prime_liquid_mL, aggregate.minimum_recovered_nominal_mL, aggregate.maximum_cartridge_inflow_mL, aggregate.occupancy_uncertainty_mL, current_margin, current_capacity_satisfied, minimum_recovery_capacity_satisfied, projected_mandatory_recovery, projected_mandatory_recovery_margin, mandatory_recovery_target_feasible, maximum_additional_primes, reserved_future_prime_events, reserved_future_prime_mL, projected_end_inflow, projected_end_margin, maximum_unreserved_primes, target_feasible)
        states.append(state)
        if first_overflow is None and not state.capacity_satisfied: first_overflow = cycle
        if first_mandatory_recovery_overflow is None and not state.minimum_recovery_capacity_satisfied: first_mandatory_recovery_overflow = cycle
        if first_mandatory_recovery_target_infeasible is None and not state.mandatory_recovery_service_target_feasible: first_mandatory_recovery_target_infeasible = cycle
        if first_target_infeasible is None and not state.service_target_feasible: first_target_infeasible = cycle

    return ServiceFluidProfile(tuple(states), target_cycles, future_prime_events_per_remaining_cycle, capacity_reserve_mL, usable_capacity, first_overflow, first_mandatory_recovery_overflow, first_mandatory_recovery_target_infeasible, first_target_infeasible, source_capacity_reserve_sha256)
