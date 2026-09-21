"""Capacity-sizing interval derived from cycle-resolved service accounting."""
from __future__ import annotations

from dataclasses import dataclass

from .waste_fluid_accounting import WasteFluidAccountingError
from .waste_fluid_profile import ServiceFluidProfile


@dataclass(frozen=True, slots=True)
class ServiceCapacitySizingInterval:
    """Required cartridge capacity bounds for one screened service profile.

    The contractual lower bound is the largest mandatory-recovery projection in
    the profile. The conservative upper bound is the largest projected inflow,
    including the caller-selected future-prime contingency. Usable-capacity bounds
    describe liquid-holding volume after explicit reserves. Retained-capacity bounds
    add those unavailable reserves back so packaging can size the controlled
    cartridge requirement without accidentally treating reserve volume as free.
    These are digital sizing bounds, not physical retained-volume measurements.
    """

    contractual_required_usable_capacity_mL: float
    conservative_required_usable_capacity_mL: float
    unresolved_capacity_interval_mL: float
    capacity_reserve_mL: float
    usable_capacity_mL: float
    retained_capacity_requirement_mL: float
    contractual_required_retained_capacity_mL: float
    conservative_required_retained_capacity_mL: float
    contractual_headroom_mL: float
    conservative_headroom_mL: float
    contractual_fit: bool
    conservative_fit: bool


def derive_service_capacity_sizing_interval(
    profile: ServiceFluidProfile,
) -> ServiceCapacitySizingInterval:
    """Derive auditable usable and retained-capacity bounds from an exact profile."""
    if type(profile) is not ServiceFluidProfile:
        raise WasteFluidAccountingError(
            "service capacity sizing requires exact ServiceFluidProfile evidence"
        )
    if not profile.cycles:
        raise WasteFluidAccountingError("service capacity sizing requires cycle evidence")

    contractual = max(
        state.minimum_projected_service_end_recovered_mL for state in profile.cycles
    )
    conservative = max(
        state.minimum_projected_service_end_inflow_mL for state in profile.cycles
    )
    if conservative + 1e-12 < contractual:
        raise WasteFluidAccountingError(
            "conservative service capacity bound cannot be below contractual bound"
        )

    unresolved = max(0.0, conservative - contractual)
    reserve = profile.capacity_reserve_mL
    retained_requirement = profile.usable_capacity_mL + reserve
    contractual_retained = contractual + reserve
    conservative_retained = conservative + reserve
    contractual_headroom = retained_requirement - contractual_retained
    conservative_headroom = retained_requirement - conservative_retained

    # The retained-capacity and usable-capacity views must be exactly the same
    # physical fit decision. This invariant prevents reserve volume from being
    # counted once in the profile and then silently credited again during sizing.
    usable_contractual_headroom = profile.usable_capacity_mL - contractual
    usable_conservative_headroom = profile.usable_capacity_mL - conservative
    if abs(contractual_headroom - usable_contractual_headroom) > 1e-12:
        raise WasteFluidAccountingError("contractual reserve accounting does not conserve capacity")
    if abs(conservative_headroom - usable_conservative_headroom) > 1e-12:
        raise WasteFluidAccountingError("conservative reserve accounting does not conserve capacity")

    return ServiceCapacitySizingInterval(
        contractual_required_usable_capacity_mL=contractual,
        conservative_required_usable_capacity_mL=conservative,
        unresolved_capacity_interval_mL=unresolved,
        capacity_reserve_mL=reserve,
        usable_capacity_mL=profile.usable_capacity_mL,
        retained_capacity_requirement_mL=retained_requirement,
        contractual_required_retained_capacity_mL=contractual_retained,
        conservative_required_retained_capacity_mL=conservative_retained,
        contractual_headroom_mL=contractual_headroom,
        conservative_headroom_mL=conservative_headroom,
        contractual_fit=contractual_headroom >= -1e-12,
        conservative_fit=conservative_headroom >= -1e-12,
    )
