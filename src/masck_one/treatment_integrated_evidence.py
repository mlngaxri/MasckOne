"""Atomic evidence boundary across CLEAN/recovery, massage, and thermal coexistence."""
from __future__ import annotations

from dataclasses import dataclass

from .actuation_parameters import ActuationParameterError, ActuationParameterSet
from .actuation_zone_sweep import FourZoneImpedanceSweep
from .treatment_massage_thermal_evidence import (
    TreatmentMassageThermalEvidence,
    validate_treatment_massage_thermal_evidence,
)
from .treatment_recovery_readiness import TreatmentRecoveryReadiness
from .waste_fluid_accounting import WasteFluidAccountingError
from .waste_fluid_overflow_guard import CartridgeOverflowGuard


@dataclass(frozen=True, slots=True)
class IntegratedTreatmentEvidence:
    """One fail-closed treatment view spanning recovery and measured actuation evidence."""

    recovery: TreatmentRecoveryReadiness
    massage_thermal: TreatmentMassageThermalEvidence
    source_sweep_sha256: str


def build_integrated_treatment_evidence(
    recovery: TreatmentRecoveryReadiness,
    sweep: FourZoneImpedanceSweep,
    parameters: ActuationParameterSet,
    massage_thermal: TreatmentMassageThermalEvidence,
) -> IntegratedTreatmentEvidence:
    """Bind independently qualified treatment evidence without inventing new physics."""
    validate_integrated_treatment_inputs(recovery, sweep, parameters, massage_thermal)
    return IntegratedTreatmentEvidence(
        recovery=recovery,
        massage_thermal=massage_thermal,
        source_sweep_sha256=sweep.sweep_sha256,
    )


def validate_integrated_treatment_inputs(
    recovery: TreatmentRecoveryReadiness,
    sweep: FourZoneImpedanceSweep,
    parameters: ActuationParameterSet,
    massage_thermal: TreatmentMassageThermalEvidence,
) -> None:
    """Revalidate both subsystem evidence trees at their canonical boundaries."""
    if type(recovery) is not TreatmentRecoveryReadiness:
        raise WasteFluidAccountingError(
            "integrated treatment evidence requires exact TreatmentRecoveryReadiness"
        )
    recovery.__post_init__()
    if type(recovery.source_capacity_guard) is not CartridgeOverflowGuard:
        raise WasteFluidAccountingError(
            "integrated treatment evidence requires reserve-aware CartridgeOverflowGuard evidence"
        )
    validate_treatment_massage_thermal_evidence(sweep, parameters, massage_thermal)


def validate_integrated_treatment_evidence(
    sweep: FourZoneImpedanceSweep,
    parameters: ActuationParameterSet,
    evidence: IntegratedTreatmentEvidence,
) -> IntegratedTreatmentEvidence:
    """Reject stale, forged, or independently substituted treatment evidence."""
    if type(evidence) is not IntegratedTreatmentEvidence:
        raise TypeError("evidence must be exact IntegratedTreatmentEvidence")
    validate_integrated_treatment_inputs(
        evidence.recovery, sweep, parameters, evidence.massage_thermal
    )
    if evidence.source_sweep_sha256 != sweep.sweep_sha256:
        raise ActuationParameterError(
            "integrated treatment evidence does not match current four-zone sweep"
        )
    return evidence
