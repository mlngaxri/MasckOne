"""Typed CLEAN/recovery to thermal-control integration boundary."""
from __future__ import annotations

from .actuation_parameters import ActuationParameterSet
from .actuation_zone_sweep import FourZoneImpedanceSweep
from .thermal_control import ThermalCommand, ThermalCommandInterlock
from .treatment_integrated_evidence import (
    IntegratedTreatmentEvidence,
    validate_integrated_treatment_evidence,
)
from .treatment_recovery_readiness import TreatmentRecoveryReadiness
from .waste_fluid_accounting import WasteFluidAccountingError
from .waste_fluid_overflow_guard import CartridgeOverflowGuard


def command_thermal_after_treatment(interlock: ThermalCommandInterlock, readiness: TreatmentRecoveryReadiness, *, warm_requested: bool, cool_requested: bool) -> ThermalCommand:
    """Arbitrate WARM/COOL only from reserve-aware recovery-capacity evidence."""
    if type(interlock) is not ThermalCommandInterlock:
        raise WasteFluidAccountingError("treatment thermal handoff requires exact ThermalCommandInterlock")
    if type(readiness) is not TreatmentRecoveryReadiness:
        raise WasteFluidAccountingError("treatment thermal handoff requires exact TreatmentRecoveryReadiness")
    # Revalidate at the subsystem boundary rather than trusting construction-time
    # validation. Frozen dataclasses can still be altered by low-level callers, and
    # thermal enable must never consume a stale or forged recovery decision.
    readiness.__post_init__()
    if type(readiness.source_capacity_guard) is not CartridgeOverflowGuard:
        raise WasteFluidAccountingError("treatment thermal handoff requires reserve-aware CartridgeOverflowGuard evidence")
    return interlock.command(warm_requested=warm_requested, cool_requested=cool_requested, recovery_complete=readiness.post_recovery_handoff_permitted)


def command_thermal_from_integrated_treatment_evidence(
    interlock: ThermalCommandInterlock,
    sweep: FourZoneImpedanceSweep,
    parameters: ActuationParameterSet,
    evidence: IntegratedTreatmentEvidence,
    *,
    warm_requested: bool,
    cool_requested: bool,
) -> ThermalCommand:
    """Arbitrate thermal output only after validating the complete treatment evidence tree.

    This is the treatment-facing handoff when measured massage/thermal coexistence
    evidence is available. It prevents a caller from validating massage/thermal
    evidence and then dropping that provenance before the thermal command boundary.
    No new thermal or recovery acceptance threshold is introduced here.
    """
    validate_integrated_treatment_evidence(sweep, parameters, evidence)
    return command_thermal_after_treatment(
        interlock,
        evidence.recovery,
        warm_requested=warm_requested,
        cool_requested=cool_requested,
    )
