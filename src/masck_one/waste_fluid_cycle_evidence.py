"""Independent structural validation for cycle-resolved recovery evidence."""
from __future__ import annotations

import math

from .waste_fluid_accounting import WasteFluidAccountingError
from .waste_fluid_cycle_routing import CycleResolvedRoutingClosure, CycleRoutingScreen

_TOL = 1e-12
_NONNEGATIVE_VOLUME_FIELDS = (
    "prime_residual_mL",
    "prime_external_leakage_mL",
    "minimum_nominal_routed_to_cartridge_mL",
    "minimum_prime_routed_to_cartridge_mL",
    "minimum_total_routed_to_cartridge_mL",
    "cumulative_minimum_cartridge_routing_mL",
    "cumulative_maximum_cartridge_inflow_mL",
    "cartridge_occupancy_uncertainty_mL",
    "residual_ceiling_margin_mL",
    "external_leakage_ceiling_margin_mL",
    "classified_sink_capacity_after_prime_mL",
    "nominal_unclassified_nonrecovery_after_prime_mL",
    "classified_sink_headroom_after_nominal_mL",
)


def validate_cycle_routing_evidence(closure: CycleResolvedRoutingClosure) -> None:
    """Reject internally inconsistent cycle evidence before treatment handoff.

    This validates arithmetic and state relationships only. It does not replace
    physical recovery, leakage, retained-capacity, pressure/flow, or hygiene tests.
    """
    if type(closure) is not CycleResolvedRoutingClosure:
        raise WasteFluidAccountingError("cycle evidence validator requires exact CycleResolvedRoutingClosure")
    if not closure.cycles:
        raise WasteFluidAccountingError("cycle evidence validator requires cycle evidence")

    cumulative_minimum = 0.0
    previous_maximum = 0.0
    inferred_capacity = None
    for expected_cycle, state in enumerate(closure.cycles, start=1):
        if type(state) is not CycleRoutingScreen or state.cycle != expected_cycle:
            raise WasteFluidAccountingError("cycle evidence must contain contiguous exact CycleRoutingScreen states")
        if type(state.prime_events) is not int or state.prime_events < 0:
            raise WasteFluidAccountingError("cycle prime_events must be a nonnegative exact integer")
        for name, value in vars(state).items():
            if name in {"cycle", "prime_events", "minimum_routing_capacity_satisfied", "cartridge_capacity_satisfied", "local_routing_contract_complete"}:
                continue
            if type(value) not in (int, float) or not math.isfinite(value):
                raise WasteFluidAccountingError(f"cycle {state.cycle} {name} must be finite numeric evidence")
        for name in _NONNEGATIVE_VOLUME_FIELDS:
            if getattr(state, name) < -_TOL:
                raise WasteFluidAccountingError(f"cycle {state.cycle} {name} must be nonnegative volume evidence")
        for name in ("minimum_routing_capacity_satisfied", "cartridge_capacity_satisfied", "local_routing_contract_complete"):
            if type(getattr(state, name)) is not bool:
                raise WasteFluidAccountingError(f"cycle {state.cycle} {name} must be an exact bool")

        local_total = state.minimum_nominal_routed_to_cartridge_mL + state.minimum_prime_routed_to_cartridge_mL
        if not math.isclose(state.minimum_total_routed_to_cartridge_mL, local_total, rel_tol=0.0, abs_tol=_TOL):
            raise WasteFluidAccountingError("cycle minimum routing components do not reconcile")
        cumulative_minimum += local_total
        if not math.isclose(state.cumulative_minimum_cartridge_routing_mL, cumulative_minimum, rel_tol=0.0, abs_tol=_TOL):
            raise WasteFluidAccountingError("cycle cumulative minimum routing does not reconcile")
        if state.cumulative_maximum_cartridge_inflow_mL + _TOL < previous_maximum:
            raise WasteFluidAccountingError("cycle conservative cartridge inflow must be monotonic")
        local_maximum_inflow = state.cumulative_maximum_cartridge_inflow_mL - previous_maximum
        if local_maximum_inflow + _TOL < local_total:
            raise WasteFluidAccountingError("cycle minimum cartridge routing exceeds local conservative inflow bound")
        expected_uncertainty = max(0.0, state.cumulative_maximum_cartridge_inflow_mL - cumulative_minimum)
        if not math.isclose(state.cartridge_occupancy_uncertainty_mL, expected_uncertainty, rel_tol=0.0, abs_tol=_TOL):
            raise WasteFluidAccountingError("cycle cartridge occupancy uncertainty does not reconcile")

        expected_classified_capacity = state.residual_ceiling_margin_mL + state.external_leakage_ceiling_margin_mL
        if not math.isclose(state.classified_sink_capacity_after_prime_mL, expected_classified_capacity, rel_tol=0.0, abs_tol=_TOL):
            raise WasteFluidAccountingError("cycle classified sink capacity does not reconcile to residual and leakage margins")
        if state.nominal_unclassified_nonrecovery_after_prime_mL > _TOL and state.classified_sink_headroom_after_nominal_mL > _TOL:
            raise WasteFluidAccountingError("cycle cannot simultaneously have nominal sink deficit and classified sink headroom")
        if state.local_routing_contract_complete and state.nominal_unclassified_nonrecovery_after_prime_mL > _TOL:
            raise WasteFluidAccountingError("cycle routing cannot be complete while nominal nonrecovery remains unclassified")

        capacity_from_minimum = state.minimum_routing_capacity_margin_mL + cumulative_minimum
        capacity_from_maximum = state.cartridge_capacity_margin_mL + state.cumulative_maximum_cartridge_inflow_mL
        if not math.isclose(capacity_from_minimum, capacity_from_maximum, rel_tol=0.0, abs_tol=_TOL):
            raise WasteFluidAccountingError("cycle capacity margins imply different retained capacities")
        if inferred_capacity is None:
            inferred_capacity = capacity_from_minimum
        elif not math.isclose(capacity_from_minimum, inferred_capacity, rel_tol=0.0, abs_tol=_TOL):
            raise WasteFluidAccountingError("cycle retained-capacity evidence drifts across profile")

        if state.minimum_routing_capacity_satisfied != (state.minimum_routing_capacity_margin_mL >= -_TOL):
            raise WasteFluidAccountingError("cycle minimum-routing capacity boolean contradicts margin")
        if state.cartridge_capacity_satisfied != (state.cartridge_capacity_margin_mL >= -_TOL):
            raise WasteFluidAccountingError("cycle conservative capacity boolean contradicts margin")
        previous_maximum = state.cumulative_maximum_cartridge_inflow_mL