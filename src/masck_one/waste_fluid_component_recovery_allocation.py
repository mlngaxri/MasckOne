"""Joint conservation verifier for component-level recovery allocations.

This module checks candidate component recovery volumes against the exact clean-cycle
ledger. It does not claim that any candidate allocation has been physically measured.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

from .waste_fluid_accounting import WasteFluidAccountingError
from .waste_fluid_delivery_recovery import (
    CleanCycleDeliveryRecoveryLedger,
    build_authority_delivery_recovery_ledger,
)

_TOL = 1e-12


@dataclass(frozen=True, slots=True)
class ComponentRecoveryAllocation:
    source_ledger: CleanCycleDeliveryRecoveryLedger
    recovered_face_water_mL: float
    recovered_cleanser_mL: float
    recovered_post_flush_water_mL: float
    total_recovered_mL: float
    total_nonrecovered_mL: float
    recovery_ratio: float
    meets_recovery_floor: bool

    def __post_init__(self) -> None:
        if type(self.source_ledger) is not CleanCycleDeliveryRecoveryLedger:
            raise WasteFluidAccountingError("component recovery allocation requires exact delivery ledger source")
        self.source_ledger.__post_init__()
        recovered = (
            self.recovered_face_water_mL,
            self.recovered_cleanser_mL,
            self.recovered_post_flush_water_mL,
        )
        introduced = (
            self.source_ledger.service_face_water_mL,
            self.source_ledger.service_cleanser_mL,
            self.source_ledger.service_post_flush_water_mL,
        )
        numeric = recovered + (self.total_recovered_mL, self.total_nonrecovered_mL, self.recovery_ratio)
        if any(type(v) not in (int, float) or not math.isfinite(float(v)) or v < 0.0 for v in numeric):
            raise WasteFluidAccountingError("component recovery allocation values must be finite and nonnegative")
        if type(self.meets_recovery_floor) is not bool:
            raise WasteFluidAccountingError("component recovery allocation decision must be boolean")
        for value, ceiling in zip(recovered, introduced):
            if value > ceiling + _TOL:
                raise WasteFluidAccountingError("component recovered volume cannot exceed introduced volume")

        expected_total = sum(recovered)
        expected_nonrecovered = self.source_ledger.service_nominal_mL - expected_total
        if expected_nonrecovered < -_TOL:
            raise WasteFluidAccountingError("aggregate recovered volume cannot exceed introduced volume")
        expected_nonrecovered = max(0.0, expected_nonrecovered)
        expected_ratio = expected_total / self.source_ledger.service_nominal_mL
        expected_decision = expected_total + _TOL >= self.source_ledger.minimum_service_recovery_mL
        checks = (
            (self.total_recovered_mL, expected_total, "recovered total"),
            (self.total_nonrecovered_mL, expected_nonrecovered, "nonrecovered total"),
            (self.recovery_ratio, expected_ratio, "recovery ratio"),
        )
        for actual, expected, label in checks:
            if not math.isclose(actual, expected, rel_tol=0.0, abs_tol=_TOL):
                raise WasteFluidAccountingError(f"component recovery allocation {label} does not reconcile")
        if self.meets_recovery_floor is not expected_decision:
            raise WasteFluidAccountingError("component recovery allocation decision does not reconcile")
        if self.meets_recovery_floor and self.total_nonrecovered_mL > self.source_ledger.maximum_service_nonrecovery_mL + _TOL:
            raise WasteFluidAccountingError("passing allocation exceeds aggregate nonrecovery envelope")


def evaluate_component_recovery_allocation(
    *,
    recovered_face_water_mL: float,
    recovered_cleanser_mL: float,
    recovered_post_flush_water_mL: float,
    ledger: CleanCycleDeliveryRecoveryLedger | None = None,
) -> ComponentRecoveryAllocation:
    """Evaluate a candidate allocation without treating it as physical evidence."""
    ledger = ledger or build_authority_delivery_recovery_ledger()
    if type(ledger) is not CleanCycleDeliveryRecoveryLedger:
        raise WasteFluidAccountingError("component recovery allocation requires exact delivery ledger source")
    ledger.__post_init__()
    recovered = (recovered_face_water_mL, recovered_cleanser_mL, recovered_post_flush_water_mL)
    if any(type(v) not in (int, float) or not math.isfinite(float(v)) or v < 0.0 for v in recovered):
        raise WasteFluidAccountingError("candidate component recovery volumes must be finite and nonnegative")
    introduced = (ledger.service_face_water_mL, ledger.service_cleanser_mL, ledger.service_post_flush_water_mL)
    if any(value > ceiling + _TOL for value, ceiling in zip(recovered, introduced)):
        raise WasteFluidAccountingError("candidate component recovery cannot exceed introduced component volume")
    total = sum(recovered)
    if total > ledger.service_nominal_mL + _TOL:
        raise WasteFluidAccountingError("candidate aggregate recovery cannot exceed introduced volume")
    nonrecovered = max(0.0, ledger.service_nominal_mL - total)
    ratio = total / ledger.service_nominal_mL
    result = ComponentRecoveryAllocation(
        source_ledger=ledger,
        recovered_face_water_mL=recovered_face_water_mL,
        recovered_cleanser_mL=recovered_cleanser_mL,
        recovered_post_flush_water_mL=recovered_post_flush_water_mL,
        total_recovered_mL=total,
        total_nonrecovered_mL=nonrecovered,
        recovery_ratio=ratio,
        meets_recovery_floor=total + _TOL >= ledger.minimum_service_recovery_mL,
    )
    result.__post_init__()
    return result
