"""Independent integrity validation for service-level waste/fluid routing evidence.

This module reconstructs a ``ServiceRoutingClosure`` from its authoritative budget
and source contracts, then compares every derived field. It is requirement-space
verification only and does not claim measured recovery, leakage, residual, or
retained-volume performance.
"""
from __future__ import annotations

from dataclasses import fields
import math

from .waste_fluid_accounting import WasteFluidAccountingError, WasteFluidBudget
from .waste_fluid_closure import ServiceRoutingClosure, screen_service_routing_closure

_TOL = 1e-9


def validate_service_routing_closure_evidence(
    budget: WasteFluidBudget,
    closure: ServiceRoutingClosure,
) -> None:
    """Fail closed when service-routing evidence is stale, partial, or nonfinite.

    The validator intentionally rebuilds the closure instead of trusting stored
    derived quantities. This catches mutations to nominal recovery, nominal
    unclassified nonrecovery, prime sink volumes, shared sink margins, unresolved
    liquid, and routing-completeness state.
    """
    budget.validate()
    if type(closure) is not ServiceRoutingClosure:
        raise WasteFluidAccountingError("service routing integrity requires exact ServiceRoutingClosure evidence")
    if type(closure.cycles) is not int or closure.cycles <= 0 or closure.cycles > budget.service_cycles:
        raise WasteFluidAccountingError("service routing evidence has an invalid cycle window")
    if type(closure.prime_events) is not int or closure.prime_events < 0:
        raise WasteFluidAccountingError("service routing evidence has an invalid prime-event count")

    expected = screen_service_routing_closure(
        budget,
        cycles=closure.cycles,
        prime_events=closure.prime_events,
        prime_recovery_ratio_contract=closure.prime_recovery_ratio_contract,
        prime_residual_ratio_contract=closure.prime_residual_ratio_contract,
        prime_external_leakage_ratio_contract=closure.prime_external_leakage_ratio_contract,
    )

    for field in fields(ServiceRoutingClosure):
        name = field.name
        actual = getattr(closure, name)
        wanted = getattr(expected, name)
        if name in {"cycles", "prime_events"}:
            if actual != wanted:
                raise WasteFluidAccountingError(f"service routing {name} is stale")
            continue
        if name == "routing_contract_complete":
            if type(actual) is not bool or actual != wanted:
                raise WasteFluidAccountingError("service routing completeness state is stale")
            continue
        if name.endswith("_contract"):
            if actual != wanted:
                raise WasteFluidAccountingError(f"service routing {name} is stale")
            continue
        if type(actual) not in (int, float) or not math.isfinite(float(actual)):
            raise WasteFluidAccountingError(f"service routing {name} must be finite numeric evidence")
        if not math.isclose(float(actual), float(wanted), rel_tol=0.0, abs_tol=_TOL):
            raise WasteFluidAccountingError(f"service routing {name} is stale")
