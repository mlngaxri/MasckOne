"""Cycle-resolved cartridge capacity milestones derived from screened overflow evidence."""
from __future__ import annotations

import math
from dataclasses import dataclass

from .waste_fluid_accounting import WasteFluidAccountingError
from .waste_fluid_overflow_guard import CartridgeOverflowGuard

_TOL = 1e-12


@dataclass(frozen=True)
class CartridgeCapacityMilestone:
    """First service cycle reaching a utilization threshold, including crossing overshoot."""

    utilization_fraction: float
    first_contractual_cycle: int | None
    first_conservative_cycle: int | None
    contractual_crossing_volume_mL: float | None
    conservative_crossing_volume_mL: float | None
    contractual_overshoot_mL: float | None
    conservative_overshoot_mL: float | None

    def __post_init__(self) -> None:
        if (not isinstance(self.utilization_fraction, (int, float)) or isinstance(self.utilization_fraction, bool)
                or not math.isfinite(float(self.utilization_fraction)) or not 0.0 < float(self.utilization_fraction) <= 1.0):
            raise WasteFluidAccountingError("capacity milestone utilization must be finite in (0, 1]")
        for name in ("first_contractual_cycle", "first_conservative_cycle"):
            value = getattr(self, name)
            if value is not None and (type(value) is not int or value < 1):
                raise WasteFluidAccountingError(f"{name} must be a positive integer or None")
        for cycle_name, volume_name, overshoot_name in (
            ("first_contractual_cycle", "contractual_crossing_volume_mL", "contractual_overshoot_mL"),
            ("first_conservative_cycle", "conservative_crossing_volume_mL", "conservative_overshoot_mL"),
        ):
            cycle, volume, overshoot = getattr(self, cycle_name), getattr(self, volume_name), getattr(self, overshoot_name)
            if cycle is None:
                if volume is not None or overshoot is not None:
                    raise WasteFluidAccountingError("unreached capacity milestone cannot carry crossing volume")
            else:
                if any(v is None or type(v) not in (int, float) or not math.isfinite(float(v)) or float(v) < -_TOL for v in (volume, overshoot)):
                    raise WasteFluidAccountingError("reached capacity milestone requires finite nonnegative crossing evidence")
        if self.first_contractual_cycle is not None:
            if self.first_conservative_cycle is None or self.first_contractual_cycle < self.first_conservative_cycle:
                raise WasteFluidAccountingError("contractual capacity milestone cannot precede conservative milestone")


