from dataclasses import replace

import pytest

from masck_one.waste_fluid_accounting import WasteFluidAccountingError, build_authority_waste_fluid_budget
from masck_one.waste_fluid_capacity_reserve import CartridgeCapacityReserve, screen_cartridge_capacity_reserve_evidence
from masck_one.waste_fluid_reserved_overflow_authority import validate_capacity_reserved_overflow_authority


def _evidence(budget=None):
    budget = budget or build_authority_waste_fluid_budget()
    return screen_cartridge_capacity_reserve_evidence(
        budget,
        CartridgeCapacityReserve(fill_sensor_trip_mL=1.0, foam_allowance_mL=1.0),
        prime_events_by_cycle=[1] * budget.service_cycles,
        prime_recovery_ratio_contract=0.90,
        prime_residual_ratio_contract=0.08,
        prime_external_leakage_ratio_contract=0.02,
    )


def test_reserved_overflow_evidence_binds_to_current_fluid_authority():
    budget = build_authority_waste_fluid_budget()
    validate_capacity_reserved_overflow_authority(budget, _evidence(budget))


def test_rejects_reserved_overflow_evidence_from_different_fluid_authority():
    budget = build_authority_waste_fluid_budget()
    alternate = replace(budget, recovery_ratio_min=0.95)
    with pytest.raises(WasteFluidAccountingError, match="service routing|cycle routing|nominal recovery"):
        validate_capacity_reserved_overflow_authority(budget, _evidence(alternate))
