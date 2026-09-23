"""Typed CLEAN/recovery to thermal-control integration boundary."""
from __future__ import annotations
from .thermal_control import ThermalCommand, ThermalCommandInterlock
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
