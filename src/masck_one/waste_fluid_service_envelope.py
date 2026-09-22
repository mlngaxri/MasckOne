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
    minimum_nominal_recovery_ratio_for_sink_closure: float
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
    maximum_prime_events_before_residual_ceiling: int | None
    maximum_prime_events_before_external_leakage_ceiling: int | None
    residual_event_headroom_at_capacity_boundary: int | None
    external_leakage_event_headroom_at_capacity_boundary: int | None
    controlling_constraint: str
    maximum_feasible: ServiceEnvelopePoint
    first_infeasible: ServiceEnvelopePoint


def _maximum_events_within_sink_ceiling(*, ceiling_mL: float, per_event_mL: float) -> int | None:
    """Return the exact integer event count that still fits one shared sink.

    ``None`` means this routing contract sends no prime liquid to that sink, so
    the sink itself does not impose a finite reprime-event boundary.
    """
    if per_event_mL <= _TOL:
        return None
    return math.floor((ceiling_mL + _TOL) / per_event_mL)


def _point(budget: WasteFluidBudget, *, cycles: int, prime_events: int, recovery: float, residual: float, leakage: float) -> ServiceEnvelopePoint:
    closure = screen_service_routing_closure(
        budget, cycles=cycles, prime_events=prime_events,
        prime_recovery_ratio_contract=recovery,
        prime_residual_ratio_contract=residual,
        prime_external_leakage_ratio_contract=leakage,
    )
    if closure.prime_liquid_without_routing_contract_mL > _TOL:
        raise WasteFluidAccountingError("service envelope requires a complete prime destination contract")
    nominal_threshold = closure.minimum_nominal_liquid_routed_to_cartridge_mL + closure.shared_sink_unclassified_nonrecovery_mL
    nominal_introduced = cycles * budget.nominal_introduced_mL_per_cycle
    if nominal_threshold > nominal_introduced + _TOL:
        raise WasteFluidAccountingError("shared-sink closure would require recovering more nominal liquid than introduced")
    nominal_recovery_ratio = nominal_threshold / nominal_introduced
    total = nominal_threshold + closure.minimum_prime_liquid_routed_to_cartridge_mL
    margin = budget.cartridge_retained_capacity_requirement_mL - total
    return ServiceEnvelopePoint(
        prime_events, nominal_threshold, nominal_recovery_ratio,
        closure.minimum_prime_liquid_routed_to_cartridge_mL,
        total, budget.cartridge_retained_capacity_requirement_mL, margin, margin >= -_TOL, closure,
    )


def _headroom(limit: int | None, *, used: int) -> int | None:
    return None if limit is None else limit - used


def _controlling_constraint(*, capacity_next: int, residual_limit: int | None, leakage_limit: int | None) -> str:
    """Identify the first independently computable service-envelope constraint."""
    candidates = [(capacity_next, "CARTRIDGE_CAPACITY")]
    if residual_limit is not None:
        candidates.append((residual_limit + 1, "RESIDUAL_CEILING"))
    if leakage_limit is not None:
        candidates.append((leakage_limit + 1, "EXTERNAL_LEAKAGE_CEILING"))
    first_event = min(event for event, _ in candidates)
    names = sorted(name for event, name in candidates if event == first_event)
    return "+".join(names)


def evaluate_reprime_service_envelope(
    budget: WasteFluidBudget, *, cycles: int,
    prime_recovery_ratio_contract: float,
    prime_residual_ratio_contract: float,
    prime_external_leakage_ratio_contract: float,
) -> ReprimeServiceEnvelope:
    """Find the exact integer reprime boundary under the supplied routing contract."""
    budget.validate()
    # ``cycles`` is both a service-life count and the denominator of the
    # derived nominal-recovery ratio. Reject bools, fractions and zero here so
    # invalid service intervals cannot leak into downstream closure arithmetic.
    if type(cycles) is not int or cycles <= 0:
        raise WasteFluidAccountingError("service envelope cycles must be a positive integer")
    ratios = (prime_recovery_ratio_contract, prime_residual_ratio_contract, prime_external_leakage_ratio_contract)
    if any(type(value) not in (int, float) or not math.isfinite(value) for value in ratios):
        raise WasteFluidAccountingError("service envelope routing ratios must be finite numbers")
    if any(value < 0.0 or value > 1.0 for value in ratios):
        raise WasteFluidAccountingError("service envelope routing ratios must each lie in [0, 1]")
    if abs(sum(ratios) - 1.0) > _TOL:
        raise WasteFluidAccountingError("service envelope requires prime destination ratios to sum to exactly one")

    recovery, residual, leakage = (float(value) for value in ratios)
    previous = _point(budget, cycles=cycles, prime_events=0, recovery=recovery, residual=residual, leakage=leakage)
    if not previous.feasible:
        raise WasteFluidAccountingError("zero-prime service cannot close shared sinks within retained cartridge capacity")

    prime_volume = budget.maximum_initial_prime_mL_per_cycle
    residual_event_limit = _maximum_events_within_sink_ceiling(
        ceiling_mL=budget.residual_free_liquid_max_mL * cycles, per_event_mL=prime_volume * residual,
    )
    leakage_event_limit = _maximum_events_within_sink_ceiling(
        ceiling_mL=budget.external_leakage_max_mL_per_cycle * cycles, per_event_mL=prime_volume * leakage,
    )
    if prime_volume <= _TOL:
        raise WasteFluidAccountingError("zero-volume prime has no finite reprime-event capacity boundary")
    conservative_bound = budget.maximum_prime_events_that_fit(cycles=cycles)
    search_limit = max(1, (conservative_bound or 0) + math.ceil(budget.cartridge_retained_capacity_requirement_mL / prime_volume) + 2)

    for events in range(1, search_limit + 1):
        try:
            current = _point(budget, cycles=cycles, prime_events=events, recovery=recovery, residual=residual, leakage=leakage)
        except WasteFluidAccountingError:
            raise WasteFluidAccountingError(f"prime routing contract becomes invalid before a capacity boundary at {events} events")
        if not current.feasible:
            return ReprimeServiceEnvelope(
                cycles=cycles,
                maximum_feasible_prime_events=previous.prime_events,
                limiting_next_prime_events=current.prime_events,
                maximum_prime_events_before_residual_ceiling=residual_event_limit,
                maximum_prime_events_before_external_leakage_ceiling=leakage_event_limit,
                residual_event_headroom_at_capacity_boundary=_headroom(residual_event_limit, used=previous.prime_events),
                external_leakage_event_headroom_at_capacity_boundary=_headroom(leakage_event_limit, used=previous.prime_events),
                controlling_constraint=_controlling_constraint(
                    capacity_next=current.prime_events,
                    residual_limit=residual_event_limit,
                    leakage_limit=leakage_event_limit,
                ),
                maximum_feasible=previous,
                first_infeasible=current,
            )
        previous = current
    raise WasteFluidAccountingError("failed to locate finite reprime service-envelope boundary")
