from dataclasses import replace

import pytest

from masck_one.waste_fluid_accounting import (
    WasteFluidAccountingError,
    build_authority_waste_fluid_budget,
)
from masck_one.waste_fluid_overflow_authority import validate_overflow_guard_authority
from masck_one.waste_fluid_overflow_guard import screen_cartridge_overflow_guard


def _guard(budget=None):
    budget = budget or build_authority_waste_fluid_budget()
    return screen_cartridge_overflow_guard(
        budget,
        prime_events_by_cycle=[1] * 6,
        prime_recovery_ratio_contract=0.90,
        prime_residual_ratio_contract=0.08,
        prime_external_leakage_ratio_contract=0.02,
    )


def test_authority_guard_binds_to_budget():
    budget = build_authority_waste_fluid_budget()
    guard = _guard(budget)
    validate_overflow_guard_authority(budget, guard)


def test_rejects_internally_valid_guard_from_different_capacity_authority():
    budget = build_authority_waste_fluid_budget()
    alternate = replace(budget, cartridge_retained_capacity_requirement_mL=36.0)
    guard = _guard(alternate)
    with pytest.raises(WasteFluidAccountingError, match="retained capacity"):
        validate_overflow_guard_authority(budget, guard)


def test_rejects_internally_valid_guard_from_different_delivery_authority():
    budget = build_authority_waste_fluid_budget()
    alternate = replace(
        budget,
        nominal_introduced_mL_per_cycle=4.5,
        recovery_ratio_min=0.90,
    )
    guard = screen_cartridge_overflow_guard(
        alternate,
        prime_events_by_cycle=[1] * 6,
        prime_recovery_ratio_contract=0.90,
        prime_residual_ratio_contract=0.08,
        prime_external_leakage_ratio_contract=0.02,
    )
    with pytest.raises(WasteFluidAccountingError, match="inflow trajectory"):
        validate_overflow_guard_authority(budget, guard)


def test_rejects_wrong_evidence_types():
    budget = build_authority_waste_fluid_budget()
    guard = _guard(budget)
    with pytest.raises(WasteFluidAccountingError):
        validate_overflow_guard_authority(object(), guard)
    with pytest.raises(WasteFluidAccountingError):
        validate_overflow_guard_authority(budget, object())
