"""Authority binding for capacity-reserved cartridge overflow evidence."""
from __future__ import annotations

from .waste_fluid_accounting import WasteFluidAccountingError, WasteFluidBudget
from .waste_fluid_capacity_reserve import CapacityReservedOverflowGuard
from .waste_fluid_overflow_authority import validate_overflow_guard_authority


def validate_capacity_reserved_overflow_authority(
    budget: WasteFluidBudget,
    evidence: CapacityReservedOverflowGuard,
) -> None:
    """Require reserve provenance and cycle routing to share one fluid authority."""
    if type(budget) is not WasteFluidBudget:
        raise WasteFluidAccountingError(
            "capacity-reserved overflow authority requires exact WasteFluidBudget"
        )
    if type(evidence) is not CapacityReservedOverflowGuard:
        raise WasteFluidAccountingError(
            "capacity-reserved overflow authority requires exact CapacityReservedOverflowGuard"
        )
    evidence.__post_init__()
    validate_overflow_guard_authority(budget, evidence.guard)
