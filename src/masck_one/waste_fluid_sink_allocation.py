"""Feasible nominal nonrecovery allocation across residual and leakage sinks.

This reducer preserves the individual sink ceilings after prime routing instead of
checking only their sum. It is requirement arithmetic, not physical validation.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

from .waste_fluid_accounting import WasteFluidAccountingError
from .waste_fluid_recovery_requirement import ServiceRecoveryRequirement

_TOL = 1e-12


@dataclass(frozen=True, slots=True)
class ServiceSinkAllocationWindow:
    source: ServiceRecoveryRequirement
    nominal_nonrecovery_mL: float
    residual_capacity_mL: float
    leakage_capacity_mL: float
    residual_allocation_min_mL: float
    residual_allocation_max_mL: float
    leakage_allocation_min_mL: float
    leakage_allocation_max_mL: float
    feasible: bool

    def __post_init__(self) -> None:
        if type(self.source) is not ServiceRecoveryRequirement:
            raise WasteFluidAccountingError("sink allocation requires exact ServiceRecoveryRequirement evidence")
        numeric = (
            self.nominal_nonrecovery_mL, self.residual_capacity_mL, self.leakage_capacity_mL,
            self.residual_allocation_min_mL, self.residual_allocation_max_mL,
            self.leakage_allocation_min_mL, self.leakage_allocation_max_mL,
        )
        if any(type(v) not in (int, float) or not math.isfinite(float(v)) or v < -_TOL for v in numeric):
            raise WasteFluidAccountingError("sink allocation evidence must be finite and nonnegative")

        budget = self.source.source_budget
        nonrecovery = self.source.nominal_service_liquid_mL * (1.0 - budget.recovery_ratio_min)
        residual_capacity = self.source.source.prime_residual_ceiling_margin_mL
        leakage_capacity = self.source.source.prime_external_leakage_ceiling_margin_mL
        residual_min = max(0.0, nonrecovery - leakage_capacity)
        residual_max = min(nonrecovery, residual_capacity)
        leakage_min = max(0.0, nonrecovery - residual_capacity)
        leakage_max = min(nonrecovery, leakage_capacity)
        feasible = residual_min <= residual_max + _TOL and leakage_min <= leakage_max + _TOL
        checks = (
            (self.nominal_nonrecovery_mL, nonrecovery, "nominal nonrecovery"),
            (self.residual_capacity_mL, residual_capacity, "residual capacity"),
            (self.leakage_capacity_mL, leakage_capacity, "leakage capacity"),
            (self.residual_allocation_min_mL, residual_min, "minimum residual allocation"),
            (self.residual_allocation_max_mL, residual_max, "maximum residual allocation"),
            (self.leakage_allocation_min_mL, leakage_min, "minimum leakage allocation"),
            (self.leakage_allocation_max_mL, leakage_max, "maximum leakage allocation"),
        )
        for actual, expected, label in checks:
            if not math.isclose(actual, expected, rel_tol=0.0, abs_tol=_TOL):
                raise WasteFluidAccountingError(f"sink allocation {label} is inconsistent with source evidence")
        if type(self.feasible) is not bool or self.feasible != feasible:
            raise WasteFluidAccountingError("sink allocation feasibility is inconsistent with source evidence")
        if feasible:
            if not math.isclose(residual_min + leakage_max, nonrecovery, rel_tol=0.0, abs_tol=_TOL):
                raise WasteFluidAccountingError("minimum-residual allocation does not conserve nominal liquid")
            if not math.isclose(residual_max + leakage_min, nonrecovery, rel_tol=0.0, abs_tol=_TOL):
                raise WasteFluidAccountingError("maximum-residual allocation does not conserve nominal liquid")


def derive_service_sink_allocation_window(requirement: ServiceRecoveryRequirement) -> ServiceSinkAllocationWindow:
    if type(requirement) is not ServiceRecoveryRequirement:
        raise WasteFluidAccountingError("sink allocation requires exact ServiceRecoveryRequirement evidence")
    budget = requirement.source_budget
    nonrecovery = requirement.nominal_service_liquid_mL * (1.0 - budget.recovery_ratio_min)
    residual_capacity = requirement.source.prime_residual_ceiling_margin_mL
    leakage_capacity = requirement.source.prime_external_leakage_ceiling_margin_mL
    residual_min = max(0.0, nonrecovery - leakage_capacity)
    residual_max = min(nonrecovery, residual_capacity)
    leakage_min = max(0.0, nonrecovery - residual_capacity)
    leakage_max = min(nonrecovery, leakage_capacity)
    feasible = residual_min <= residual_max + _TOL and leakage_min <= leakage_max + _TOL
    return ServiceSinkAllocationWindow(
        source=requirement,
        nominal_nonrecovery_mL=nonrecovery,
        residual_capacity_mL=residual_capacity,
        leakage_capacity_mL=leakage_capacity,
        residual_allocation_min_mL=residual_min,
        residual_allocation_max_mL=residual_max,
        leakage_allocation_min_mL=leakage_min,
        leakage_allocation_max_mL=leakage_max,
        feasible=feasible,
    )
