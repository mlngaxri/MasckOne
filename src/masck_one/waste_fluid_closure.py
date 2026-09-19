"""Cross-requirement closure checks for CLEAN-cycle liquid.

This module reconciles the recovery floor with the residual-fluid and external-
leakage ceilings without treating those ceilings as measured sinks. The result is
a synthetic requirement-consistency bound, not a physical fluid-loss model.
"""
from __future__ import annotations

from dataclasses import dataclass

from .waste_fluid_accounting import WasteFluidAccountingError, WasteFluidBudget


@dataclass(frozen=True)
class NonrecoveryClosure:
    """Requirement-space accounting for nominal liquid not recovered as waste."""

    maximum_unrecovered_nominal_mL: float
    residual_ceiling_mL: float
    external_leakage_ceiling_mL: float
    classified_nonrecovery_ceiling_mL: float
    unclassified_nonrecovery_allowance_mL: float
    classified_sink_headroom_mL: float
    closes_using_only_classified_sinks: bool


@dataclass(frozen=True)
class ServiceRoutingClosure:
    """Service-level liquid whose destination is not closed by current requirements.

    Prime liquid is intentionally treated separately from nominal CLEAN liquid.
    The authority specifies its maximum introduced volume but no prime-specific
    recovery fraction or disposal sink, so none of it is silently credited to the
    nominal recovery requirement.
    """

    cycles: int
    prime_events: int
    nominal_unclassified_nonrecovery_mL: float
    prime_liquid_without_routing_contract_mL: float
    total_liquid_without_routing_contract_mL: float
    routing_contract_complete: bool


def screen_nonrecovery_closure(budget: WasteFluidBudget) -> NonrecoveryClosure:
    """Reconcile recovery, residual and leakage requirements for one nominal cycle."""
    budget.validate()
    unrecovered = budget.maximum_unrecovered_nominal_mL_per_cycle
    classified = budget.maximum_classified_nonrecovery_mL_per_cycle
    gap = unrecovered - classified
    tolerance = 1e-12
    return NonrecoveryClosure(
        maximum_unrecovered_nominal_mL=unrecovered,
        residual_ceiling_mL=budget.residual_free_liquid_max_mL,
        external_leakage_ceiling_mL=budget.external_leakage_max_mL_per_cycle,
        classified_nonrecovery_ceiling_mL=classified,
        unclassified_nonrecovery_allowance_mL=max(0.0, gap),
        classified_sink_headroom_mL=max(0.0, -gap),
        closes_using_only_classified_sinks=gap <= tolerance,
    )


def screen_service_routing_closure(
    budget: WasteFluidBudget,
    *,
    cycles: int,
    prime_events: int,
) -> ServiceRoutingClosure:
    """Expose service liquid that lacks a requirement-level destination contract.

    This is deliberately stricter than cartridge capacity accounting. Capacity may
    conservatively reserve all prime liquid, but that does not prove prime liquid is
    recovered to the cartridge. Until a prime recovery/disposal contract exists,
    every allowed prime event remains an explicit routing obligation.
    """
    budget.validate()
    if type(cycles) is not int or cycles <= 0:
        raise WasteFluidAccountingError("cycles must be a positive integer")
    if type(prime_events) is not int or prime_events < 0:
        raise WasteFluidAccountingError("prime_events must be a nonnegative integer")

    nominal = screen_nonrecovery_closure(budget).unclassified_nonrecovery_allowance_mL * cycles
    prime = budget.maximum_initial_prime_mL_per_cycle * prime_events
    total = nominal + prime
    return ServiceRoutingClosure(
        cycles=cycles,
        prime_events=prime_events,
        nominal_unclassified_nonrecovery_mL=nominal,
        prime_liquid_without_routing_contract_mL=prime,
        total_liquid_without_routing_contract_mL=total,
        routing_contract_complete=total <= 1e-12,
    )
