"""Discrete cycle windows around cartridge capacity milestones.

This keeps capacity evidence exact at cycle resolution. It does not infer a
within-cycle crossing time or assume uniform flow.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

from .waste_fluid_accounting import WasteFluidAccountingError
from .waste_fluid_capacity_milestones import CartridgeCapacityMilestones

_TOL = 1e-12


@dataclass(frozen=True)
class CapacityCrossingWindow:
    utilization_fraction: float
    path: str
    cycle: int
    threshold_volume_mL: float
    volume_before_cycle_mL: float
    cycle_increment_mL: float
    crossing_volume_mL: float
    headroom_before_cycle_mL: float
    overshoot_after_cycle_mL: float

    def __post_init__(self) -> None:
        if self.path not in ("contractual", "conservative"):
            raise WasteFluidAccountingError("capacity crossing path must be contractual or conservative")
        if type(self.cycle) is not int or self.cycle < 1:
            raise WasteFluidAccountingError("capacity crossing cycle must be a positive integer")
        values = (
            self.utilization_fraction, self.threshold_volume_mL,
            self.volume_before_cycle_mL, self.cycle_increment_mL,
            self.crossing_volume_mL, self.headroom_before_cycle_mL,
            self.overshoot_after_cycle_mL,
        )
        if any(type(value) not in (int, float) or not math.isfinite(float(value)) for value in values):
            raise WasteFluidAccountingError("capacity crossing evidence must be finite numeric data")
        if not 0.0 < self.utilization_fraction <= 1.0:
            raise WasteFluidAccountingError("capacity crossing utilization must be in (0, 1]")
        if min(self.threshold_volume_mL, self.volume_before_cycle_mL, self.cycle_increment_mL,
               self.crossing_volume_mL, self.headroom_before_cycle_mL, self.overshoot_after_cycle_mL) < -_TOL:
            raise WasteFluidAccountingError("capacity crossing volumes cannot be negative")
        if self.volume_before_cycle_mL + self.cycle_increment_mL != self.crossing_volume_mL:
            raise WasteFluidAccountingError("capacity crossing increment does not conserve cartridge volume")
        if self.threshold_volume_mL - self.volume_before_cycle_mL != self.headroom_before_cycle_mL:
            raise WasteFluidAccountingError("capacity crossing pre-cycle headroom is inconsistent")
        if self.crossing_volume_mL - self.threshold_volume_mL != self.overshoot_after_cycle_mL:
            raise WasteFluidAccountingError("capacity crossing overshoot is inconsistent")
        if self.headroom_before_cycle_mL <= _TOL:
            raise WasteFluidAccountingError("capacity crossing cycle must begin below its threshold")
        if self.overshoot_after_cycle_mL < -_TOL:
            raise WasteFluidAccountingError("capacity crossing cycle must end at or above its threshold")
        if self.headroom_before_cycle_mL - self.cycle_increment_mL > _TOL:
            raise WasteFluidAccountingError("capacity crossing increment cannot reach the threshold")


@dataclass(frozen=True)
class CartridgeCapacityCrossings:
    source: CartridgeCapacityMilestones
    windows: tuple[CapacityCrossingWindow, ...]

    def __post_init__(self) -> None:
        if type(self.source) is not CartridgeCapacityMilestones:
            raise WasteFluidAccountingError("capacity crossings require exact milestone evidence")
        expected = _build_windows(self.source)
        if self.windows != expected:
            raise WasteFluidAccountingError("capacity crossing evidence is stale or inconsistent with routing")


def _build_windows(source: CartridgeCapacityMilestones) -> tuple[CapacityCrossingWindow, ...]:
    cycles = source.guard.routing.cycles
    usable = source.guard.usable_capacity_mL
    windows: list[CapacityCrossingWindow] = []
    for milestone in source.milestones:
        threshold = milestone.utilization_fraction * usable
        for path, cycle, crossing in (
            ("contractual", milestone.first_contractual_cycle, milestone.contractual_crossing_volume_mL),
            ("conservative", milestone.first_conservative_cycle, milestone.conservative_crossing_volume_mL),
        ):
            if cycle is None:
                continue
            if crossing is None or cycle > len(cycles):
                raise WasteFluidAccountingError("reached capacity milestone lost cycle routing evidence")
            field = ("cumulative_minimum_cartridge_routing_mL" if path == "contractual"
                     else "cumulative_maximum_cartridge_inflow_mL")
            before = 0.0 if cycle == 1 else float(getattr(cycles[cycle - 2], field))
            after = float(getattr(cycles[cycle - 1], field))
            if not math.isclose(after, float(crossing), rel_tol=0.0, abs_tol=_TOL):
                raise WasteFluidAccountingError("capacity crossing volume disagrees with cycle routing")
            increment = after - before
            if increment < -_TOL:
                raise WasteFluidAccountingError("cartridge cumulative routing cannot decrease across a crossing cycle")
            windows.append(CapacityCrossingWindow(
                utilization_fraction=milestone.utilization_fraction,
                path=path,
                cycle=cycle,
                threshold_volume_mL=threshold,
                volume_before_cycle_mL=before,
                cycle_increment_mL=increment,
                crossing_volume_mL=after,
                headroom_before_cycle_mL=threshold - before,
                overshoot_after_cycle_mL=after - threshold,
            ))
    return tuple(windows)


def quantify_cartridge_capacity_crossings(source: CartridgeCapacityMilestones) -> CartridgeCapacityCrossings:
    """Quantify exact pre/post threshold margins for every reached milestone."""
    if type(source) is not CartridgeCapacityMilestones:
        raise WasteFluidAccountingError("capacity crossings require exact milestone evidence")
    return CartridgeCapacityCrossings(source=source, windows=_build_windows(source))
