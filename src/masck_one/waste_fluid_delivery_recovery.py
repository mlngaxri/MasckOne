"""Authority-bound delivery composition at the waste/recovery interface.

The waste model historically retained only the 4.6 mL nominal cycle total. This
module keeps the water, cleanser and post-flush contributions attached to that
same total so delivery changes cannot silently enter recovery accounting as an
unchanged scalar. These are digital conservation checks, not physical recovery
or mixing validation.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

from .authority import Authority, load_authority
from .waste_fluid_accounting import (
    WasteFluidAccountingError,
    WasteFluidBudget,
    build_authority_waste_fluid_budget,
)

_TOL = 1e-12


@dataclass(frozen=True, slots=True)
class CleanCycleDeliveryRecoveryLedger:
    source_budget: WasteFluidBudget
    cycles: int
    face_water_mL_per_cycle: float
    cleanser_mL_per_cycle: float
    post_flush_water_mL_per_cycle: float
    nominal_mL_per_cycle: float
    service_face_water_mL: float
    service_cleanser_mL: float
    service_post_flush_water_mL: float
    service_nominal_mL: float
    minimum_service_recovery_mL: float
    maximum_service_nonrecovery_mL: float

    def __post_init__(self) -> None:
        if type(self.source_budget) is not WasteFluidBudget:
            raise WasteFluidAccountingError("delivery/recovery ledger requires exact WasteFluidBudget source")
        self.source_budget.validate()
        if type(self.cycles) is not int or not 1 <= self.cycles <= self.source_budget.service_cycles:
            raise WasteFluidAccountingError("delivery/recovery cycles must lie within configured service life")
        numeric = (
            self.face_water_mL_per_cycle,
            self.cleanser_mL_per_cycle,
            self.post_flush_water_mL_per_cycle,
            self.nominal_mL_per_cycle,
            self.service_face_water_mL,
            self.service_cleanser_mL,
            self.service_post_flush_water_mL,
            self.service_nominal_mL,
            self.minimum_service_recovery_mL,
            self.maximum_service_nonrecovery_mL,
        )
        if any(type(v) not in (int, float) or not math.isfinite(float(v)) or v < 0.0 for v in numeric):
            raise WasteFluidAccountingError("delivery/recovery ledger values must be finite and nonnegative")

        component_cycle = self.face_water_mL_per_cycle + self.cleanser_mL_per_cycle + self.post_flush_water_mL_per_cycle
        expected_nominal = self.source_budget.nominal_introduced_mL_per_cycle
        expected_service = self.cycles * expected_nominal
        expected_recovery = expected_service * self.source_budget.recovery_ratio_min
        expected_nonrecovery = expected_service - expected_recovery
        checks = (
            (component_cycle, self.nominal_mL_per_cycle, "cycle component conservation"),
            (self.nominal_mL_per_cycle, expected_nominal, "waste-budget nominal binding"),
            (self.service_face_water_mL, self.cycles * self.face_water_mL_per_cycle, "service face-water total"),
            (self.service_cleanser_mL, self.cycles * self.cleanser_mL_per_cycle, "service cleanser total"),
            (self.service_post_flush_water_mL, self.cycles * self.post_flush_water_mL_per_cycle, "service post-flush total"),
            (self.service_nominal_mL, expected_service, "service nominal total"),
            (self.minimum_service_recovery_mL, expected_recovery, "service recovery floor"),
            (self.maximum_service_nonrecovery_mL, expected_nonrecovery, "service nonrecovery envelope"),
            (self.minimum_service_recovery_mL + self.maximum_service_nonrecovery_mL, self.service_nominal_mL, "recovery conservation"),
            (self.service_face_water_mL + self.service_cleanser_mL + self.service_post_flush_water_mL, self.service_nominal_mL, "service component conservation"),
        )
        for actual, expected, label in checks:
            if not math.isclose(actual, expected, rel_tol=0.0, abs_tol=_TOL):
                raise WasteFluidAccountingError(f"delivery/recovery {label} does not reconcile")

    @property
    def cleanser_fraction(self) -> float:
        return self.cleanser_mL_per_cycle / self.nominal_mL_per_cycle

    @property
    def water_fraction(self) -> float:
        return (self.face_water_mL_per_cycle + self.post_flush_water_mL_per_cycle) / self.nominal_mL_per_cycle


def build_authority_delivery_recovery_ledger(
    *,
    cycles: int | None = None,
    budget: WasteFluidBudget | None = None,
    authority: Authority | None = None,
) -> CleanCycleDeliveryRecoveryLedger:
    """Bind clean-cycle component volumes to the exact recovery budget in use."""
    authority = authority or load_authority()
    budget = budget or build_authority_waste_fluid_budget(authority)
    if type(budget) is not WasteFluidBudget:
        raise WasteFluidAccountingError("delivery/recovery ledger requires exact WasteFluidBudget source")
    budget.validate()
    cycles = budget.service_cycles if cycles is None else cycles
    face_water = authority.number("fluid", "clean_cycle", "face_water_mL")
    cleanser = authority.number("fluid", "clean_cycle", "cleanser_mL")
    post_flush = authority.number("fluid", "clean_cycle", "post_flush_water_mL")
    nominal = authority.number("fluid", "clean_cycle", "nominal_introduced_liquid_mL")
    component_total = face_water + cleanser + post_flush
    if not math.isclose(component_total, nominal, rel_tol=0.0, abs_tol=_TOL):
        raise WasteFluidAccountingError("authority clean-cycle components do not conserve nominal introduced liquid")
    if not math.isclose(nominal, budget.nominal_introduced_mL_per_cycle, rel_tol=0.0, abs_tol=_TOL):
        raise WasteFluidAccountingError("delivery authority nominal volume disagrees with recovery budget")
    service_face = cycles * face_water
    service_cleanser = cycles * cleanser
    service_post = cycles * post_flush
    service_nominal = cycles * nominal
    minimum_recovery = service_nominal * budget.recovery_ratio_min
    return CleanCycleDeliveryRecoveryLedger(
        source_budget=budget,
        cycles=cycles,
        face_water_mL_per_cycle=face_water,
        cleanser_mL_per_cycle=cleanser,
        post_flush_water_mL_per_cycle=post_flush,
        nominal_mL_per_cycle=nominal,
        service_face_water_mL=service_face,
        service_cleanser_mL=service_cleanser,
        service_post_flush_water_mL=service_post,
        service_nominal_mL=service_nominal,
        minimum_service_recovery_mL=minimum_recovery,
        maximum_service_nonrecovery_mL=service_nominal - minimum_recovery,
    )
