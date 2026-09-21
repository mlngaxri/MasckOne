"""Cycle-resolved cartridge overflow trajectory derived from screened routing evidence."""
from __future__ import annotations

import math
from dataclasses import dataclass

from .waste_fluid_accounting import WasteFluidAccountingError
from .waste_fluid_overflow_guard import CartridgeOverflowGuard

_TOL = 1e-12


@dataclass(frozen=True)
class CartridgeOverflowState:
    cycle: int
    contractual_overflow_mL: float
    conservative_overflow_mL: float
    contractual_increment_mL: float
    conservative_increment_mL: float

    def __post_init__(self) -> None:
        if type(self.cycle) is not int or self.cycle < 1:
            raise WasteFluidAccountingError("overflow trajectory cycle must be a positive integer")
        for name in (
            "contractual_overflow_mL", "conservative_overflow_mL",
            "contractual_increment_mL", "conservative_increment_mL",
        ):
            value = getattr(self, name)
            if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)) or value < -_TOL:
                raise WasteFluidAccountingError(f"{name} must be finite and nonnegative")
        if self.contractual_overflow_mL > self.conservative_overflow_mL + _TOL:
            raise WasteFluidAccountingError("contractual overflow cannot exceed conservative overflow")
        if self.contractual_increment_mL > self.conservative_increment_mL + _TOL:
            raise WasteFluidAccountingError("contractual overflow increment cannot exceed conservative increment")


@dataclass(frozen=True)
class CartridgeOverflowTrajectory:
    guard: CartridgeOverflowGuard
    states: tuple[CartridgeOverflowState, ...]

    def __post_init__(self) -> None:
        if type(self.guard) is not CartridgeOverflowGuard:
            raise WasteFluidAccountingError("overflow trajectory requires exact CartridgeOverflowGuard evidence")
        if len(self.states) != len(self.guard.routing.cycles):
            raise WasteFluidAccountingError("overflow trajectory must cover every routed cycle")

        previous_contractual = 0.0
        previous_conservative = 0.0
        for routed, state in zip(self.guard.routing.cycles, self.states):
            if type(state) is not CartridgeOverflowState or state.cycle != routed.cycle:
                raise WasteFluidAccountingError("overflow trajectory cycle identity does not match routing evidence")
            contractual = max(0.0, routed.cumulative_minimum_cartridge_routing_mL - self.guard.usable_capacity_mL)
            conservative = max(0.0, routed.cumulative_maximum_cartridge_inflow_mL - self.guard.usable_capacity_mL)
            expected = (
                contractual, conservative,
                contractual - previous_contractual,
                conservative - previous_conservative,
            )
            supplied = (
                state.contractual_overflow_mL, state.conservative_overflow_mL,
                state.contractual_increment_mL, state.conservative_increment_mL,
            )
            if any(not math.isclose(float(actual), float(wanted), rel_tol=0.0, abs_tol=_TOL) for actual, wanted in zip(supplied, expected)):
                raise WasteFluidAccountingError("overflow trajectory is stale or inconsistent with routing evidence")
            if contractual + _TOL < previous_contractual or conservative + _TOL < previous_conservative:
                raise WasteFluidAccountingError("cumulative cartridge overflow cannot decrease across service cycles")
            previous_contractual = contractual
            previous_conservative = conservative

        final = self.states[-1]
        if not math.isclose(final.contractual_overflow_mL, self.guard.contractual_end_of_service_overflow_mL, rel_tol=0.0, abs_tol=_TOL):
            raise WasteFluidAccountingError("contractual trajectory does not reconcile with end-of-service overflow")
        if not math.isclose(final.conservative_overflow_mL, self.guard.conservative_end_of_service_overflow_mL, rel_tol=0.0, abs_tol=_TOL):
            raise WasteFluidAccountingError("conservative trajectory does not reconcile with end-of-service overflow")


def build_cartridge_overflow_trajectory(guard: CartridgeOverflowGuard) -> CartridgeOverflowTrajectory:
    """Resolve overflow accumulation at every service cycle without granting sink credit."""
    if type(guard) is not CartridgeOverflowGuard:
        raise WasteFluidAccountingError("overflow trajectory requires exact CartridgeOverflowGuard evidence")

    states: list[CartridgeOverflowState] = []
    previous_contractual = 0.0
    previous_conservative = 0.0
    for routed in guard.routing.cycles:
        contractual = max(0.0, routed.cumulative_minimum_cartridge_routing_mL - guard.usable_capacity_mL)
        conservative = max(0.0, routed.cumulative_maximum_cartridge_inflow_mL - guard.usable_capacity_mL)
        states.append(CartridgeOverflowState(
            cycle=routed.cycle,
            contractual_overflow_mL=contractual,
            conservative_overflow_mL=conservative,
            contractual_increment_mL=contractual - previous_contractual,
            conservative_increment_mL=conservative - previous_conservative,
        ))
        previous_contractual = contractual
        previous_conservative = conservative
    return CartridgeOverflowTrajectory(guard=guard, states=tuple(states))
