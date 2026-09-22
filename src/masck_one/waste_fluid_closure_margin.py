"""Quantify service recovery closure margin without changing fluid authority.

This module converts an exact ServiceRecoveryRequirement into per-cycle design
margin evidence. It is a synthetic requirement-consistency calculation, not a
physical recovery or leakage validation result.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

from .waste_fluid_accounting import WasteFluidAccountingError
from .waste_fluid_recovery_requirement import ServiceRecoveryRequirement

_TOL = 1e-12


@dataclass(frozen=True, slots=True)
class ServiceClosureMargin:
    source: ServiceRecoveryRequirement
    cycles: int
    configured_nominal_nonrecovery_mL: float
    available_sink_mL: float
    service_deficit_mL: float
    deficit_mL_per_cycle: float
    required_combined_sink_mL_per_cycle_at_authority_recovery: float
    configured_combined_sink_mL_per_cycle: float
    combined_sink_shortfall_mL_per_cycle: float
    closes: bool

    def __post_init__(self) -> None:
        if type(self.source) is not ServiceRecoveryRequirement:
            raise WasteFluidAccountingError("closure margin requires exact ServiceRecoveryRequirement evidence")
        if type(self.cycles) is not int or self.cycles <= 0 or self.cycles != self.source.source.cycles:
            raise WasteFluidAccountingError("closure margin cycle count is inconsistent with source evidence")
        numeric = (
            self.configured_nominal_nonrecovery_mL,
            self.available_sink_mL,
            self.service_deficit_mL,
            self.deficit_mL_per_cycle,
            self.required_combined_sink_mL_per_cycle_at_authority_recovery,
            self.configured_combined_sink_mL_per_cycle,
            self.combined_sink_shortfall_mL_per_cycle,
        )
        if any(type(v) not in (int, float) or not math.isfinite(float(v)) or v < -_TOL for v in numeric):
            raise WasteFluidAccountingError("closure margin evidence must be finite and nonnegative")

        budget = self.source.source_budget
        expected_nonrecovery = self.source.nominal_service_liquid_mL * (1.0 - budget.recovery_ratio_min)
        expected_sink = self.source.available_nominal_nonrecovery_sink_mL
        expected_deficit = max(0.0, expected_nonrecovery - expected_sink)
        expected_deficit_per_cycle = expected_deficit / self.cycles
        expected_required_sink_per_cycle = expected_nonrecovery / self.cycles
        expected_configured_sink_per_cycle = expected_sink / self.cycles
        expected_sink_shortfall = max(0.0, expected_required_sink_per_cycle - expected_configured_sink_per_cycle)
        checks = (
            (self.configured_nominal_nonrecovery_mL, expected_nonrecovery, "configured nonrecovery"),
            (self.available_sink_mL, expected_sink, "available sink"),
            (self.service_deficit_mL, expected_deficit, "service deficit"),
            (self.deficit_mL_per_cycle, expected_deficit_per_cycle, "per-cycle deficit"),
            (self.required_combined_sink_mL_per_cycle_at_authority_recovery, expected_required_sink_per_cycle, "required sink"),
            (self.configured_combined_sink_mL_per_cycle, expected_configured_sink_per_cycle, "configured sink"),
            (self.combined_sink_shortfall_mL_per_cycle, expected_sink_shortfall, "sink shortfall"),
        )
        for actual, expected, label in checks:
            if not math.isclose(actual, expected, rel_tol=0.0, abs_tol=_TOL):
                raise WasteFluidAccountingError(f"closure margin {label} is inconsistent with source evidence")
        expected_closes = expected_deficit <= _TOL
        if type(self.closes) is not bool or self.closes != expected_closes:
            raise WasteFluidAccountingError("closure margin decision is inconsistent with source evidence")


def derive_service_closure_margin(requirement: ServiceRecoveryRequirement) -> ServiceClosureMargin:
    """Reduce recovery evidence to explicit service and per-cycle closure margins."""
    if type(requirement) is not ServiceRecoveryRequirement:
        raise WasteFluidAccountingError("closure margin requires exact ServiceRecoveryRequirement evidence")
    cycles = requirement.source.cycles
    budget = requirement.source_budget
    configured_nonrecovery = requirement.nominal_service_liquid_mL * (1.0 - budget.recovery_ratio_min)
    available_sink = requirement.available_nominal_nonrecovery_sink_mL
    deficit = max(0.0, configured_nonrecovery - available_sink)
    required_sink_per_cycle = configured_nonrecovery / cycles
    configured_sink_per_cycle = available_sink / cycles
    return ServiceClosureMargin(
        source=requirement,
        cycles=cycles,
        configured_nominal_nonrecovery_mL=configured_nonrecovery,
        available_sink_mL=available_sink,
        service_deficit_mL=deficit,
        deficit_mL_per_cycle=deficit / cycles,
        required_combined_sink_mL_per_cycle_at_authority_recovery=required_sink_per_cycle,
        configured_combined_sink_mL_per_cycle=configured_sink_per_cycle,
        combined_sink_shortfall_mL_per_cycle=max(0.0, required_sink_per_cycle - configured_sink_per_cycle),
        closes=deficit <= _TOL,
    )