@dataclass(frozen=True)
class CartridgeCapacityMilestones:
    """Fail-closed milestone evidence for approaching cartridge capacity exhaustion."""

    guard: CartridgeOverflowGuard
    milestones: tuple[CartridgeCapacityMilestone, ...]

    def __post_init__(self) -> None:
        if type(self.guard) is not CartridgeOverflowGuard:
            raise WasteFluidAccountingError("capacity milestones require exact CartridgeOverflowGuard evidence")
        if not self.milestones:
            raise WasteFluidAccountingError("capacity milestones require at least one threshold")
        previous_threshold = 0.0
        previous_contractual: int | None = None
        previous_conservative: int | None = None
        for milestone in self.milestones:
            if type(milestone) is not CartridgeCapacityMilestone:
                raise WasteFluidAccountingError("capacity milestones require exact milestone evidence")
            threshold = float(milestone.utilization_fraction)
            if threshold <= previous_threshold + _TOL:
                raise WasteFluidAccountingError("capacity milestone thresholds must be strictly increasing")
            limit = threshold * self.guard.usable_capacity_mL
            contractual_state = next((s for s in self.guard.routing.cycles if s.cumulative_minimum_cartridge_routing_mL + _TOL >= limit), None)
            conservative_state = next((s for s in self.guard.routing.cycles if s.cumulative_maximum_cartridge_inflow_mL + _TOL >= limit), None)
            expected_contractual = None if contractual_state is None else contractual_state.cycle
            expected_conservative = None if conservative_state is None else conservative_state.cycle
            expected_contractual_volume = None if contractual_state is None else contractual_state.cumulative_minimum_cartridge_routing_mL
            expected_conservative_volume = None if conservative_state is None else conservative_state.cumulative_maximum_cartridge_inflow_mL
            expected_contractual_overshoot = None if contractual_state is None else max(0.0, expected_contractual_volume - limit)
            expected_conservative_overshoot = None if conservative_state is None else max(0.0, expected_conservative_volume - limit)
            supplied = (milestone.first_contractual_cycle, milestone.first_conservative_cycle, milestone.contractual_crossing_volume_mL,
                        milestone.conservative_crossing_volume_mL, milestone.contractual_overshoot_mL, milestone.conservative_overshoot_mL)
            expected = (expected_contractual, expected_conservative, expected_contractual_volume, expected_conservative_volume,
                        expected_contractual_overshoot, expected_conservative_overshoot)
            if supplied != expected:
                raise WasteFluidAccountingError("capacity milestone evidence is stale or inconsistent with routing")
            if previous_contractual is not None and expected_contractual is not None and expected_contractual < previous_contractual:
                raise WasteFluidAccountingError("higher contractual capacity threshold cannot be reached earlier")
            if previous_conservative is not None and expected_conservative is not None and expected_conservative < previous_conservative:
                raise WasteFluidAccountingError("higher conservative capacity threshold cannot be reached earlier")
            previous_threshold = threshold
            if expected_contractual is not None:
                previous_contractual = expected_contractual
            if expected_conservative is not None:
                previous_conservative = expected_conservative

        full = next((m for m in self.milestones if math.isclose(m.utilization_fraction, 1.0, rel_tol=0.0, abs_tol=_TOL)), None)
        if full is not None:
            if self.guard.first_unavoidable_overflow_cycle is not None:
                if full.first_contractual_cycle is None or self.guard.first_unavoidable_overflow_cycle < full.first_contractual_cycle:
                    raise WasteFluidAccountingError("contractual overflow precedes full-capacity milestone")
            if self.guard.first_conservative_capacity_failure_cycle is not None:
                if full.first_conservative_cycle is None or self.guard.first_conservative_capacity_failure_cycle < full.first_conservative_cycle:
                    raise WasteFluidAccountingError("conservative overflow precedes full-capacity milestone")


def screen_cartridge_capacity_milestones(guard: CartridgeOverflowGuard, *, utilization_fractions: tuple[float, ...] = (0.80, 0.90, 1.0)) -> CartridgeCapacityMilestones:
    """Resolve the first cycle reaching each requested capacity fraction and its overshoot."""
    if type(guard) is not CartridgeOverflowGuard:
        raise WasteFluidAccountingError("capacity milestones require exact CartridgeOverflowGuard evidence")
    if not utilization_fractions:
        raise WasteFluidAccountingError("capacity milestones require at least one threshold")
    milestones: list[CartridgeCapacityMilestone] = []
    for raw_threshold in utilization_fractions:
        if (not isinstance(raw_threshold, (int, float)) or isinstance(raw_threshold, bool)
                or not math.isfinite(float(raw_threshold)) or not 0.0 < float(raw_threshold) <= 1.0):
            raise WasteFluidAccountingError("capacity milestone utilization must be finite in (0, 1]")
        threshold = float(raw_threshold)
        limit = threshold * guard.usable_capacity_mL
        contractual_state = next((s for s in guard.routing.cycles if s.cumulative_minimum_cartridge_routing_mL + _TOL >= limit), None)
        conservative_state = next((s for s in guard.routing.cycles if s.cumulative_maximum_cartridge_inflow_mL + _TOL >= limit), None)
        contractual_volume = None if contractual_state is None else contractual_state.cumulative_minimum_cartridge_routing_mL
        conservative_volume = None if conservative_state is None else conservative_state.cumulative_maximum_cartridge_inflow_mL
        milestones.append(CartridgeCapacityMilestone(
            utilization_fraction=threshold,
            first_contractual_cycle=None if contractual_state is None else contractual_state.cycle,
            first_conservative_cycle=None if conservative_state is None else conservative_state.cycle,
            contractual_crossing_volume_mL=contractual_volume,
            conservative_crossing_volume_mL=conservative_volume,
            contractual_overshoot_mL=None if contractual_volume is None else max(0.0, contractual_volume - limit),
            conservative_overshoot_mL=None if conservative_volume is None else max(0.0, conservative_volume - limit),
        ))
    return CartridgeCapacityMilestones(guard=guard, milestones=tuple(milestones))
