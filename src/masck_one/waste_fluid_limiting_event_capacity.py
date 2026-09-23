"""Independent cartridge-capacity screen at the reprime service boundary.

This is requirement arithmetic only. It deliberately separates sink closure from
cartridge capacity by screening the first limiting reprime event at the maximum
physically possible nominal recovery, so a sink-first failure cannot be mistaken
for a simultaneous cartridge-capacity failure.
"""
from __future__ import annotations

from dataclasses import dataclass

from .waste_fluid_accounting import WasteFluidBudget
from .waste_fluid_service_envelope import ReprimeServiceEnvelope, evaluate_reprime_service_envelope


@dataclass(frozen=True, slots=True)
class LimitingEventCapacityScreen:
    service_envelope: ReprimeServiceEnvelope
    limiting_prime_events: int
    nominal_liquid_at_maximum_recovery_mL: float
    nominal_only_cartridge_headroom_mL: float
    nominal_only_cartridge_overflow_mL: float
    prime_cartridge_capacity_allowance_mL: float
    prime_liquid_routed_to_cartridge_mL: float
    prime_cartridge_allowance_margin_mL: float
    cartridge_demand_at_maximum_nominal_recovery_mL: float
    retained_cartridge_capacity_mL: float
    cartridge_margin_at_maximum_nominal_recovery_mL: float
    cartridge_headroom_at_maximum_nominal_recovery_mL: float
    cartridge_overflow_at_maximum_nominal_recovery_mL: float
    cartridge_utilization_at_maximum_nominal_recovery: float
    cartridge_capacity_exceeded_at_maximum_nominal_recovery: bool


def screen_limiting_event_cartridge_capacity(
    budget: WasteFluidBudget,
    *,
    cycles: int,
    prime_recovery_ratio_contract: float,
    prime_residual_ratio_contract: float,
    prime_external_leakage_ratio_contract: float,
) -> LimitingEventCapacityScreen:
    """Screen cartridge capacity independently at the first limiting prime event.

    The nominal term is intentionally set to 100% recovery. This is not a claim
    that 100% physical recovery is achievable. It is the conservative cartridge
    load corresponding to the maximum physically possible nominal recovery and
    therefore exposes whether a sink-first boundary still has cartridge headroom.

    The nominal-only split makes a packaging failure diagnosable: nominal service
    demand is screened before any reprime load is added, then the remaining
    retained capacity is exposed as the exact allowance available to recovered
    reprime liquid. A negative prime allowance margin therefore means reprime
    recovery alone consumed more than the capacity left after nominal service.
    """
    envelope = evaluate_reprime_service_envelope(
        budget,
        cycles=cycles,
        prime_recovery_ratio_contract=prime_recovery_ratio_contract,
        prime_residual_ratio_contract=prime_residual_ratio_contract,
        prime_external_leakage_ratio_contract=prime_external_leakage_ratio_contract,
    )
    limiting_events = envelope.limiting_next_prime_events
    nominal_at_maximum_recovery = cycles * budget.nominal_introduced_mL_per_cycle
    prime_to_cartridge = (
        limiting_events
        * budget.maximum_initial_prime_mL_per_cycle
        * float(prime_recovery_ratio_contract)
    )
    capacity = budget.cartridge_retained_capacity_requirement_mL
    if capacity <= 0.0:
        raise ValueError("retained cartridge capacity must be positive")

    nominal_margin = capacity - nominal_at_maximum_recovery
    nominal_headroom = max(nominal_margin, 0.0)
    nominal_overflow = max(-nominal_margin, 0.0)
    prime_allowance = nominal_headroom
    prime_allowance_margin = prime_allowance - prime_to_cartridge

    demand = nominal_at_maximum_recovery + prime_to_cartridge
    margin = capacity - demand
    headroom = max(margin, 0.0)
    overflow = max(-margin, 0.0)
    utilization = demand / capacity
    return LimitingEventCapacityScreen(
        service_envelope=envelope,
        limiting_prime_events=limiting_events,
        nominal_liquid_at_maximum_recovery_mL=nominal_at_maximum_recovery,
        nominal_only_cartridge_headroom_mL=nominal_headroom,
        nominal_only_cartridge_overflow_mL=nominal_overflow,
        prime_cartridge_capacity_allowance_mL=prime_allowance,
        prime_liquid_routed_to_cartridge_mL=prime_to_cartridge,
        prime_cartridge_allowance_margin_mL=prime_allowance_margin,
        cartridge_demand_at_maximum_nominal_recovery_mL=demand,
        retained_cartridge_capacity_mL=capacity,
        cartridge_margin_at_maximum_nominal_recovery_mL=margin,
        cartridge_headroom_at_maximum_nominal_recovery_mL=headroom,
        cartridge_overflow_at_maximum_nominal_recovery_mL=overflow,
        cartridge_utilization_at_maximum_nominal_recovery=utilization,
        cartridge_capacity_exceeded_at_maximum_nominal_recovery=overflow > 0.0,
    )
