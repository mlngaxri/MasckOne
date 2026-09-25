"""Recovery requirement implied by shared residual and leakage sink capacity.

This reducer converts the service routing closure into the minimum nominal recovery
ratio needed to keep all nominal nonrecovery inside the residual and external-leakage
ceilings after explicit prime-liquid sink allocations. It is a digital requirement
consistency calculation, not a physical recovery prediction or validation result.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

from .waste_fluid_accounting import WasteFluidAccountingError, WasteFluidBudget
from .waste_fluid_closure import ServiceRoutingClosure, screen_service_routing_closure

_TOL = 1e-12


@dataclass(frozen=True, slots=True)
class ServiceRecoveryRequirement:
    """Minimum nominal recovery needed to close the configured service routing."""

    source_budget: WasteFluidBudget
    source: ServiceRoutingClosure
    authority_recovery_ratio_min: float
    nominal_service_liquid_mL: float
    available_nominal_nonrecovery_sink_mL: float
    required_nominal_recovery_mL: float
    required_nominal_recovery_ratio: float
    recovery_ratio_shortfall: float
    additional_nominal_recovery_required_mL: float
    recovery_requirement_closes: bool

    def __post_init__(self) -> None:
        if type(self.source_budget) is not WasteFluidBudget:
            raise WasteFluidAccountingError("recovery requirement requires exact WasteFluidBudget evidence")
        self.source_budget.validate()
        if type(self.source) is not ServiceRoutingClosure:
            raise WasteFluidAccountingError("recovery requirement requires exact ServiceRoutingClosure evidence")
        numeric = (
            self.authority_recovery_ratio_min,
            self.nominal_service_liquid_mL,
            self.available_nominal_nonrecovery_sink_mL,
            self.required_nominal_recovery_mL,
            self.required_nominal_recovery_ratio,
            self.recovery_ratio_shortfall,
            self.additional_nominal_recovery_required_mL,
        )
        if any(type(value) not in (int, float) or not math.isfinite(float(value)) for value in numeric):
            raise WasteFluidAccountingError("recovery requirement evidence must be finite numeric data")
        if not 0.0 <= self.authority_recovery_ratio_min <= 1.0:
            raise WasteFluidAccountingError("authority recovery ratio must be between zero and one")
        if self.nominal_service_liquid_mL <= _TOL:
            raise WasteFluidAccountingError("nominal service liquid must be positive")
        if not 0.0 <= self.required_nominal_recovery_ratio <= 1.0:
            raise WasteFluidAccountingError("required nominal recovery ratio must be between zero and one")
        if self.available_nominal_nonrecovery_sink_mL < -_TOL:
            raise WasteFluidAccountingError("available nominal nonrecovery sink cannot be negative")
        if self.required_nominal_recovery_mL < -_TOL:
            raise WasteFluidAccountingError("required nominal recovery cannot be negative")
        if self.recovery_ratio_shortfall < -_TOL or self.additional_nominal_recovery_required_mL < -_TOL:
            raise WasteFluidAccountingError("recovery shortfall evidence cannot be negative")

        # Bind all recovery arithmetic back to the exact fluid-budget values that
        # produced the routing closure. Without this check a copied result could
        # previously replace nominal volume or recovery floor and remain self-consistent.
        expected_nominal = self.source_budget.nominal_introduced_mL_per_cycle * self.source.cycles
        if not math.isclose(self.nominal_service_liquid_mL, expected_nominal, rel_tol=0.0, abs_tol=_TOL):
            raise WasteFluidAccountingError("nominal service liquid is inconsistent with source budget")
        if not math.isclose(
            self.authority_recovery_ratio_min,
            self.source_budget.recovery_ratio_min,
            rel_tol=0.0,
            abs_tol=_TOL,
        ):
            raise WasteFluidAccountingError("authority recovery ratio is inconsistent with source budget")
        expected_nominal_routed = self.source_budget.minimum_recovered_mL_per_cycle * self.source.cycles
        if not math.isclose(
            self.source.minimum_nominal_liquid_routed_to_cartridge_mL,
            expected_nominal_routed,
            rel_tol=0.0,
            abs_tol=_TOL,
        ):
            raise WasteFluidAccountingError("routing closure nominal recovery is inconsistent with source budget")
        expected_residual_ceiling = self.source_budget.residual_free_liquid_max_mL * self.source.cycles
        expected_leakage_ceiling = self.source_budget.external_leakage_max_mL_per_cycle * self.source.cycles
        if not math.isclose(self.source.service_residual_ceiling_mL, expected_residual_ceiling, rel_tol=0.0, abs_tol=_TOL):
            raise WasteFluidAccountingError("routing closure residual ceiling is inconsistent with source budget")
        if not math.isclose(self.source.service_external_leakage_ceiling_mL, expected_leakage_ceiling, rel_tol=0.0, abs_tol=_TOL):
            raise WasteFluidAccountingError("routing closure leakage ceiling is inconsistent with source budget")
        expected_prime = self.source_budget.maximum_initial_prime_mL_per_cycle * self.source.prime_events
        if not math.isclose(self.source.total_prime_liquid_mL, expected_prime, rel_tol=0.0, abs_tol=_TOL):
            raise WasteFluidAccountingError("routing closure prime volume is inconsistent with source budget")

        expected_sink = self.source.prime_residual_ceiling_margin_mL + self.source.prime_external_leakage_ceiling_margin_mL
        expected_required_mL = max(0.0, expected_nominal - expected_sink)
        expected_ratio = min(1.0, expected_required_mL / expected_nominal)
        expected_shortfall = max(0.0, expected_ratio - self.source_budget.recovery_ratio_min)
        expected_additional = max(
            0.0,
            expected_required_mL - expected_nominal * self.source_budget.recovery_ratio_min,
        )
        checks = (
            (self.available_nominal_nonrecovery_sink_mL, expected_sink, "available sink"),
            (self.required_nominal_recovery_mL, expected_required_mL, "required recovery volume"),
            (self.required_nominal_recovery_ratio, expected_ratio, "required recovery ratio"),
            (self.recovery_ratio_shortfall, expected_shortfall, "recovery ratio shortfall"),
            (self.additional_nominal_recovery_required_mL, expected_additional, "additional recovery volume"),
        )
        for actual, expected, label in checks:
            if not math.isclose(actual, expected, rel_tol=0.0, abs_tol=_TOL):
                raise WasteFluidAccountingError(f"recovery requirement {label} is inconsistent with source evidence")
        expected_closes = expected_shortfall <= _TOL
        if type(self.recovery_requirement_closes) is not bool or self.recovery_requirement_closes != expected_closes:
            raise WasteFluidAccountingError("recovery closure decision is inconsistent with recovery shortfall")


def derive_service_recovery_requirement(
    budget: WasteFluidBudget,
    *,
    cycles: int,
    prime_events: int,
    prime_recovery_ratio_contract: float | None = None,
    prime_residual_ratio_contract: float | None = None,
    prime_external_leakage_ratio_contract: float | None = None,
) -> ServiceRecoveryRequirement:
    """Derive the nominal recovery floor required after explicit prime sink use."""
    budget.validate()
    source = screen_service_routing_closure(
        budget,
        cycles=cycles,
        prime_events=prime_events,
        prime_recovery_ratio_contract=prime_recovery_ratio_contract,
        prime_residual_ratio_contract=prime_residual_ratio_contract,
        prime_external_leakage_ratio_contract=prime_external_leakage_ratio_contract,
    )
    nominal_total = budget.nominal_introduced_mL_per_cycle * cycles
    if nominal_total <= _TOL:
        raise WasteFluidAccountingError("nominal service liquid must be positive")
    available_sink = source.prime_residual_ceiling_margin_mL + source.prime_external_leakage_ceiling_margin_mL
    required_recovery_mL = max(0.0, nominal_total - available_sink)
    required_ratio = min(1.0, max(0.0, required_recovery_mL / nominal_total))
    ratio_shortfall = max(0.0, required_ratio - budget.recovery_ratio_min)
    additional_recovery = max(0.0, required_recovery_mL - nominal_total * budget.recovery_ratio_min)

    return ServiceRecoveryRequirement(
        source_budget=budget,
        source=source,
        authority_recovery_ratio_min=budget.recovery_ratio_min,
        nominal_service_liquid_mL=nominal_total,
        available_nominal_nonrecovery_sink_mL=available_sink,
        required_nominal_recovery_mL=required_recovery_mL,
        required_nominal_recovery_ratio=required_ratio,
        recovery_ratio_shortfall=ratio_shortfall,
        additional_nominal_recovery_required_mL=additional_recovery,
        recovery_requirement_closes=ratio_shortfall <= _TOL,
    )
