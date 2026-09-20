"""Explicit cartridge capacity-reserve composition for waste/fluid integration."""
from __future__ import annotations

import math
from dataclasses import dataclass

from .waste_fluid_accounting import WasteFluidAccountingError, WasteFluidBudget
from .waste_fluid_overflow_guard import CartridgeOverflowGuard, screen_cartridge_overflow_guard


@dataclass(frozen=True, slots=True)
class CartridgeCapacityReserve:
    """Explicit unavailable-volume allowances, supplied by their owning subsystems.

    Values are engineering inputs, not inferred physical performance. Keeping them
    separate prevents foam, sensor trip, tolerance, and other allowances from being
    hidden inside the controlled retained-capacity requirement.
    """

    fill_sensor_trip_mL: float = 0.0
    foam_allowance_mL: float = 0.0
    manufacturing_tolerance_mL: float = 0.0
    other_integration_mL: float = 0.0

    def validate(self) -> None:
        for name, value in (
            ("fill_sensor_trip_mL", self.fill_sensor_trip_mL),
            ("foam_allowance_mL", self.foam_allowance_mL),
            ("manufacturing_tolerance_mL", self.manufacturing_tolerance_mL),
            ("other_integration_mL", self.other_integration_mL),
        ):
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise WasteFluidAccountingError(f"{name} must be a finite numeric value")
            if not math.isfinite(float(value)) or float(value) < 0.0:
                raise WasteFluidAccountingError(f"{name} must be finite and nonnegative")

    @property
    def total_mL(self) -> float:
        self.validate()
        return float(
            self.fill_sensor_trip_mL
            + self.foam_allowance_mL
            + self.manufacturing_tolerance_mL
            + self.other_integration_mL
        )


def screen_cartridge_capacity_reserve(
    budget: WasteFluidBudget,
    reserve: CartridgeCapacityReserve,
    *,
    prime_events_by_cycle: tuple[int, ...] | list[int],
    prime_recovery_ratio_contract: float | None = None,
    prime_residual_ratio_contract: float | None = None,
    prime_external_leakage_ratio_contract: float | None = None,
) -> CartridgeOverflowGuard:
    """Apply an auditable reserve breakdown to the cycle-resolved overflow screen."""
    budget.validate()
    if type(reserve) is not CartridgeCapacityReserve:
        raise WasteFluidAccountingError("reserve must use the exact CartridgeCapacityReserve type")
    reserve.validate()
    if reserve.total_mL >= budget.cartridge_retained_capacity_requirement_mL:
        raise WasteFluidAccountingError(
            "composed capacity reserve must be smaller than cartridge retained-capacity requirement"
        )
    return screen_cartridge_overflow_guard(
        budget,
        prime_events_by_cycle=prime_events_by_cycle,
        prime_recovery_ratio_contract=prime_recovery_ratio_contract,
        prime_residual_ratio_contract=prime_residual_ratio_contract,
        prime_external_leakage_ratio_contract=prime_external_leakage_ratio_contract,
        capacity_reserve_mL=reserve.total_mL,
    )
