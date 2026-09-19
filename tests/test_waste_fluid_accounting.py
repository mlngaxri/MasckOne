from dataclasses import replace

import pytest

from masck_one.waste_fluid_accounting import (
    WasteFluidAccountingError,
    build_authority_waste_fluid_budget,
)


def test_authority_budget_reconciles_cycle_and_capacity_screen():
    budget = build_authority_waste_fluid_budget()
    assert budget.nominal_introduced_mL_per_cycle == pytest.approx(4.60)
    assert budget.maximum_liquid_presented_to_recovery_mL_per_cycle == pytest.approx(5.00)
    assert budget.minimum_recovered_mL_per_cycle == pytest.approx(4.14)
    assert budget.residual_free_liquid_max_mL == pytest.approx(0.400)
    assert budget.external_leakage_max_mL_per_cycle == pytest.approx(0.050)
    assert budget.maximum_cartridge_inflow_screen_mL == pytest.approx(30.0)
    assert budget.cartridge_requirement_margin_mL == pytest.approx(5.0)
    assert budget.manifest()["physical_validation_eligible"] is False


def test_capacity_screen_credits_neither_residual_nor_leakage():
    budget = build_authority_waste_fluid_budget()
    changed = replace(
        budget,
        residual_free_liquid_max_mL=0.0,
        external_leakage_max_mL_per_cycle=0.0,
    )
    assert changed.maximum_cartridge_inflow_screen_mL == budget.maximum_cartridge_inflow_screen_mL


def test_seventh_cycle_exhausts_digital_requirement_margin():
    budget = replace(build_authority_waste_fluid_budget(), service_cycles=7)
    budget.validate()
    assert budget.maximum_cartridge_inflow_screen_mL == pytest.approx(35.0)
    assert budget.cartridge_requirement_margin_mL == pytest.approx(0.0)


def test_eighth_cycle_fails_closed_against_capacity_requirement():
    budget = replace(build_authority_waste_fluid_budget(), service_cycles=8)
    with pytest.raises(WasteFluidAccountingError, match="below conservative cycle inflow screen"):
        budget.validate()


def test_invalid_recovery_ratio_fails_closed():
    budget = replace(build_authority_waste_fluid_budget(), recovery_ratio_min=1.01)
    with pytest.raises(WasteFluidAccountingError, match="recovery ratio"):
        budget.validate()


def test_boolean_cycle_count_is_rejected():
    budget = replace(build_authority_waste_fluid_budget(), service_cycles=True)
    with pytest.raises(WasteFluidAccountingError, match="positive integer"):
        budget.validate()
