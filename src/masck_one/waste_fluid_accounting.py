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
class ServiceCapacityScreen:
    """Cumulative cartridge loading for a specified digital service profile."""

    cycles: int
    prime_events: int
    nominal_liquid_mL: float
    prime_liquid_mL: float
    minimum_recovered_nominal_mL: float
    maximum_cartridge_inflow_mL: float
    requirement_margin_mL: float
    capacity_satisfied: bool

    @property
    def occupancy_uncertainty_mL(self) -> float:
        """Gap between guaranteed nominal recovery and fail-conservative inflow."""
        return self.maximum_cartridge_inflow_mL - self.minimum_recovered_nominal_mL


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
    def maximum_unrecovered_nominal_mL_per_cycle(self) -> float:
        return self.nominal_introduced_mL_per_cycle - self.minimum_recovered_mL_per_cycle

    @property
    def maximum_classified_nonrecovery_mL_per_cycle(self) -> float:
        return self.residual_free_liquid_max_mL + self.external_leakage_max_mL_per_cycle

    @property
    def recovery_ratio_for_residual_leakage_closure(self) -> float:
        """Recovery needed if residual and leakage are the only nonrecovery sinks."""
        if self.nominal_introduced_mL_per_cycle == 0.0:
            return 1.0
        return max(0.0, 1.0 - self.maximum_classified_nonrecovery_mL_per_cycle / self.nominal_introduced_mL_per_cycle)

    @property
    def recovery_ratio_closure_delta(self) -> float:
        return self.recovery_ratio_for_residual_leakage_closure - self.recovery_ratio_min

    @staticmethod
    def _require_finite_capacity_arithmetic(**values: float) -> None:
        nonfinite = tuple(name for name, value in values.items() if not math.isfinite(value))
        if nonfinite:
            raise WasteFluidAccountingError(
                "capacity arithmetic produced nonfinite value(s): " + ", ".join(nonfinite)
            )

    def service_capacity_screen(self, *, cycles: int, prime_events: int) -> ServiceCapacityScreen:
        """Bound retained occupancy for an in-authority service-life interval.

        The lower bound counts only nominal liquid that must be recovered at the
        authority recovery floor. The upper bound charges every introduced nominal
        and prime volume to the cartridge, taking no residual/leakage credit. Prime
        recovery is intentionally not assumed because no authority recovery fraction
        for prime liquid exists. This interval therefore remains conservative at both
        ends until physical routing and recovery data exist.

        ``cycles`` may describe a prefix of the configured service life, but may not
        extend beyond it. This prevents capacity checks from silently reusing a
        cartridge beyond the authority service interval.
        """
        if type(cycles) is not int or cycles <= 0:
            raise WasteFluidAccountingError("cycles must be a positive integer")
        if cycles > self.service_cycles:
            raise WasteFluidAccountingError(
                "cycles exceeds configured service life: "
                f"{cycles} requested for {self.service_cycles} service cycles"
            )
        if type(prime_events) is not int or prime_events < 0:
            raise WasteFluidAccountingError("prime_events must be a nonnegative integer")
        nominal = cycles * self.nominal_introduced_mL_per_cycle
        prime = prime_events * self.maximum_initial_prime_mL_per_cycle
        minimum_recovered = cycles * self.minimum_recovered_mL_per_cycle
        inflow = nominal + prime
        margin = self.cartridge_retained_capacity_requirement_mL - inflow
        self._require_finite_capacity_arithmetic(
            nominal_liquid_mL=nominal,
            prime_liquid_mL=prime,
            minimum_recovered_nominal_mL=minimum_recovered,
            maximum_cartridge_inflow_mL=inflow,
            requirement_margin_mL=margin,
        )
        return ServiceCapacityScreen(
            cycles=cycles,
            prime_events=prime_events,
            nominal_liquid_mL=nominal,
            prime_liquid_mL=prime,
            minimum_recovered_nominal_mL=minimum_recovered,
            maximum_cartridge_inflow_mL=inflow,
            requirement_margin_mL=margin,
            capacity_satisfied=margin >= -1e-12,
        )

    def maximum_prime_events_that_fit(self, *, cycles: int) -> int | None:
        baseline = self.service_capacity_screen(cycles=cycles, prime_events=0)
        if not baseline.capacity_satisfied:
            raise WasteFluidAccountingError("nominal service liquid alone exceeds cartridge requirement")
        if self.maximum_initial_prime_mL_per_cycle == 0.0:
            return None
        quotient = (baseline.requirement_margin_mL + 1e-12) / self.maximum_initial_prime_mL_per_cycle
        self._require_finite_capacity_arithmetic(maximum_prime_events_quotient=quotient)
        return math.floor(quotient)

    def maximum_service_cycles_that_fit(self, *, prime_events: int) -> int | None:
        """Return packaging capacity in cycles after reserving explicit reprime volume.

        This is deliberately a packaging calculation rather than a service-profile
        authorization. It may report capacity beyond ``service_cycles``; callers that
        model an actual service interval must use ``service_capacity_screen``, which
        enforces the configured service-life boundary.
        """
        if type(prime_events) is not int or prime_events < 0:
            raise WasteFluidAccountingError("prime_events must be a nonnegative integer")
        prime = prime_events * self.maximum_initial_prime_mL_per_cycle
        remaining = self.cartridge_retained_capacity_requirement_mL - prime
        self._require_finite_capacity_arithmetic(prime_liquid_mL=prime, remaining_capacity_mL=remaining)
        if remaining < -1e-12:
            raise WasteFluidAccountingError("prime liquid alone exceeds cartridge requirement")
        if self.nominal_introduced_mL_per_cycle == 0.0:
            return None
        quotient = (remaining + 1e-12) / self.nominal_introduced_mL_per_cycle
        self._require_finite_capacity_arithmetic(maximum_service_cycles_quotient=quotient)
        return max(0, math.floor(quotient))

    @property
    def conservative_service_screen(self) -> ServiceCapacityScreen:
        return self.service_capacity_screen(cycles=self.service_cycles, prime_events=self.service_cycles)

    @property
    def maximum_cartridge_inflow_screen_mL(self) -> float:
        return self.conservative_service_screen.maximum_cartridge_inflow_mL

    @property
    def minimum_retained_waste_screen_mL(self) -> float:
        """Minimum nominal waste that recovery requirements imply must reach cartridge."""
        return self.conservative_service_screen.minimum_recovered_nominal_mL

    @property
    def cartridge_requirement_margin_mL(self) -> float:
        return self.cartridge_retained_capacity_requirement_mL - self.maximum_cartridge_inflow_screen_mL

    @property
    def single_initial_prime_service_screen(self) -> ServiceCapacityScreen:
        return self.service_capacity_screen(cycles=self.service_cycles, prime_events=1)

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
        if self.minimum_retained_waste_screen_mL > self.cartridge_retained_capacity_requirement_mL + 1e-12:
            raise WasteFluidAccountingError("minimum required recovered waste exceeds cartridge requirement")
        if self.cartridge_requirement_margin_mL < -1e-12:
            raise WasteFluidAccountingError("authority cartridge requirement is below conservative cycle inflow screen")

    def manifest(self) -> dict[str, object]:
        self.validate()
        single_prime = self.single_initial_prime_service_screen
        conservative = self.conservative_service_screen
        return {
            "scope": "DIGITAL_CONSERVATION_AND_CAPACITY_SCREEN_ONLY",
            "service_cycles": self.service_cycles,
            "nominal_introduced_mL_per_cycle": self.nominal_introduced_mL_per_cycle,
            "maximum_initial_prime_mL_per_cycle": self.maximum_initial_prime_mL_per_cycle,
            "maximum_liquid_presented_to_recovery_mL_per_cycle": self.maximum_liquid_presented_to_recovery_mL_per_cycle,
            "minimum_recovered_mL_per_cycle": self.minimum_recovered_mL_per_cycle,
            "maximum_unrecovered_nominal_mL_per_cycle": self.maximum_unrecovered_nominal_mL_per_cycle,
            "maximum_classified_nonrecovery_mL_per_cycle": self.maximum_classified_nonrecovery_mL_per_cycle,
            "recovery_ratio_min": self.recovery_ratio_min,
            "recovery_ratio_for_residual_leakage_closure": self.recovery_ratio_for_residual_leakage_closure,
            "recovery_ratio_closure_delta": self.recovery_ratio_closure_delta,
            "residual_free_liquid_max_mL": self.residual_free_liquid_max_mL,
            "external_leakage_max_mL_per_cycle": self.external_leakage_max_mL_per_cycle,
            "minimum_retained_waste_screen_mL": self.minimum_retained_waste_screen_mL,
            "maximum_cartridge_inflow_screen_mL": self.maximum_cartridge_inflow_screen_mL,
            "conservative_occupancy_uncertainty_mL": conservative.occupancy_uncertainty_mL,
            "maximum_prime_events_that_fit_baseline_service": self.maximum_prime_events_that_fit(cycles=self.service_cycles),
            "maximum_service_cycles_with_single_initial_prime": self.maximum_service_cycles_that_fit(prime_events=1),
            "maximum_service_cycles_with_baseline_reprimes": self.maximum_service_cycles_that_fit(prime_events=self.service_cycles),
            "single_initial_prime_service_inflow_mL": single_prime.maximum_cartridge_inflow_mL,
            "single_initial_prime_service_margin_mL": single_prime.requirement_margin_mL,
            "cartridge_retained_capacity_requirement_mL": self.cartridge_retained_capacity_requirement_mL,
            "cartridge_requirement_margin_mL": self.cartridge_requirement_margin_mL,
            "prime_recovery_assumption": "UNSPECIFIED_NO_CREDIT_IN_LOWER_BOUND",
            "physical_validation_eligible": False,
        }


