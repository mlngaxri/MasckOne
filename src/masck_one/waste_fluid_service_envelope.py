"""Joint service envelope for reprime routing, sink closure and cartridge capacity.

This is requirement arithmetic only. It determines how many prime events can be
accommodated by the supplied digital routing contract when nominal recovery is
raised only as far as necessary to close the shared residual/leakage sinks.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

from .waste_fluid_accounting import WasteFluidAccountingError, WasteFluidBudget
from .waste_fluid_closure import ServiceRoutingClosure, screen_service_routing_closure

_TOL = 1e-12


@dataclass(frozen=True, slots=True)
class ServiceEnvelopePoint:
    prime_events: int
    minimum_nominal_recovery_for_sink_closure_mL: float
    minimum_prime_routed_to_cartridge_mL: float
    minimum_total_cartridge_routing_for_sink_closure_mL: float
    retained_cartridge_capacity_mL: float
    cartridge_margin_mL: float
    feasible: bool
    source_closure: ServiceRoutingClosure


@dataclass(frozen=True, slots=True)
class ReprimeServiceEnvelope:
    cycles: int
    maximum_feasible_prime_events: int
    limiting_next_prime_events: int
    maximum_feasible: ServiceEnvelopePoint
    first_infeasible: ServiceEnvelopePoint


def _point(
    budget: WasteFluidBudget,
    *,
    cycles: int,
    prime_events: int,
    recovery: float,
    residual: float,
    leakage: float,
) -> ServiceEnvelopePoint:
    closure = screen_service_routing_closure(
        budget,
        cycles=cycles,
        prime_events=prime_events,
        prime_recovery_ratio_contract=recovery,
        prime_residual_ratio_contract=residual,
        prime_external_leakage_ratio_contract=leakage,
    )
    if closure.prime_liquid_without_routing_contract_mL > _TOL:
        raise WasteFluidAccountingError("service envelope requires a complete prime destination contract")
    nominal_threshold = (
        closure.minimum_nominal_liquid_routed_to_cartridge_mL
        + closure.shared_sink_unclassified_nonrecovery_mL
    )
    if nominal_threshold > cycles * budget.nominal_introduced_mL_per_cycle + _TOL:
        raise WasteFluidAccountingError("shared-sink closure would require recovering more nominal liquid than introduced")
    total = nominal_threshold + closure.minimum_prime_liquid_routed_to_cartridge_mL
    margin = budget.cartridge_retained_capacity_requirement_mL - total
    return ServiceEnvelopePoint(
        prime_events=prime_events,
        minimum_nominal_recovery_for_sink_closure_mL=nominal_threshold,
        minimum_prime_routed_to_cartridge_mL=closure.minimum_prime_liquid_routed_to_cartridge_mL,
        minimum_total_cartridge_routing_for_sink_closure_mL=total,
        retained_cartridge_capacity_mL=budget.cartridge_retained_capacity_requirement_mL,
        cartridge_margin_mL=margin,
        feasible=margin >= -_TOL,
        source_closure=closure,
    )


def evaluate_reprime_service_envelope(
    budget: WasteFluidBudget,
    *,
    cycles: int,
    prime_recovery_ratio_contract: float,
    prime_residual_ratio_contract: float,
    prime_external_leakage_ratio_contract: float,
) -> ReprimeServiceEnvelope:
    """Find the exact integer reprime boundary under the supplied routing contract."""
    budget.validate()
    ratios = (
        prime_recovery_ratio_contract,
        prime_residual_ratio_contract,
        prime_external_leakage_ratio_contract,
    )
    if any(type(value) not in (int, float) or not math.isfinite(value) for value in ratios):
        raise WasteFluidAccountingError("service envelope routing ratios must be finite numbers")
    if sum(ratios) < 1.0 - _TOL:
        raise WasteFluidAccountingError("service envelope requires all prime liquid to have a destination contract")

    previous = _point(
        budget, cycles=cycles, prime_events=0,
        recovery=float(ratios[0]), residual=float(ratios[1]), leakage=float(ratios[2]),
    )
    if not previous.feasible:
        raise WasteFluidAccountingError("zero-prime service cannot close shared sinks within retained cartridge capacity")

    # Capacity provides a finite search bound whenever prime volume is nonzero.
    if budget.maximum_initial_prime_mL_per_cycle <= _TOL:
        raise WasteFluidAccountingError("zero-volume prime has no finite reprime-event capacity boundary")
    conservative_bound = budget.maximum_prime_events_that_fit(cycles=cycles)
    search_limit = max(1, (conservative_bound or 0) + math.ceil(
        budget.cartridge_retained_capacity_requirement_mL / budget.maximum_initial_prime_mL_per_cycle
    ) + 2)

    for events in range(1, search_limit + 1):
        try:
            current = _point(
                budget, cycles=cycles, prime_events=events,
                recovery=float(ratios[0]), residual=float(ratios[1]), leakage=float(ratios[2]),
            )
        except WasteFluidAccountingError:
            # A sink ceiling exceeded before capacity is itself an infeasible next event.
            closure = previous.source_closure
            raise WasteFluidAccountingError(
                f"prime routing contract becomes invalid before a capacity boundary at {events} events"
            )
        if not current.feasible:
            return ReprimeServiceEnvelope(
                cycles=cycles,
                maximum_feasible_prime_events=previous.prime_events,
                limiting_next_prime_events=current.prime_events,
                maximum_feasible=previous,
                first_infeasible=current,
            )
        previous = current
    raise WasteFluidAccountingError("failed to locate finite reprime service-envelope boundary")
