"""Deterministic failure-source diagnostic for limiting-event cartridge capacity.

This reducer consumes the independent limiting-event capacity screen and reports
which physical load first makes each recovery-state cartridge demand infeasible.
It introduces no new capacity, recovery, or sink threshold.
"""
from __future__ import annotations

from dataclasses import dataclass

from .waste_fluid_limiting_event_capacity import LimitingEventCapacityScreen


class CapacityFailureDiagnosticError(ValueError):
    """Raised when limiting-event capacity evidence is internally inconsistent."""


@dataclass(frozen=True, slots=True)
class CapacityFailureDiagnostic:
    authority_floor_source: str
    maximum_recovery_source: str
    authority_floor_overflow_mL: float
    maximum_recovery_overflow_mL: float


def _source(*, nominal_failed: bool, reprime_failed: bool, total_failed: bool, label: str) -> str:
    if nominal_failed and reprime_failed:
        raise CapacityFailureDiagnosticError(f"{label} capacity failure sources must be mutually exclusive")
    expected_total = nominal_failed or reprime_failed
    if total_failed != expected_total:
        raise CapacityFailureDiagnosticError(f"{label} capacity failure source does not match total capacity state")
    if nominal_failed:
        return "NOMINAL_LOAD"
    if reprime_failed:
        return "REPRIME_LOAD"
    return "NONE"


def diagnose_limiting_event_capacity_failure(screen: LimitingEventCapacityScreen) -> CapacityFailureDiagnostic:
    """Classify whether nominal or recovered-reprime load causes capacity failure."""
    if not isinstance(screen, LimitingEventCapacityScreen):
        raise TypeError("capacity diagnostic requires LimitingEventCapacityScreen evidence")

    authority_source = _source(
        nominal_failed=screen.authority_floor_nominal_capacity_exceeded,
        reprime_failed=screen.authority_floor_capacity_exceeded_by_reprime,
        total_failed=screen.authority_floor_cartridge_capacity_exceeded,
        label="authority-floor",
    )
    maximum_source = _source(
        nominal_failed=screen.nominal_capacity_exceeded_at_maximum_recovery,
        reprime_failed=screen.capacity_exceeded_by_reprime_at_maximum_recovery,
        total_failed=screen.cartridge_capacity_exceeded_at_maximum_nominal_recovery,
        label="maximum-recovery",
    )

    if screen.authority_floor_cartridge_overflow_mL < 0.0 or screen.cartridge_overflow_at_maximum_nominal_recovery_mL < 0.0:
        raise CapacityFailureDiagnosticError("cartridge overflow cannot be negative")
    if (authority_source == "NONE") != (screen.authority_floor_cartridge_overflow_mL == 0.0):
        raise CapacityFailureDiagnosticError("authority-floor failure source disagrees with overflow")
    if (maximum_source == "NONE") != (screen.cartridge_overflow_at_maximum_nominal_recovery_mL == 0.0):
        raise CapacityFailureDiagnosticError("maximum-recovery failure source disagrees with overflow")

    return CapacityFailureDiagnostic(
        authority_floor_source=authority_source,
        maximum_recovery_source=maximum_source,
        authority_floor_overflow_mL=screen.authority_floor_cartridge_overflow_mL,
        maximum_recovery_overflow_mL=screen.cartridge_overflow_at_maximum_nominal_recovery_mL,
    )
