import pytest

from masck_one.thermal_control import ThermalCommandInterlock
from masck_one.treatment_recovery_readiness import screen_treatment_recovery_readiness
from masck_one.treatment_thermal_handoff import command_thermal_after_treatment
from masck_one.waste_fluid_accounting import WasteFluidAccountingError, build_authority_waste_fluid_budget
from masck_one.waste_fluid_capacity_reserve import (
    CartridgeCapacityReserve,
    screen_cartridge_capacity_reserve_evidence,
)


def _reserved_readiness():
    budget = build_authority_waste_fluid_budget()
    reserve = CartridgeCapacityReserve(manufacturing_tolerance_mL=0.5)
    evidence = screen_cartridge_capacity_reserve_evidence(
        budget,
        reserve,
        prime_events_by_cycle=[0] * budget.service_cycles,
        prime_recovery_ratio_contract=1.0,
    )
    return screen_treatment_recovery_readiness(evidence)


def test_mutated_nested_capacity_guard_cannot_cross_thermal_handoff():
    readiness = _reserved_readiness()
    assert readiness.post_recovery_handoff_permitted
    guard = readiness.source_capacity_guard
    object.__setattr__(guard, "usable_capacity_mL", guard.usable_capacity_mL - 1.0)

    with pytest.raises(WasteFluidAccountingError, match="usable capacity plus reserve"):
        command_thermal_after_treatment(
            ThermalCommandInterlock(), readiness, warm_requested=False, cool_requested=True
        )


def test_mutated_nested_reserve_composition_cannot_cross_thermal_handoff():
    readiness = _reserved_readiness()
    assert readiness.post_recovery_handoff_permitted
    reserve = readiness.source_capacity_reserve_evidence.reserve
    object.__setattr__(reserve, "manufacturing_tolerance_mL", 1.0)

    with pytest.raises(WasteFluidAccountingError, match="reserve total does not match"):
        command_thermal_after_treatment(
            ThermalCommandInterlock(), readiness, warm_requested=False, cool_requested=True
        )
