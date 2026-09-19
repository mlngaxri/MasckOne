"""Cross-requirement closure checks for CLEAN-cycle liquid.

This module reconciles the recovery floor with the residual-fluid and external-
leakage ceilings without treating those ceilings as measured sinks. The result is
a synthetic requirement-consistency bound, not a physical fluid-loss model.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

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
    """Service-level liquid whose destination is not closed by current requirements."""

    cycles: int
    prime_events: int
    nominal_unclassified_nonrecovery_mL: float
    total_prime_liquid_mL: float
    prime_recovery_ratio_contract: float | None
    minimum_prime_liquid_routed_to_cartridge_mL: float
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
    prime_recovery_ratio_contract: float | None = None,
) -> ServiceRoutingClosure:
    """Expose service liquid that lacks a requirement-level destination contract.

    Capacity accounting reserves all prime liquid, but reservation does not prove
    routing. ``prime_recovery_ratio_contract`` is therefore optional and explicit:
    when absent, all prime liquid remains unresolved; when present, only the
    contracted recovered fraction is credited as routed to the cartridge. The
    remainder stays unresolved until another sink contract exists. This is a digital
    interface check and does not claim measured recovery performance.
    """
    budget.validate()
    if type(cycles) is not int or cycles <= 0:
        raise WasteFluidAccountingError("cycles must be a positive integer")
    if type(prime_events) is not int or prime_events < 0:
        raise WasteFluidAccountingError("prime_events must be a nonnegative integer")
    if prime_recovery_ratio_contract is not None:
        if (
            type(prime_recovery_ratio_contract) not in (int, float)
            or not math.isfinite(prime_recovery_ratio_contract)
            or not 0.0 <= prime_recovery_ratio_contract <= 1.0
        ):
            raise WasteFluidAccountingError("prime_recovery_ratio_contract must be finite and between zero and one")
        prime_recovery_ratio_contract = float(prime_recovery_ratio_contract)

    nominal = screen_nonrecovery_closure(budget).unclassified_nonrecovery_allowance_mL * cycles
    total_prime = budget.maximum_initial_prime_mL_per_cycle * prime_events
    routed_prime = 0.0 if prime_recovery_ratio_contract is None else total_prime * prime_recovery_ratio_contract
    unresolved_prime = total_prime - routed_prime
    total_unresolved = nominal + unresolved_prime
    return ServiceRoutingClosure(
        cycles=cycles,
        prime_events=prime_events,
        nominal_unclassified_nonrecovery_mL=nominal,
        total_prime_liquid_mL=total_prime,
        prime_recovery_ratio_contract=prime_recovery_ratio_contract,
        minimum_prime_liquid_routed_to_cartridge_mL=routed_prime,
        prime_liquid_without_routing_contract_mL=unresolved_prime,
        total_liquid_without_routing_contract_mL=total_unresolved,
        routing_contract_complete=total_unresolved <= 1e-12,
    )
