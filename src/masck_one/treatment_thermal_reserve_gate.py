"""Production thermal handoff requiring source-bound cartridge reserve evidence."""
from __future__ import annotations

from .thermal_control import ThermalCommand, ThermalCommandInterlock
from .treatment_recovery_readiness import TreatmentRecoveryReadiness
from .treatment_thermal_handoff import command_thermal_after_treatment
from .waste_fluid_accounting import WasteFluidAccountingError
from .waste_fluid_capacity_reserve import CapacityReservedOverflowGuard


def command_thermal_after_reserved_treatment(
    interlock: ThermalCommandInterlock,
    readiness: TreatmentRecoveryReadiness,
    *,
    warm_requested: bool,
    cool_requested: bool,
) -> ThermalCommand:
    """Arbitrate thermal output only from composition-bound capacity reserve evidence.

    The generic treatment handoff accepts a capacity guard because it is also useful
    during engineering sweeps. This production boundary is stricter: a scalar reserve
    is insufficient because it loses the fill-sensor, foam, manufacturing-tolerance,
    and integration-reserve provenance needed to justify usable cartridge capacity.
    """
    if type(readiness) is not TreatmentRecoveryReadiness:
        raise WasteFluidAccountingError(
            "reserved treatment thermal handoff requires exact TreatmentRecoveryReadiness"
        )
    evidence = readiness.source_capacity_reserve_evidence
    if type(evidence) is not CapacityReservedOverflowGuard:
        raise WasteFluidAccountingError(
            "reserved treatment thermal handoff requires typed CapacityReservedOverflowGuard evidence"
        )
    if readiness.source_capacity_guard is not evidence.guard:
        raise WasteFluidAccountingError(
            "reserved treatment thermal handoff requires readiness bound to the exact reserve guard"
        )
    return command_thermal_after_treatment(
        interlock,
        readiness,
        warm_requested=warm_requested,
        cool_requested=cool_requested,
    )
