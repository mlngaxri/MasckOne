"""Cycle-resolved routing checks for prime liquid.

Aggregate service accounting can hide a one-cycle sink overrun when reprimes are
clustered. This module preserves cycle locality for residual and external-leakage
ceilings while retaining the aggregate service closure calculation.
"""
from __future__ import annotations

from dataclasses import dataclass

from .waste_fluid_accounting import WasteFluidAccountingError, WasteFluidBudget
from .waste_fluid_closure import ServiceRoutingClosure, screen_service_routing_closure


@dataclass(frozen=True)
class CycleRoutingScreen:
    cycle: int
    prime_events: int
    prime_residual_mL: float
    prime_external_leakage_mL: float
    residual_ceiling_margin_mL: float
    external_leakage_ceiling_margin_mL: float


@dataclass(frozen=True)
class CycleResolvedRoutingClosure:
    cycles: tuple[CycleRoutingScreen, ...]
    service: ServiceRoutingClosure


def screen_cycle_resolved_routing_closure(
    budget: WasteFluidBudget,
    *,
    prime_events_by_cycle: tuple[int, ...] | list[int],
    prime_recovery_ratio_contract: float | None = None,
    prime_residual_ratio_contract: float | None = None,
    prime_external_leakage_ratio_contract: float | None = None,
) -> CycleResolvedRoutingClosure:
    """Check routing contracts without averaging sink use across service cycles.

    The external-leakage requirement is cycle-scoped, so reprime leakage cannot be
    borrowed from another cycle's unused allowance. Residual is screened with the
    same cycle locality here as a conservative integration guard. The aggregate
    service closure is still returned for whole-service mass accounting.
    """
    budget.validate()
    if not isinstance(prime_events_by_cycle, (tuple, list)) or not prime_events_by_cycle:
        raise WasteFluidAccountingError("prime_events_by_cycle must be a nonempty tuple or list")
    if any(type(count) is not int or count < 0 for count in prime_events_by_cycle):
        raise WasteFluidAccountingError("prime event counts must be nonnegative integers")

    screens: list[CycleRoutingScreen] = []
    for index, prime_events in enumerate(prime_events_by_cycle, start=1):
        # A one-cycle closure validates contract ratios, mass conservation and the
        # local sink ceilings. This deliberately fails before aggregate averaging.
        local = screen_service_routing_closure(
            budget,
            cycles=1,
            prime_events=prime_events,
            prime_recovery_ratio_contract=prime_recovery_ratio_contract,
            prime_residual_ratio_contract=prime_residual_ratio_contract,
            prime_external_leakage_ratio_contract=prime_external_leakage_ratio_contract,
        )
        screens.append(
            CycleRoutingScreen(
                cycle=index,
                prime_events=prime_events,
                prime_residual_mL=local.maximum_prime_residual_mL,
                prime_external_leakage_mL=local.maximum_prime_external_leakage_mL,
                residual_ceiling_margin_mL=local.prime_residual_ceiling_margin_mL,
                external_leakage_ceiling_margin_mL=local.prime_external_leakage_ceiling_margin_mL,
            )
        )

    service = screen_service_routing_closure(
        budget,
        cycles=len(prime_events_by_cycle),
        prime_events=sum(prime_events_by_cycle),
        prime_recovery_ratio_contract=prime_recovery_ratio_contract,
        prime_residual_ratio_contract=prime_residual_ratio_contract,
        prime_external_leakage_ratio_contract=prime_external_leakage_ratio_contract,
    )
    return CycleResolvedRoutingClosure(cycles=tuple(screens), service=service)
