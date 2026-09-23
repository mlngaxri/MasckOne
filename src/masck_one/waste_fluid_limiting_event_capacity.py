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
    prime_liquid_routed_to_cartridge_mL: float
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

    Headroom and overflow are reported separately so downstream integration never
    has to infer overflow from a negative signed margin. Utilization is demand
    divided by retained capacity and therefore exceeds 1.0 exactly when this
    arithmetic screen is over capacity.
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
    demand = nominal_at_maximum_recovery + prime_to_cartridge
    capacity = budget.cartridge_retained_capacity_requirement_mL
    if capacity <= 0.0:
        raise ValueError("retained cartridge capacity must be positive")
    margin = capacity - demand
    headroom = max(margin, 0.0)
    overflow = max(-margin, 0.0)
    utilization = demand / capacity
    return LimitingEventCapacityScreen(
        service_envelope=envelope,
        limiting_prime_events=limiting_events,
        nominal_liquid_at_maximum_recovery_mL=nominal_at_maximum_recovery,
        prime_liquid_routed_to_cartridge_mL=prime_to_cartridge,
        cartridge_demand_at_maximum_nominal_recovery_mL=demand,
        retained_cartridge_capacity_mL=capacity,
        cartridge_margin_at_maximum_nominal_recovery_mL=margin,
        cartridge_headroom_at_maximum_nominal_recovery_mL=headroom,
        cartridge_overflow_at_maximum_nominal_recovery_mL=overflow,
        cartridge_utilization_at_maximum_nominal_recovery=utilization,
        cartridge_capacity_exceeded_at_maximum_nominal_recovery=overflow > 0.0,
    )
