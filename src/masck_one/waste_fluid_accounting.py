"""Authority-bound digital fluid and cartridge budget checks.

This module performs conservation and capacity screens only. It does not claim
physical recovery, leakage, residual liquid, retained capacity, or pump behavior.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

from .authority import Authority, load_authority


class WasteFluidAccountingError(ValueError):
    """Raised when a fluid budget is internally inconsistent or exceeds authority."""


@dataclass(frozen=True)
class WasteFluidBudget:
    service_cycles: int
    nominal_introduced_mL_per_cycle: float
    maximum_initial_prime_mL_per_cycle: float
    recovery_ratio_min: float
    residual_free_liquid_max_mL: float
    external_leakage_max_mL_per_cycle: float
    cartridge_retained_capacity_requirement_mL: float

    @property
    def maximum_liquid_presented_to_recovery_mL_per_cycle(self) -> float:
        return self.nominal_introduced_mL_per_cycle + self.maximum_initial_prime_mL_per_cycle

    @property
    def minimum_recovered_mL_per_cycle(self) -> float:
        return self.nominal_introduced_mL_per_cycle * self.recovery_ratio_min

    @property
    def maximum_cartridge_inflow_screen_mL(self) -> float:
        # Deliberately conservative: credit no residual or external leakage and assume
        # the maximum prime can occur on every cycle. This is a packaging screen, not
        # a prediction of retained liquid.
        return self.service_cycles * self.maximum_liquid_presented_to_recovery_mL_per_cycle

    @property
    def cartridge_requirement_margin_mL(self) -> float:
        return self.cartridge_retained_capacity_requirement_mL - self.maximum_cartridge_inflow_screen_mL

    def validate(self) -> None:
        numeric = (
            self.nominal_introduced_mL_per_cycle,
            self.maximum_initial_prime_mL_per_cycle,
            self.recovery_ratio_min,
            self.residual_free_liquid_max_mL,
            self.external_leakage_max_mL_per_cycle,
            self.cartridge_retained_capacity_requirement_mL,
        )
        if type(self.service_cycles) is not int or self.service_cycles <= 0:
            raise WasteFluidAccountingError("service_cycles must be a positive integer")
        if any(type(v) not in (int, float) or not math.isfinite(v) or v < 0 for v in numeric):
            raise WasteFluidAccountingError("fluid budget values must be finite and nonnegative")
        if not 0.0 <= self.recovery_ratio_min <= 1.0:
            raise WasteFluidAccountingError("recovery ratio must be between zero and one")
        if self.minimum_recovered_mL_per_cycle > self.maximum_liquid_presented_to_recovery_mL_per_cycle:
            raise WasteFluidAccountingError("minimum recovery exceeds available liquid")
        if self.cartridge_requirement_margin_mL < -1e-12:
            raise WasteFluidAccountingError("authority cartridge requirement is below conservative cycle inflow screen")

    def manifest(self) -> dict[str, object]:
        self.validate()
        return {
            "scope": "DIGITAL_CONSERVATION_AND_CAPACITY_SCREEN_ONLY",
            "service_cycles": self.service_cycles,
            "nominal_introduced_mL_per_cycle": self.nominal_introduced_mL_per_cycle,
            "maximum_initial_prime_mL_per_cycle": self.maximum_initial_prime_mL_per_cycle,
            "maximum_liquid_presented_to_recovery_mL_per_cycle": self.maximum_liquid_presented_to_recovery_mL_per_cycle,
            "minimum_recovered_mL_per_cycle": self.minimum_recovered_mL_per_cycle,
            "recovery_ratio_min": self.recovery_ratio_min,
            "residual_free_liquid_max_mL": self.residual_free_liquid_max_mL,
            "external_leakage_max_mL_per_cycle": self.external_leakage_max_mL_per_cycle,
            "maximum_cartridge_inflow_screen_mL": self.maximum_cartridge_inflow_screen_mL,
            "cartridge_retained_capacity_requirement_mL": self.cartridge_retained_capacity_requirement_mL,
            "cartridge_requirement_margin_mL": self.cartridge_requirement_margin_mL,
            "physical_validation_eligible": False,
        }


def build_authority_waste_fluid_budget(authority: Authority | None = None) -> WasteFluidBudget:
    authority = authority or load_authority()
    face_water = authority.number("fluid", "clean_cycle", "face_water_mL")
    cleanser = authority.number("fluid", "clean_cycle", "cleanser_mL")
    post_flush = authority.number("fluid", "clean_cycle", "post_flush_water_mL")
    nominal = authority.number("fluid", "clean_cycle", "nominal_introduced_liquid_mL")
    if not math.isclose(face_water + cleanser + post_flush, nominal, rel_tol=0.0, abs_tol=1e-12):
        raise WasteFluidAccountingError("clean-cycle component volumes do not reconcile to nominal introduced liquid")

    budget = WasteFluidBudget(
        service_cycles=int(authority.number("fluid", "cartridge", "service_cycles_baseline")),
        nominal_introduced_mL_per_cycle=nominal,
        maximum_initial_prime_mL_per_cycle=authority.number("fluid", "clean_cycle", "maximum_initial_prime_mL"),
        recovery_ratio_min=authority.number("fluid", "waste", "recovery_ratio_min"),
        residual_free_liquid_max_mL=authority.number("fluid", "waste", "residual_free_liquid_max_uL") / 1000.0,
        external_leakage_max_mL_per_cycle=authority.number("safety", "fluid_fault", "max_external_leakage_uL_cycle") / 1000.0,
        cartridge_retained_capacity_requirement_mL=authority.number("fluid", "cartridge", "retained_capacity_min_mL"),
    )
    budget.validate()
    return budget
