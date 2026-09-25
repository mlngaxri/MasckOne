"""Classified-sink closure for a concrete clean-cycle recovery allocation.

This reducer connects component recovery conservation to the independent residual
and external-leakage ceilings. It is digital requirement arithmetic only and does
not treat a candidate allocation as measured recovery evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

from .waste_fluid_accounting import WasteFluidAccountingError
from .waste_fluid_component_recovery_allocation import ComponentRecoveryAllocation

_TOL = 1e-12


@dataclass(frozen=True, slots=True)
class ComponentSinkClosure:
    source: ComponentRecoveryAllocation
    nonrecovered_mL: float
    residual_capacity_mL: float
    leakage_capacity_mL: float
    residual_allocation_min_mL: float
    residual_allocation_max_mL: float
    leakage_allocation_min_mL: float
    leakage_allocation_max_mL: float
    classified_capacity_mL: float
    unclassified_liquid_mL: float
    feasible: bool

    def __post_init__(self) -> None:
        if type(self.source) is not ComponentRecoveryAllocation:
            raise WasteFluidAccountingError("component sink closure requires exact recovery allocation source")
        self.source.__post_init__()
        numeric = (
            self.nonrecovered_mL, self.residual_capacity_mL, self.leakage_capacity_mL,
            self.residual_allocation_min_mL, self.residual_allocation_max_mL,
            self.leakage_allocation_min_mL, self.leakage_allocation_max_mL,
            self.classified_capacity_mL, self.unclassified_liquid_mL,
        )
        if any(type(v) not in (int, float) or not math.isfinite(float(v)) or v < -_TOL for v in numeric):
            raise WasteFluidAccountingError("component sink closure values must be finite and nonnegative")
        if type(self.feasible) is not bool:
            raise WasteFluidAccountingError("component sink closure decision must be boolean")

        budget = self.source.source_ledger.source_budget
        nonrecovered = self.source.total_nonrecovered_mL
        residual_capacity = self.source.source_ledger.cycles * budget.residual_free_liquid_max_mL
        leakage_capacity = self.source.source_ledger.cycles * budget.external_leakage_max_mL_per_cycle
        classified_capacity = residual_capacity + leakage_capacity
        residual_min = max(0.0, nonrecovered - leakage_capacity)
        residual_max = min(nonrecovered, residual_capacity)
        leakage_min = max(0.0, nonrecovered - residual_capacity)
        leakage_max = min(nonrecovered, leakage_capacity)
        deficit = max(0.0, nonrecovered - classified_capacity)
        feasible = deficit <= _TOL
        checks = (
            (self.nonrecovered_mL, nonrecovered, "nonrecovered volume"),
            (self.residual_capacity_mL, residual_capacity, "residual capacity"),
            (self.leakage_capacity_mL, leakage_capacity, "leakage capacity"),
            (self.residual_allocation_min_mL, residual_min, "minimum residual allocation"),
            (self.residual_allocation_max_mL, residual_max, "maximum residual allocation"),
            (self.leakage_allocation_min_mL, leakage_min, "minimum leakage allocation"),
            (self.leakage_allocation_max_mL, leakage_max, "maximum leakage allocation"),
            (self.classified_capacity_mL, classified_capacity, "classified capacity"),
            (self.unclassified_liquid_mL, deficit, "unclassified liquid"),
        )
        for actual, expected, label in checks:
            if not math.isclose(actual, expected, rel_tol=0.0, abs_tol=_TOL):
                raise WasteFluidAccountingError(f"component sink closure {label} does not reconcile")
        if self.feasible != feasible:
            raise WasteFluidAccountingError("component sink closure decision does not reconcile")
        if feasible:
            if not math.isclose(residual_min + leakage_max, nonrecovered, rel_tol=0.0, abs_tol=_TOL):
                raise WasteFluidAccountingError("minimum-residual sink allocation does not conserve liquid")
            if not math.isclose(residual_max + leakage_min, nonrecovered, rel_tol=0.0, abs_tol=_TOL):
                raise WasteFluidAccountingError("maximum-residual sink allocation does not conserve liquid")


def evaluate_component_sink_closure(allocation: ComponentRecoveryAllocation) -> ComponentSinkClosure:
    """Check whether a concrete recovery allocation can fit the classified sinks."""
    if type(allocation) is not ComponentRecoveryAllocation:
        raise WasteFluidAccountingError("component sink closure requires exact recovery allocation source")
    allocation.__post_init__()
    budget = allocation.source_ledger.source_budget
    cycles = allocation.source_ledger.cycles
    nonrecovered = allocation.total_nonrecovered_mL
    residual_capacity = cycles * budget.residual_free_liquid_max_mL
    leakage_capacity = cycles * budget.external_leakage_max_mL_per_cycle
    classified_capacity = residual_capacity + leakage_capacity
    residual_min = max(0.0, nonrecovered - leakage_capacity)
    residual_max = min(nonrecovered, residual_capacity)
    leakage_min = max(0.0, nonrecovered - residual_capacity)
    leakage_max = min(nonrecovered, leakage_capacity)
    deficit = max(0.0, nonrecovered - classified_capacity)
    result = ComponentSinkClosure(
        source=allocation,
        nonrecovered_mL=nonrecovered,
        residual_capacity_mL=residual_capacity,
        leakage_capacity_mL=leakage_capacity,
        residual_allocation_min_mL=residual_min,
        residual_allocation_max_mL=residual_max,
        leakage_allocation_min_mL=leakage_min,
        leakage_allocation_max_mL=leakage_max,
        classified_capacity_mL=classified_capacity,
        unclassified_liquid_mL=deficit,
        feasible=deficit <= _TOL,
    )
    result.__post_init__()
    return result
