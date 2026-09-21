"""Capacity-sizing interval derived from cycle-resolved service accounting."""
from __future__ import annotations

from dataclasses import dataclass
import math

from .waste_fluid_accounting import WasteFluidAccountingError
from .waste_fluid_profile import ServiceFluidProfile

_TOL = 1e-12


@dataclass(frozen=True, slots=True)
class ServiceCapacitySizingInterval:
    """Required cartridge capacity bounds for one screened service profile.

    These are digital sizing bounds, not physical retained-volume measurements.
    The exact source profile is retained so downstream integration cannot substitute
    caller-authored capacity numbers for cycle-resolved routing evidence.
    """

    source: ServiceFluidProfile
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

    def __post_init__(self) -> None:
        if type(self.source) is not ServiceFluidProfile or not self.source.cycles:
            raise WasteFluidAccountingError("service capacity sizing requires exact cycle-resolved profile evidence")
        numeric = (
            self.contractual_required_usable_capacity_mL,
            self.conservative_required_usable_capacity_mL,
            self.unresolved_capacity_interval_mL,
            self.capacity_reserve_mL,
            self.usable_capacity_mL,
            self.retained_capacity_requirement_mL,
            self.contractual_required_retained_capacity_mL,
            self.conservative_required_retained_capacity_mL,
            self.contractual_headroom_mL,
            self.conservative_headroom_mL,
        )
        if any(type(value) not in (int, float) or not math.isfinite(float(value)) for value in numeric):
            raise WasteFluidAccountingError("service capacity sizing evidence must be finite numeric data")
        contractual = max(state.minimum_projected_service_end_recovered_mL for state in self.source.cycles)
        conservative = max(state.minimum_projected_service_end_inflow_mL for state in self.source.cycles)
        reserve = self.source.capacity_reserve_mL
        usable = self.source.usable_capacity_mL
        expected = (
            contractual,
            conservative,
            max(0.0, conservative - contractual),
            reserve,
            usable,
            usable + reserve,
            contractual + reserve,
            conservative + reserve,
            usable - contractual,
            usable - conservative,
        )
        if any(not math.isclose(float(actual), float(want), rel_tol=0.0, abs_tol=_TOL)
               for actual, want in zip(numeric, expected)):
            raise WasteFluidAccountingError("service capacity sizing evidence is stale or inconsistent with its source profile")
        if type(self.contractual_fit) is not bool or type(self.conservative_fit) is not bool:
            raise WasteFluidAccountingError("service capacity sizing fit evidence must be boolean")
        if self.contractual_fit != (expected[8] >= -_TOL):
            raise WasteFluidAccountingError("contractual capacity fit is inconsistent with source profile")
        if self.conservative_fit != (expected[9] >= -_TOL):
            raise WasteFluidAccountingError("conservative capacity fit is inconsistent with source profile")


def derive_service_capacity_sizing_interval(profile: ServiceFluidProfile) -> ServiceCapacitySizingInterval:
    """Derive auditable usable and retained-capacity bounds from an exact profile."""
    if type(profile) is not ServiceFluidProfile:
        raise WasteFluidAccountingError("service capacity sizing requires exact ServiceFluidProfile evidence")
    if not profile.cycles:
        raise WasteFluidAccountingError("service capacity sizing requires cycle evidence")

    contractual = max(state.minimum_projected_service_end_recovered_mL for state in profile.cycles)
    conservative = max(state.minimum_projected_service_end_inflow_mL for state in profile.cycles)
    if conservative + _TOL < contractual:
        raise WasteFluidAccountingError("conservative service capacity bound cannot be below contractual bound")

    unresolved = max(0.0, conservative - contractual)
    reserve = profile.capacity_reserve_mL
    retained_requirement = profile.usable_capacity_mL + reserve
    contractual_retained = contractual + reserve
    conservative_retained = conservative + reserve
    contractual_headroom = retained_requirement - contractual_retained
    conservative_headroom = retained_requirement - conservative_retained

    usable_contractual_headroom = profile.usable_capacity_mL - contractual
    usable_conservative_headroom = profile.usable_capacity_mL - conservative
    if abs(contractual_headroom - usable_contractual_headroom) > _TOL:
        raise WasteFluidAccountingError("contractual reserve accounting does not conserve capacity")
    if abs(conservative_headroom - usable_conservative_headroom) > _TOL:
        raise WasteFluidAccountingError("conservative reserve accounting does not conserve capacity")

    return ServiceCapacitySizingInterval(
        source=profile,
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
        contractual_fit=contractual_headroom >= -_TOL,
        conservative_fit=conservative_headroom >= -_TOL,
    )
