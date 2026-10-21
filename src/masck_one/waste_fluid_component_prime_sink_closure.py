"""Prime-adjusted sink closure for a concrete nominal recovery allocation.

This binds component-level nominal recovery to cycle-resolved prime routing so prime
residual and leakage consume the same finite sink ceilings as nominal nonrecovery.
It is requirement arithmetic, not physical recovery or leakage evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

from .waste_fluid_accounting import WasteFluidAccountingError
from .waste_fluid_component_recovery_allocation import ComponentRecoveryAllocation
from .waste_fluid_cycle_routing import CycleResolvedRoutingClosure

_TOL = 1e-12


@dataclass(frozen=True, slots=True)
class PrimeAdjustedComponentSinkClosure:
    source_allocation: ComponentRecoveryAllocation
    source_routing: CycleResolvedRoutingClosure
    nominal_nonrecovered_mL: float
    prime_residual_mL: float
    prime_external_leakage_mL: float
    residual_capacity_after_prime_mL: float
    leakage_capacity_after_prime_mL: float
    classified_capacity_after_prime_mL: float
    minimum_nominal_recovery_for_sink_closure_mL: float
    minimum_nominal_recovery_ratio_for_sink_closure: float
    additional_recovery_above_requirement_floor_mL: float
    residual_allocation_min_mL: float
    residual_allocation_max_mL: float
    leakage_allocation_min_mL: float
    leakage_allocation_max_mL: float
    unclassified_nominal_liquid_mL: float
    feasible: bool

    def __post_init__(self) -> None:
        if type(self.source_allocation) is not ComponentRecoveryAllocation:
            raise WasteFluidAccountingError("prime-adjusted sink closure requires exact component allocation evidence")
        if type(self.source_routing) is not CycleResolvedRoutingClosure:
            raise WasteFluidAccountingError("prime-adjusted sink closure requires exact cycle routing evidence")
        self.source_allocation.__post_init__()
        self.source_routing.__post_init__()
        expected = _derive(self.source_allocation, self.source_routing)
        numeric_names = (
            "nominal_nonrecovered_mL", "prime_residual_mL", "prime_external_leakage_mL",
            "residual_capacity_after_prime_mL", "leakage_capacity_after_prime_mL",
            "classified_capacity_after_prime_mL", "minimum_nominal_recovery_for_sink_closure_mL",
            "minimum_nominal_recovery_ratio_for_sink_closure", "additional_recovery_above_requirement_floor_mL",
            "residual_allocation_min_mL", "residual_allocation_max_mL", "leakage_allocation_min_mL",
            "leakage_allocation_max_mL", "unclassified_nominal_liquid_mL",
        )
        for name in numeric_names:
            value = getattr(self, name)
            if type(value) not in (int, float) or not math.isfinite(float(value)) or value < -_TOL:
                raise WasteFluidAccountingError(f"prime-adjusted sink closure {name} must be finite and nonnegative")
            if not math.isclose(value, expected[name], rel_tol=0.0, abs_tol=_TOL):
                raise WasteFluidAccountingError(f"prime-adjusted sink closure {name} does not reconcile")
        if self.minimum_nominal_recovery_ratio_for_sink_closure > 1.0 + _TOL:
            raise WasteFluidAccountingError("prime-adjusted sink closure recovery ratio cannot exceed one")
        if type(self.feasible) is not bool or self.feasible is not expected["feasible"]:
            raise WasteFluidAccountingError("prime-adjusted sink closure decision does not reconcile")
        if self.feasible:
            if not math.isclose(self.residual_allocation_min_mL + self.leakage_allocation_max_mL,
                                self.nominal_nonrecovered_mL, rel_tol=0.0, abs_tol=_TOL):
                raise WasteFluidAccountingError("minimum-residual prime-adjusted allocation does not conserve nominal liquid")
            if not math.isclose(self.residual_allocation_max_mL + self.leakage_allocation_min_mL,
                                self.nominal_nonrecovered_mL, rel_tol=0.0, abs_tol=_TOL):
                raise WasteFluidAccountingError("maximum-residual prime-adjusted allocation does not conserve nominal liquid")


def _derive(allocation: ComponentRecoveryAllocation, routing: CycleResolvedRoutingClosure) -> dict[str, float | bool]:
    ledger = allocation.source_ledger
    if ledger.cycles != len(routing.cycles):
        raise WasteFluidAccountingError("component allocation and cycle routing must cover the same service interval")
    budget = ledger.source_budget
    service = routing.service
    expected_residual_ceiling = ledger.cycles * budget.residual_free_liquid_max_mL
    expected_leakage_ceiling = ledger.cycles * budget.external_leakage_max_mL_per_cycle
    if not math.isclose(service.service_residual_ceiling_mL, expected_residual_ceiling, rel_tol=0.0, abs_tol=_TOL):
        raise WasteFluidAccountingError("cycle routing residual ceiling does not match component allocation authority")
    if not math.isclose(service.service_external_leakage_ceiling_mL, expected_leakage_ceiling, rel_tol=0.0, abs_tol=_TOL):
        raise WasteFluidAccountingError("cycle routing leakage ceiling does not match component allocation authority")
    if not math.isclose(
        service.minimum_nominal_liquid_routed_to_cartridge_mL,
        ledger.minimum_service_recovery_mL,
        rel_tol=0.0,
        abs_tol=_TOL,
    ):
        raise WasteFluidAccountingError("cycle routing recovery floor does not match component allocation authority")
    prime_residual = routing.total_prime_residual_mL
    prime_leakage = routing.total_prime_external_leakage_mL
    residual_capacity = expected_residual_ceiling - prime_residual
    leakage_capacity = expected_leakage_ceiling - prime_leakage
    if residual_capacity < -_TOL or leakage_capacity < -_TOL:
        raise WasteFluidAccountingError("prime routing exceeds a shared classified sink ceiling")
    residual_capacity = max(0.0, residual_capacity)
    leakage_capacity = max(0.0, leakage_capacity)
    nonrecovered = allocation.total_nonrecovered_mL
    classified = residual_capacity + leakage_capacity

    # The delivery/recovery ledger is the authority-bound source for nominal liquid.
    # Keep this reducer coupled to its released field names rather than reconstructing
    # the total independently from components, so delivery changes remain provenance-bound.
    introduced = ledger.service_nominal_mL
    recovery_floor = ledger.minimum_service_recovery_mL
    minimum_recovery_for_closure = max(0.0, introduced - classified)
    if introduced <= _TOL:
        raise WasteFluidAccountingError("prime-adjusted sink closure requires positive introduced liquid")
    minimum_recovery_ratio = minimum_recovery_for_closure / introduced
    additional_above_floor = max(0.0, minimum_recovery_for_closure - recovery_floor)

    residual_min = max(0.0, nonrecovered - leakage_capacity)
    residual_max = min(nonrecovered, residual_capacity)
    leakage_min = max(0.0, nonrecovered - residual_capacity)
    leakage_max = min(nonrecovered, leakage_capacity)
    deficit = max(0.0, nonrecovered - classified)
    return {
        "nominal_nonrecovered_mL": nonrecovered,
        "prime_residual_mL": prime_residual,
        "prime_external_leakage_mL": prime_leakage,
        "residual_capacity_after_prime_mL": residual_capacity,
        "leakage_capacity_after_prime_mL": leakage_capacity,
        "classified_capacity_after_prime_mL": classified,
        "minimum_nominal_recovery_for_sink_closure_mL": minimum_recovery_for_closure,
        "minimum_nominal_recovery_ratio_for_sink_closure": minimum_recovery_ratio,
        "additional_recovery_above_requirement_floor_mL": additional_above_floor,
        "residual_allocation_min_mL": residual_min,
        "residual_allocation_max_mL": residual_max,
        "leakage_allocation_min_mL": leakage_min,
        "leakage_allocation_max_mL": leakage_max,
        "unclassified_nominal_liquid_mL": deficit,
        "feasible": deficit <= _TOL,
    }


def evaluate_prime_adjusted_component_sink_closure(
    allocation: ComponentRecoveryAllocation,
    routing: CycleResolvedRoutingClosure,
) -> PrimeAdjustedComponentSinkClosure:
    """Classify concrete nominal nonrecovery after cycle-resolved prime sink use."""
    if type(allocation) is not ComponentRecoveryAllocation or type(routing) is not CycleResolvedRoutingClosure:
        raise WasteFluidAccountingError("prime-adjusted sink closure requires exact allocation and routing evidence")
    allocation.__post_init__()
    routing.__post_init__()
    values = _derive(allocation, routing)
    result = PrimeAdjustedComponentSinkClosure(allocation, routing, **values)
    result.__post_init__()
    return result
