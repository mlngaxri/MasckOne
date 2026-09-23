"""Capacity-limited nominal-recovery compatibility at the reprime service boundary.

This is requirement arithmetic only. It asks how much nominal recovery the retained
cartridge can accept after the limiting recovered reprime load is reserved, then
compares that packaging ceiling with the authority recovery floor. It does not
claim measured recovery performance or physical cartridge capacity.
"""
from __future__ import annotations

from dataclasses import dataclass

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
    authority_recovery_floor_capacity_feasible: bool
    full_nominal_recovery_capacity_feasible: bool


def evaluate_recovery_capacity_compatibility(
    budget: WasteFluidBudget,
    screen: LimitingEventCapacityScreen,
) -> RecoveryCapacityCompatibility:
    """Compare cartridge packaging capacity with the required nominal recovery range."""
    if not isinstance(screen, LimitingEventCapacityScreen):
        raise TypeError("recovery capacity compatibility requires LimitingEventCapacityScreen evidence")
    nominal_service = screen.nominal_liquid_at_maximum_recovery_mL
    if nominal_service <= 0.0:
        raise RecoveryCapacityCompatibilityError("nominal introduced service liquid must be positive")
    capacity = screen.retained_cartridge_capacity_mL
    if capacity <= 0.0:
        raise RecoveryCapacityCompatibilityError("retained cartridge capacity must be positive")
    reprime = screen.prime_liquid_routed_to_cartridge_mL
    if reprime < 0.0:
        raise RecoveryCapacityCompatibilityError("recovered reprime load cannot be negative")

    # Cross-check the independent screen against the supplied authority budget so
    # evidence from another cycle count or capacity configuration cannot be mixed in.
    expected_nominal_service = screen.service_envelope.cycles * budget.nominal_introduced_mL_per_cycle
    if abs(nominal_service - expected_nominal_service) > 1e-9:
        raise RecoveryCapacityCompatibilityError("capacity screen nominal service load disagrees with budget")
    if abs(capacity - budget.cartridge_retained_capacity_requirement_mL) > 1e-9:
        raise RecoveryCapacityCompatibilityError("capacity screen retained capacity disagrees with budget")

    authority_floor_ratio = budget.minimum_recovered_mL_per_cycle / budget.nominal_introduced_mL_per_cycle
    if not 0.0 <= authority_floor_ratio <= 1.0:
        raise RecoveryCapacityCompatibilityError("authority nominal recovery floor must lie within [0, 1]")

    # Reprime is an unavoidable reserved load for this screen. Keep its capacity
    # failure distinct from a nominal-recovery incompatibility: clamping the
    # remaining nominal allowance to zero alone would otherwise hide a cartridge
    # that cannot package reprime even at zero nominal recovery.
    reprime_margin = capacity - reprime
    reprime_exceeded = reprime_margin < -1e-12
    available_for_nominal = max(reprime_margin, 0.0)
    capacity_limited_ratio = min(available_for_nominal / nominal_service, 1.0)
    ratio_margin = capacity_limited_ratio - authority_floor_ratio
    floor_feasible = (not reprime_exceeded) and ratio_margin >= -1e-12
    full_feasible = capacity >= nominal_service + reprime - 1e-12

    # The direct compatibility result must agree with both independently screened
    # endpoint states. Any disagreement indicates stale or mixed subsystem evidence.
    if floor_feasible == screen.authority_floor_cartridge_capacity_exceeded:
        raise RecoveryCapacityCompatibilityError("authority-floor capacity compatibility disagrees with limiting-event screen")
    if full_feasible == screen.cartridge_capacity_exceeded_at_maximum_nominal_recovery:
        raise RecoveryCapacityCompatibilityError("full-recovery capacity compatibility disagrees with limiting-event screen")

    return RecoveryCapacityCompatibility(
        nominal_introduced_service_mL=nominal_service,
        recovered_reprime_reserved_mL=reprime,
        reprime_only_capacity_margin_mL=reprime_margin,
        reprime_only_capacity_exceeded=reprime_exceeded,
        capacity_available_for_nominal_recovery_mL=available_for_nominal,
        authority_nominal_recovery_floor_ratio=authority_floor_ratio,
        capacity_limited_nominal_recovery_ratio=capacity_limited_ratio,
        recovery_ratio_margin_above_authority_floor=ratio_margin,
        authority_recovery_floor_capacity_feasible=floor_feasible,
        full_nominal_recovery_capacity_feasible=full_feasible,
    )
