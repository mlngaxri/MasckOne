"""Reserve-provenance boundary for cartridge service-capacity sizing."""
from __future__ import annotations

from dataclasses import dataclass

from .waste_fluid_accounting import WasteFluidAccountingError
from .waste_fluid_capacity_reserve import CapacityReservedServiceProfile, CartridgeCapacityReserve
from .waste_fluid_service_sizing import ServiceCapacitySizingInterval, derive_service_capacity_sizing_interval


@dataclass(frozen=True, slots=True)
class CapacityReservedServiceSizing:
    """Capacity sizing that retains the exact unavailable-volume composition.

    The scalar reserve total is insufficient provenance because distinct fill-sensor,
    foam, manufacturing and integration allowances can have the same volume. This
    wrapper prevents downstream sizing consumers from substituting an equal-total
    reserve composition after the service profile has been screened.
    """

    reserve: CartridgeCapacityReserve
    sizing: ServiceCapacitySizingInterval

    def __post_init__(self) -> None:
        if type(self.reserve) is not CartridgeCapacityReserve:
            raise WasteFluidAccountingError("capacity sizing reserve evidence must use exact CartridgeCapacityReserve type")
        if type(self.sizing) is not ServiceCapacitySizingInterval:
            raise WasteFluidAccountingError("capacity sizing evidence must use exact ServiceCapacitySizingInterval type")
        self.reserve.validate()
        self.sizing.__post_init__()
        profile = self.sizing.source
        if profile.source_capacity_reserve_sha256 != self.reserve.evidence_sha256:
            raise WasteFluidAccountingError("capacity sizing reserve composition does not match its source profile")
        if profile.capacity_reserve_mL != self.reserve.total_mL:
            raise WasteFluidAccountingError("capacity sizing reserve total does not match its source profile")


def derive_capacity_reserved_service_sizing(
    evidence: CapacityReservedServiceProfile,
) -> CapacityReservedServiceSizing:
    """Derive sizing without discarding typed reserve provenance."""
    if type(evidence) is not CapacityReservedServiceProfile:
        raise WasteFluidAccountingError("capacity-reserved sizing requires exact CapacityReservedServiceProfile evidence")
    evidence.__post_init__()
    sizing = derive_service_capacity_sizing_interval(evidence.profile)
    return CapacityReservedServiceSizing(reserve=evidence.reserve, sizing=sizing)
