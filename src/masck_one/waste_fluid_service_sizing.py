"""Capacity-sizing interval derived from cycle-resolved service accounting."""
from __future__ import annotations

from dataclasses import dataclass
import math

from .waste_fluid_accounting import WasteFluidAccountingError
from .waste_fluid_profile import ServiceFluidProfile

_TOL = 1e-12


def _finite_sizing_value(value: float, label: str) -> float:
    """Return a finite sizing value or fail before it can drive a fit decision."""
    if type(value) not in (int, float) or not math.isfinite(float(value)):
        raise WasteFluidAccountingError(f"{label} must be finite")
    return float(value)


def _validate_projected_bounds(profile: ServiceFluidProfile, contractual: float, conservative: float) -> None:
    """Reject projected service bounds that contradict already accumulated liquid.

    A service-end projection cannot be below liquid already assigned to the same
    sink bound. This check is intentionally independent of the projection model so
    stale or corrupted future-cycle evidence cannot make cartridge sizing look
    artificially smaller than the current cycle-resolved state.
    """
    current_contractual_floor = _finite_sizing_value(
        max(state.minimum_recovered_nominal_mL for state in profile.cycles),
        "current recovered-volume floor",
    )
    current_conservative_floor = _finite_sizing_value(
        max(state.maximum_cartridge_inflow_mL for state in profile.cycles),
        "current cartridge-inflow floor",
    )
    if contractual + _TOL < current_contractual_floor:
        raise WasteFluidAccountingError("projected contractual capacity bound is below already recovered volume")
    if conservative + _TOL < current_conservative_floor:
        raise WasteFluidAccountingError("projected conservative capacity bound is below already accumulated cartridge inflow")
    if conservative + _TOL < contractual:
        raise WasteFluidAccountingError("conservative service capacity bound cannot be below contractual bound")


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
        self.source.__post_init__()
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
        contractual = _finite_sizing_value(max(state.minimum_projected_service_end_recovered_mL for state in self.source.cycles), "contractual service capacity bound")
        conservative = _finite_sizing_value(max(state.minimum_projected_service_end_inflow_mL for state in self.source.cycles), "conservative service capacity bound")
        _validate_projected_bounds(self.source, contractual, conservative)
        reserve = _finite_sizing_value(self.source.capacity_reserve_mL, "capacity reserve")
        usable = _finite_sizing_value(self.source.usable_capacity_mL, "usable capacity")
        derived = (
            max(0.0, conservative - contractual),
            usable + reserve,
            contractual + reserve,
            conservative + reserve,
            usable - contractual,
            usable - conservative,
        )
        if any(not math.isfinite(value) for value in derived):
            raise WasteFluidAccountingError("derived service capacity sizing arithmetic must remain finite")
        expected = (
            contractual,
            conservative,
            derived[0],
            reserve,
            usable,
            derived[1],
            derived[2],
            derived[3],
            derived[4],
            derived[5],
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
    profile.__post_init__()
    if not profile.cycles:
        raise WasteFluidAccountingError("service capacity sizing requires cycle evidence")

    contractual = _finite_sizing_value(max(state.minimum_projected_service_end_recovered_mL for state in profile.cycles), "contractual service capacity bound")
    conservative = _finite_sizing_value(max(state.minimum_projected_service_end_inflow_mL for state in profile.cycles), "conservative service capacity bound")
    _validate_projected_bounds(profile, contractual, conservative)
    reserve = _finite_sizing_value(profile.capacity_reserve_mL, "capacity reserve")
    usable = _finite_sizing_value(profile.usable_capacity_mL, "usable capacity")

    unresolved = max(0.0, conservative - contractual)
    retained_requirement = usable + reserve
    contractual_retained = contractual + reserve
    conservative_retained = conservative + reserve
    contractual_headroom = retained_requirement - contractual_retained
    conservative_headroom = retained_requirement - conservative_retained
    derived = (
        unresolved,
        retained_requirement,
        contractual_retained,
        conservative_retained,
        contractual_headroom,
        conservative_headroom,
    )
    if any(not math.isfinite(value) for value in derived):
        raise WasteFluidAccountingError("derived service capacity sizing arithmetic must remain finite")

    usable_contractual_headroom = usable - contractual
    usable_conservative_headroom = usable - conservative
    if not math.isfinite(usable_contractual_headroom) or not math.isfinite(usable_conservative_headroom):
        raise WasteFluidAccountingError("usable service capacity headroom must remain finite")
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
        usable_capacity_mL=usable,
        retained_capacity_requirement_mL=retained_requirement,
        contractual_required_retained_capacity_mL=contractual_retained,
        conservative_required_retained_capacity_mL=conservative_retained,
        contractual_headroom_mL=contractual_headroom,
        conservative_headroom_mL=conservative_headroom,
        contractual_fit=contractual_headroom >= -_TOL,
        conservative_fit=conservative_headroom >= -_TOL,
    )
