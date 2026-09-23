"""Capacity-limited nominal-recovery compatibility at the reprime service boundary.

This is requirement arithmetic only. It asks how much nominal recovery the retained
cartridge can accept after the limiting recovered reprime load is reserved, then
compares that packaging ceiling with the authority recovery floor. It does not
claim measured recovery performance or physical cartridge capacity.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

from .waste_fluid_accounting import WasteFluidBudget
from .waste_fluid_limiting_event_capacity import LimitingEventCapacityScreen


class RecoveryCapacityCompatibilityError(ValueError):
    """Raised when capacity evidence cannot support a coherent recovery screen."""


@dataclass(frozen=True, slots=True)
class RecoveryCapacityCompatibility:
    nominal_introduced_service_mL: float
    recovered_reprime_reserved_mL: float
    reprime_only_capacity_margin_mL: float
    reprime_only_capacity_exceeded: bool
    capacity_available_for_nominal_recovery_mL: float
    authority_nominal_recovery_floor_ratio: float
    capacity_limited_nominal_recovery_ratio: float
    recovery_ratio_margin_above_authority_floor: float
    minimum_capacity_for_authority_recovery_floor_mL: float
    authority_recovery_floor_capacity_shortfall_mL: float
    minimum_capacity_for_full_nominal_recovery_mL: float
    full_nominal_recovery_capacity_shortfall_mL: float
    capacity_limited_service_cycles_at_authority_floor: int
    capacity_limited_service_cycles_at_full_recovery: int
    authority_service_cycle_shortfall_at_recovery_floor: int
    authority_service_cycle_shortfall_at_full_recovery: int
    authority_recovery_floor_capacity_feasible: bool
    full_nominal_recovery_capacity_feasible: bool


def _require_finite_evidence(**values: float) -> None:
    for name, value in values.items():
        if type(value) not in (int, float) or not math.isfinite(value):
            raise RecoveryCapacityCompatibilityError(f"{name} must be finite numeric evidence")


def evaluate_recovery_capacity_compatibility(budget: WasteFluidBudget, screen: LimitingEventCapacityScreen) -> RecoveryCapacityCompatibility:
    """Compare cartridge packaging capacity with the required nominal recovery range."""
    if not isinstance(screen, LimitingEventCapacityScreen):
        raise TypeError("recovery capacity compatibility requires LimitingEventCapacityScreen evidence")
    envelope = screen.service_envelope
    if envelope.cycles != budget.service_cycles:
        raise RecoveryCapacityCompatibilityError("capacity compatibility requires evidence for exactly the authority service cycle count")
    if screen.limiting_prime_events != envelope.limiting_next_prime_events:
        raise RecoveryCapacityCompatibilityError("capacity screen limiting prime event disagrees with service-envelope evidence")

    # Reconcile the nested closure that actually generated the limiting-event prime load.
    # Without this check, a coherently edited top-level screen could silently detach the
    # reserved reprime volume from its routing contract.
    closure = envelope.first_infeasible.source_closure if envelope.first_infeasible is not None else envelope.maximum_feasible.source_closure
    if closure.cycles != budget.service_cycles:
        raise RecoveryCapacityCompatibilityError("limiting-event source closure service window disagrees with budget")
    if closure.prime_events != screen.limiting_prime_events:
        raise RecoveryCapacityCompatibilityError("limiting-event source closure prime count disagrees with capacity screen")
    recovery_contract = closure.prime_recovery_ratio_contract
    if type(recovery_contract) not in (int, float) or not math.isfinite(recovery_contract):
        raise RecoveryCapacityCompatibilityError("limiting-event prime recovery contract must be finite numeric evidence")
    if not 0.0 <= float(recovery_contract) <= 1.0:
        raise RecoveryCapacityCompatibilityError("limiting-event prime recovery contract must lie within [0, 1]")
    if type(screen.limiting_prime_events) is not int or screen.limiting_prime_events < 0:
        raise RecoveryCapacityCompatibilityError("limiting prime event count must be a non-negative integer")
    expected_reprime = screen.limiting_prime_events * budget.maximum_initial_prime_mL_per_cycle * float(recovery_contract)

    _require_finite_evidence(
        service_envelope_retained_capacity_mL=envelope.maximum_feasible.retained_cartridge_capacity_mL,
        nominal_liquid_at_maximum_recovery_mL=screen.nominal_liquid_at_maximum_recovery_mL,
        retained_cartridge_capacity_mL=screen.retained_cartridge_capacity_mL,
        prime_liquid_routed_to_cartridge_mL=screen.prime_liquid_routed_to_cartridge_mL,
        authority_floor_nominal_recovery_mL=screen.authority_floor_nominal_recovery_mL,
        authority_floor_cartridge_demand_mL=screen.authority_floor_cartridge_demand_mL,
        cartridge_demand_at_maximum_nominal_recovery_mL=screen.cartridge_demand_at_maximum_nominal_recovery_mL,
        authority_floor_cartridge_overflow_mL=screen.authority_floor_cartridge_overflow_mL,
        cartridge_overflow_at_maximum_nominal_recovery_mL=screen.cartridge_overflow_at_maximum_nominal_recovery_mL,
        budget_retained_capacity_mL=budget.cartridge_retained_capacity_requirement_mL,
        budget_nominal_introduced_per_cycle_mL=budget.nominal_introduced_mL_per_cycle,
        budget_minimum_recovered_per_cycle_mL=budget.minimum_recovered_mL_per_cycle,
        budget_maximum_initial_prime_mL_per_cycle=budget.maximum_initial_prime_mL_per_cycle,
        expected_reprime_mL=expected_reprime,
    )
    if abs(screen.prime_liquid_routed_to_cartridge_mL - expected_reprime) > 1e-9:
        raise RecoveryCapacityCompatibilityError("capacity screen recovered reprime load disagrees with limiting-event routing contract")
    if abs(envelope.maximum_feasible.retained_cartridge_capacity_mL - budget.cartridge_retained_capacity_requirement_mL) > 1e-9:
        raise RecoveryCapacityCompatibilityError("service-envelope retained capacity disagrees with budget")
    nominal_service = screen.nominal_liquid_at_maximum_recovery_mL
    if nominal_service <= 0.0:
        raise RecoveryCapacityCompatibilityError("nominal introduced service liquid must be positive")
    capacity = screen.retained_cartridge_capacity_mL
    if capacity <= 0.0:
        raise RecoveryCapacityCompatibilityError("retained cartridge capacity must be positive")
    reprime = screen.prime_liquid_routed_to_cartridge_mL
    if reprime < 0.0:
        raise RecoveryCapacityCompatibilityError("recovered reprime load cannot be negative")

    expected_nominal_service = budget.service_cycles * budget.nominal_introduced_mL_per_cycle
    if abs(nominal_service - expected_nominal_service) > 1e-9:
        raise RecoveryCapacityCompatibilityError("capacity screen nominal service load disagrees with budget")
    if abs(capacity - budget.cartridge_retained_capacity_requirement_mL) > 1e-9:
        raise RecoveryCapacityCompatibilityError("capacity screen retained capacity disagrees with budget")

    authority_floor_ratio = budget.minimum_recovered_mL_per_cycle / budget.nominal_introduced_mL_per_cycle
    if not 0.0 <= authority_floor_ratio <= 1.0:
        raise RecoveryCapacityCompatibilityError("authority nominal recovery floor must lie within [0, 1]")

    expected_floor_nominal = nominal_service * authority_floor_ratio
    expected_floor_demand = expected_floor_nominal + reprime
    expected_full_demand = nominal_service + reprime
    if abs(screen.authority_floor_nominal_recovery_mL - expected_floor_nominal) > 1e-9:
        raise RecoveryCapacityCompatibilityError("capacity screen authority-floor nominal load disagrees with budget")
    if abs(screen.authority_floor_cartridge_demand_mL - expected_floor_demand) > 1e-9:
        raise RecoveryCapacityCompatibilityError("capacity screen authority-floor cartridge demand is stale")
    if abs(screen.cartridge_demand_at_maximum_nominal_recovery_mL - expected_full_demand) > 1e-9:
        raise RecoveryCapacityCompatibilityError("capacity screen full-recovery cartridge demand is stale")

    reprime_margin = capacity - reprime
    reprime_exceeded = reprime_margin < -1e-12
    available_for_nominal = max(reprime_margin, 0.0)
    capacity_limited_ratio = min(available_for_nominal / nominal_service, 1.0)
    ratio_margin = capacity_limited_ratio - authority_floor_ratio
    minimum_floor_capacity = expected_floor_demand
    floor_shortfall = max(minimum_floor_capacity - capacity, 0.0)
    minimum_full_capacity = expected_full_demand
    full_shortfall = max(minimum_full_capacity - capacity, 0.0)
    floor_feasible = (not reprime_exceeded) and floor_shortfall <= 1e-12
    full_feasible = full_shortfall <= 1e-12

    if abs(screen.authority_floor_cartridge_overflow_mL - floor_shortfall) > 1e-9:
        raise RecoveryCapacityCompatibilityError("capacity screen authority-floor overflow is stale")
    if abs(screen.cartridge_overflow_at_maximum_nominal_recovery_mL - full_shortfall) > 1e-9:
        raise RecoveryCapacityCompatibilityError("capacity screen full-recovery overflow is stale")

    nominal_per_cycle = budget.nominal_introduced_mL_per_cycle
    recovered_at_floor_per_cycle = nominal_per_cycle * authority_floor_ratio
    if recovered_at_floor_per_cycle <= 0.0:
        raise RecoveryCapacityCompatibilityError("authority recovered nominal liquid per cycle must be positive")
    raw_floor_cycle_limit = math.floor((available_for_nominal + 1e-12) / recovered_at_floor_per_cycle)
    raw_full_cycle_limit = math.floor((available_for_nominal + 1e-12) / nominal_per_cycle)
    floor_cycle_limit = min(raw_floor_cycle_limit, budget.service_cycles)
    full_cycle_limit = min(raw_full_cycle_limit, budget.service_cycles)
    floor_cycle_shortfall = max(budget.service_cycles - floor_cycle_limit, 0)
    full_cycle_shortfall = max(budget.service_cycles - full_cycle_limit, 0)

    if floor_feasible != ((not reprime_exceeded) and ratio_margin >= -1e-12):
        raise RecoveryCapacityCompatibilityError("capacity shortfall and recovery-ratio compatibility disagree")
    if floor_feasible != ((not reprime_exceeded) and floor_cycle_limit == budget.service_cycles):
        raise RecoveryCapacityCompatibilityError("capacity and service-life compatibility disagree at recovery floor")
    if full_feasible != ((not reprime_exceeded) and full_cycle_limit == budget.service_cycles):
        raise RecoveryCapacityCompatibilityError("capacity and service-life compatibility disagree at full recovery")
    if floor_cycle_limit < full_cycle_limit:
        raise RecoveryCapacityCompatibilityError("recovery-floor service-life bound cannot be below full-recovery bound")
    if floor_feasible == screen.authority_floor_cartridge_capacity_exceeded:
        raise RecoveryCapacityCompatibilityError("authority-floor capacity compatibility disagrees with limiting-event screen")
    if full_feasible == screen.cartridge_capacity_exceeded_at_maximum_nominal_recovery:
        raise RecoveryCapacityCompatibilityError("full-recovery capacity compatibility disagrees with limiting-event screen")

    return RecoveryCapacityCompatibility(
        nominal_service, reprime, reprime_margin, reprime_exceeded, available_for_nominal,
        authority_floor_ratio, capacity_limited_ratio, ratio_margin, minimum_floor_capacity,
        floor_shortfall, minimum_full_capacity, full_shortfall, floor_cycle_limit, full_cycle_limit,
        floor_cycle_shortfall, full_cycle_shortfall, floor_feasible, full_feasible,
    )
