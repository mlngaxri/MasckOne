"""Independent cartridge-capacity screen at the reprime service boundary.

This is requirement arithmetic only. It deliberately separates sink closure from
cartridge capacity by screening the first limiting reprime event at both the
authority nominal-recovery floor and maximum physically possible nominal recovery.
"""
from __future__ import annotations

from dataclasses import dataclass

from .waste_fluid_accounting import WasteFluidBudget
from .waste_fluid_service_envelope import ReprimeServiceEnvelope, evaluate_reprime_service_envelope


@dataclass(frozen=True, slots=True)
class LimitingEventCapacityScreen:
    service_envelope: ReprimeServiceEnvelope
    limiting_prime_events: int
    authority_floor_nominal_recovery_mL: float
    authority_floor_nominal_only_headroom_mL: float
    authority_floor_nominal_only_overflow_mL: float
    authority_floor_nominal_capacity_exceeded: bool
    authority_floor_prime_capacity_allowance_mL: float
    authority_floor_prime_allowance_margin_mL: float
    authority_floor_prime_incremental_overflow_mL: float
    authority_floor_capacity_exceeded_by_reprime: bool
    authority_floor_cartridge_demand_mL: float
    authority_floor_cartridge_margin_mL: float
    authority_floor_cartridge_headroom_mL: float
    authority_floor_cartridge_overflow_mL: float
    authority_floor_cartridge_utilization: float
    authority_floor_cartridge_capacity_exceeded: bool
    nominal_recovery_uplift_to_maximum_mL: float
    nominal_recovery_uplift_capacity_allowance_mL: float
    nominal_recovery_uplift_allowance_margin_mL: float
    nominal_recovery_uplift_incremental_overflow_mL: float
    capacity_exceeded_by_nominal_recovery_uplift: bool
    nominal_liquid_at_maximum_recovery_mL: float
    nominal_only_cartridge_headroom_mL: float
    nominal_only_cartridge_overflow_mL: float
    nominal_capacity_exceeded_at_maximum_recovery: bool
    prime_cartridge_capacity_allowance_mL: float
    prime_liquid_routed_to_cartridge_mL: float
    prime_cartridge_allowance_margin_mL: float
    prime_incremental_cartridge_overflow_mL: float
    capacity_exceeded_by_reprime_at_maximum_recovery: bool
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

    Two nominal-recovery states are retained deliberately. The authority-floor
    state exposes whether the contractual minimum recovery plus recovered reprime
    liquid already overfills the cartridge. The maximum-recovery state exposes the
    opposite packaging extreme, where every nominal millilitre reaches the
    cartridge. Neither state is a claim of measured physical recovery.
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
    nominal_at_authority_floor = cycles * budget.minimum_recovered_mL_per_cycle
    prime_to_cartridge = limiting_events * budget.maximum_initial_prime_mL_per_cycle * float(prime_recovery_ratio_contract)
    capacity = budget.cartridge_retained_capacity_requirement_mL
    if capacity <= 0.0:
        raise ValueError("retained cartridge capacity must be positive")

    authority_floor_nominal_margin = capacity - nominal_at_authority_floor
    authority_floor_nominal_headroom = max(authority_floor_nominal_margin, 0.0)
    authority_floor_nominal_overflow = max(-authority_floor_nominal_margin, 0.0)
    authority_floor_nominal_capacity_exceeded = authority_floor_nominal_overflow > 0.0
    authority_floor_prime_allowance = authority_floor_nominal_headroom
    authority_floor_prime_allowance_margin = authority_floor_prime_allowance - prime_to_cartridge
    authority_floor_prime_incremental_overflow = max(-authority_floor_prime_allowance_margin, 0.0)
    authority_floor_capacity_exceeded_by_reprime = (
        not authority_floor_nominal_capacity_exceeded
        and authority_floor_prime_incremental_overflow > 0.0
    )

    authority_floor_demand = nominal_at_authority_floor + prime_to_cartridge
    authority_floor_margin = capacity - authority_floor_demand
    authority_floor_headroom = max(authority_floor_margin, 0.0)
    authority_floor_overflow = max(-authority_floor_margin, 0.0)
    authority_floor_partitioned_overflow = authority_floor_nominal_overflow + authority_floor_prime_incremental_overflow
    if abs(authority_floor_overflow - authority_floor_partitioned_overflow) > 1e-9:
        raise ValueError("authority-floor cartridge overflow partition is internally inconsistent")
    authority_floor_utilization = authority_floor_demand / capacity
    authority_floor_capacity_exceeded = authority_floor_overflow > 0.0
    if authority_floor_capacity_exceeded != (
        authority_floor_nominal_capacity_exceeded or authority_floor_capacity_exceeded_by_reprime
    ):
        raise ValueError("authority-floor cartridge failure-source classification is internally inconsistent")
    if authority_floor_headroom * authority_floor_overflow > 1e-12:
        raise ValueError("authority-floor cartridge headroom and overflow cannot coexist")

    nominal_recovery_uplift = nominal_at_maximum_recovery - nominal_at_authority_floor
    if nominal_recovery_uplift < -1e-12:
        raise ValueError("authority nominal recovery floor exceeds introduced nominal liquid")

    # Treat recovery uncertainty as a separate packaging load after the complete
    # authority-floor state, including reprime recovery. This identifies whether
    # a cartridge that satisfies the minimum recovery contract crosses capacity
    # solely because actual nominal recovery approaches 100%.
    recovery_uplift_allowance = authority_floor_headroom
    recovery_uplift_allowance_margin = recovery_uplift_allowance - nominal_recovery_uplift
    recovery_uplift_incremental_overflow = max(-recovery_uplift_allowance_margin, 0.0)
    capacity_exceeded_by_recovery_uplift = (
        not authority_floor_capacity_exceeded
        and recovery_uplift_incremental_overflow > 0.0
    )

    nominal_margin = capacity - nominal_at_maximum_recovery
    nominal_headroom = max(nominal_margin, 0.0)
    nominal_overflow = max(-nominal_margin, 0.0)
    nominal_capacity_exceeded = nominal_overflow > 0.0
    prime_allowance = nominal_headroom
    prime_allowance_margin = prime_allowance - prime_to_cartridge
    prime_incremental_overflow = max(-prime_allowance_margin, 0.0)
    capacity_exceeded_by_reprime = not nominal_capacity_exceeded and prime_incremental_overflow > 0.0

    demand = nominal_at_maximum_recovery + prime_to_cartridge
    margin = capacity - demand
    headroom = max(margin, 0.0)
    overflow = max(-margin, 0.0)
    partitioned_overflow = nominal_overflow + prime_incremental_overflow
    if abs(overflow - partitioned_overflow) > 1e-9:
        raise ValueError("cartridge overflow partition is internally inconsistent")
    capacity_exceeded = overflow > 0.0
    if capacity_exceeded != (nominal_capacity_exceeded or capacity_exceeded_by_reprime):
        raise ValueError("maximum-recovery cartridge failure-source classification is internally inconsistent")

    if abs((demand - authority_floor_demand) - nominal_recovery_uplift) > 1e-9:
        raise ValueError("authority-floor and maximum-recovery capacity states are inconsistent")
    if abs(overflow - (authority_floor_overflow + recovery_uplift_incremental_overflow)) > 1e-9:
        raise ValueError("nominal-recovery uplift overflow partition is internally inconsistent")
    if capacity_exceeded_by_recovery_uplift and authority_floor_capacity_exceeded:
        raise ValueError("nominal-recovery uplift cannot originate an existing authority-floor capacity failure")

    utilization = demand / capacity
    return LimitingEventCapacityScreen(
        service_envelope=envelope,
        limiting_prime_events=limiting_events,
        authority_floor_nominal_recovery_mL=nominal_at_authority_floor,
        authority_floor_nominal_only_headroom_mL=authority_floor_nominal_headroom,
        authority_floor_nominal_only_overflow_mL=authority_floor_nominal_overflow,
        authority_floor_nominal_capacity_exceeded=authority_floor_nominal_capacity_exceeded,
        authority_floor_prime_capacity_allowance_mL=authority_floor_prime_allowance,
        authority_floor_prime_allowance_margin_mL=authority_floor_prime_allowance_margin,
        authority_floor_prime_incremental_overflow_mL=authority_floor_prime_incremental_overflow,
        authority_floor_capacity_exceeded_by_reprime=authority_floor_capacity_exceeded_by_reprime,
        authority_floor_cartridge_demand_mL=authority_floor_demand,
        authority_floor_cartridge_margin_mL=authority_floor_margin,
        authority_floor_cartridge_headroom_mL=authority_floor_headroom,
        authority_floor_cartridge_overflow_mL=authority_floor_overflow,
        authority_floor_cartridge_utilization=authority_floor_utilization,
        authority_floor_cartridge_capacity_exceeded=authority_floor_capacity_exceeded,
        nominal_recovery_uplift_to_maximum_mL=nominal_recovery_uplift,
        nominal_recovery_uplift_capacity_allowance_mL=recovery_uplift_allowance,
        nominal_recovery_uplift_allowance_margin_mL=recovery_uplift_allowance_margin,
        nominal_recovery_uplift_incremental_overflow_mL=recovery_uplift_incremental_overflow,
        capacity_exceeded_by_nominal_recovery_uplift=capacity_exceeded_by_recovery_uplift,
        nominal_liquid_at_maximum_recovery_mL=nominal_at_maximum_recovery,
        nominal_only_cartridge_headroom_mL=nominal_headroom,
        nominal_only_cartridge_overflow_mL=nominal_overflow,
        nominal_capacity_exceeded_at_maximum_recovery=nominal_capacity_exceeded,
        prime_cartridge_capacity_allowance_mL=prime_allowance,
        prime_liquid_routed_to_cartridge_mL=prime_to_cartridge,
        prime_cartridge_allowance_margin_mL=prime_allowance_margin,
        prime_incremental_cartridge_overflow_mL=prime_incremental_overflow,
        capacity_exceeded_by_reprime_at_maximum_recovery=capacity_exceeded_by_reprime,
        cartridge_demand_at_maximum_nominal_recovery_mL=demand,
        retained_cartridge_capacity_mL=capacity,
        cartridge_margin_at_maximum_nominal_recovery_mL=margin,
        cartridge_headroom_at_maximum_nominal_recovery_mL=headroom,
        cartridge_overflow_at_maximum_nominal_recovery_mL=overflow,
        cartridge_utilization_at_maximum_nominal_recovery=utilization,
        cartridge_capacity_exceeded_at_maximum_nominal_recovery=capacity_exceeded,
    )
