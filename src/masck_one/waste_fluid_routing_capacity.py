"""Route-qualified cartridge capacity floor for completed service profiles.

This bridge prevents an explicit prime-recovery contract from disappearing at the
cartridge sizing boundary. It is a digital conservation check only, not evidence
of physical prime recovery or retained volume.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from .waste_fluid_accounting import WasteFluidAccountingError
from .waste_fluid_closure import ServiceRoutingClosure
from .waste_fluid_profile import ServiceFluidProfile


@dataclass(frozen=True, slots=True)
class RoutingQualifiedCapacityFloor:
    nominal_recovery_floor_mL: float
    prime_recovery_floor_mL: float
    combined_recovery_floor_mL: float
    usable_capacity_mL: float
    headroom_mL: float
    fit: bool
    routing_contract_complete: bool
    integration_ready: bool


def _require_finite(label: str, value: float) -> float:
    """Reject corrupted or overflowed scalar evidence before capacity decisions."""
    if type(value) not in (int, float) or not math.isfinite(value):
        raise WasteFluidAccountingError(f"{label} must be finite")
    return float(value)


def derive_routing_qualified_capacity_floor(
    profile: ServiceFluidProfile,
    routing: ServiceRoutingClosure,
) -> RoutingQualifiedCapacityFloor:
    """Bind completed service routing evidence into the cartridge capacity floor.

    The function intentionally accepts only a completed profile. Otherwise a routing
    closure for observed cycles could be mistaken for a service-end prime recovery
    requirement. The routing object must describe the exact same cycle and prime
    counts as the profile. The resulting floor adds explicitly contracted prime
    recovery to the nominal recovery floor already carried by the service model.

    ``fit`` answers only whether the explicitly routed recovery floor fits the usable
    cartridge capacity. ``integration_ready`` additionally requires every service
    liquid destination to be closed by the routing contract. This distinction prevents
    unresolved prime or shared-sink liquid from being hidden behind a passing capacity
    check.
    """
    if type(profile) is not ServiceFluidProfile:
        raise WasteFluidAccountingError("routing-qualified capacity requires exact ServiceFluidProfile evidence")
    if type(routing) is not ServiceRoutingClosure:
        raise WasteFluidAccountingError("routing-qualified capacity requires exact ServiceRoutingClosure evidence")
    if not profile.cycles:
        raise WasteFluidAccountingError("routing-qualified capacity requires cycle evidence")
    if len(profile.cycles) != profile.target_cycles:
        raise WasteFluidAccountingError("routing-qualified capacity requires a completed service profile")

    final = profile.final
    if routing.cycles != profile.target_cycles:
        raise WasteFluidAccountingError("routing closure cycle count does not match service profile")
    if routing.prime_events != final.cumulative_prime_events:
        raise WasteFluidAccountingError("routing closure prime count does not match service profile")

    nominal_floor = _require_finite("profile nominal recovery floor", final.minimum_recovered_nominal_mL)
    routed_nominal_floor = _require_finite(
        "routing nominal recovery floor", routing.minimum_nominal_liquid_routed_to_cartridge_mL
    )
    if not math.isclose(routed_nominal_floor, nominal_floor, rel_tol=0.0, abs_tol=1e-12):
        raise WasteFluidAccountingError("routing and profile nominal recovery floors do not reconcile")

    prime_floor = _require_finite(
        "routing prime recovery floor", routing.minimum_prime_liquid_routed_to_cartridge_mL
    )
    maximum_inflow = _require_finite(
        "profile maximum cartridge inflow", final.maximum_cartridge_inflow_mL
    )
    usable_capacity = _require_finite("profile usable capacity", profile.usable_capacity_mL)

    combined_floor = nominal_floor + prime_floor
    _require_finite("combined routing recovery floor", combined_floor)
    if combined_floor > maximum_inflow + 1e-12:
        raise WasteFluidAccountingError("contracted recovery floor exceeds liquid presented to cartridge screen")

    headroom = usable_capacity - combined_floor
    _require_finite("routing-qualified cartridge headroom", headroom)
    fit = headroom >= -1e-12
    routing_complete = routing.routing_contract_complete
    if type(routing_complete) is not bool:
        raise WasteFluidAccountingError("routing contract disposition must be boolean")
    return RoutingQualifiedCapacityFloor(
        nominal_recovery_floor_mL=nominal_floor,
        prime_recovery_floor_mL=prime_floor,
        combined_recovery_floor_mL=combined_floor,
        usable_capacity_mL=usable_capacity,
        headroom_mL=headroom,
        fit=fit,
        routing_contract_complete=routing_complete,
        integration_ready=fit and routing_complete,
    )