def _authority_service_cycles(authority: Authority) -> int:
    value = authority.number("fluid", "cartridge", "service_cycles_baseline")
    if not math.isfinite(value) or value <= 0.0 or not value.is_integer():
        raise WasteFluidAccountingError("authority service_cycles_baseline must be a positive integer")
    return int(value)


def build_authority_waste_fluid_budget(authority: Authority | None = None) -> WasteFluidBudget:
    authority = authority or load_authority()
    face_water = authority.number("fluid", "clean_cycle", "face_water_mL")
    cleanser = authority.number("fluid", "clean_cycle", "cleanser_mL")
    post_flush = authority.number("fluid", "clean_cycle", "post_flush_water_mL")
    nominal = authority.number("fluid", "clean_cycle", "nominal_introduced_liquid_mL")
    if not math.isclose(face_water + cleanser + post_flush, nominal, rel_tol=0.0, abs_tol=1e-12):
        raise WasteFluidAccountingError("clean-cycle component volumes do not reconcile to nominal introduced liquid")

    budget = WasteFluidBudget(
        service_cycles=_authority_service_cycles(authority),
        nominal_introduced_mL_per_cycle=nominal,
        maximum_initial_prime_mL_per_cycle=authority.number("fluid", "clean_cycle", "maximum_initial_prime_mL"),
        recovery_ratio_min=authority.number("fluid", "waste", "recovery_ratio_min"),
        residual_free_liquid_max_mL=authority.number("fluid", "waste", "residual_free_liquid_max_uL") / 1000.0,
        external_leakage_max_mL_per_cycle=authority.number("safety", "fluid_fault", "max_external_leakage_uL_cycle") / 1000.0,
        cartridge_retained_capacity_requirement_mL=authority.number("fluid", "cartridge", "retained_capacity_min_mL"),
    )
    budget.validate()
    return budget
