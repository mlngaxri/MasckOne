"""Authority binding for cartridge overflow-guard evidence."""
from __future__ import annotations

import math

from .waste_fluid_accounting import WasteFluidAccountingError, WasteFluidBudget
from .waste_fluid_cycle_evidence import validate_cycle_routing_evidence
from .waste_fluid_overflow_guard import CartridgeOverflowGuard

_TOL = 1e-12


def validate_overflow_guard_authority(
    budget: WasteFluidBudget,
    guard: CartridgeOverflowGuard,
) -> None:
    """Reject internally valid overflow evidence that drifts from its fluid authority.

    The overflow guard already checks its own derived capacity fields. This boundary
    independently binds its retained capacity and cycle-resolved conservative inflow
    trajectory to the supplied ``WasteFluidBudget``. Authority-qualified overflow
    evidence must cover the complete service life so a partial trajectory cannot be
    mistaken for an end-of-service cartridge-capacity proof. It is a digital
    conservation check only and does not claim physical recovery, leakage, foam,
    pressure/flow, retained capacity, or sealing performance.
    """
    if type(budget) is not WasteFluidBudget:
        raise WasteFluidAccountingError("overflow authority validator requires exact WasteFluidBudget")
    if type(guard) is not CartridgeOverflowGuard:
        raise WasteFluidAccountingError("overflow authority validator requires exact CartridgeOverflowGuard")
    budget.validate()
    guard.__post_init__()
    validate_cycle_routing_evidence(guard.routing)

    if not math.isclose(
        guard.retained_capacity_mL,
        budget.cartridge_retained_capacity_requirement_mL,
        rel_tol=0.0,
        abs_tol=_TOL,
    ):
        raise WasteFluidAccountingError("overflow guard retained capacity does not match fluid authority")
    if len(guard.routing.cycles) != budget.service_cycles:
        raise WasteFluidAccountingError(
            "overflow guard cycle evidence must cover the complete authority service life"
        )

    cumulative_prime_events = 0
    for state in guard.routing.cycles:
        cumulative_prime_events += state.prime_events
        authority_screen = budget.service_capacity_screen(
            cycles=state.cycle,
            prime_events=cumulative_prime_events,
        )
        expected_maximum = authority_screen.maximum_cartridge_inflow_mL
        if not math.isclose(
            state.cumulative_maximum_cartridge_inflow_mL,
            expected_maximum,
            rel_tol=0.0,
            abs_tol=_TOL,
        ):
            raise WasteFluidAccountingError(
                "overflow guard conservative inflow trajectory does not match fluid authority"
            )

        authority_minimum_nominal = authority_screen.minimum_recovered_nominal_mL
        if state.cumulative_minimum_cartridge_routing_mL + _TOL < authority_minimum_nominal:
            raise WasteFluidAccountingError(
                "overflow guard minimum routing falls below authority nominal recovery floor"
            )
        if state.cumulative_minimum_cartridge_routing_mL > expected_maximum + _TOL:
            raise WasteFluidAccountingError(
                "overflow guard minimum routing exceeds authority maximum available inflow"
            )
