from dataclasses import replace

import pytest

from masck_one.thermal_control import ThermalCommandInterlock, ThermalMode
from masck_one.treatment_thermal_handoff import command_thermal_from_reserved_full_treatment_evidence
from masck_one.waste_fluid_accounting import WasteFluidAccountingError, build_authority_waste_fluid_budget
from tests.test_treatment_full_evidence import _full


def test_reserved_full_treatment_boundary_accepts_matching_fluid_authority(built):
    sources, parameters, sweep, full = _full(built, reserved=True)
    command = command_thermal_from_reserved_full_treatment_evidence(
        ThermalCommandInterlock(),
        sweep,
        parameters,
        full,
        **sources,
        budget=build_authority_waste_fluid_budget(),
        warm_requested=False,
        cool_requested=True,
    )
    assert command.mode is ThermalMode.COOL
    assert command.cool_enable


def test_reserved_full_treatment_boundary_rejects_stale_fluid_capacity_authority(built):
    sources, parameters, sweep, full = _full(built, reserved=True)
    current = build_authority_waste_fluid_budget()
    stale = replace(
        current,
        cartridge_retained_capacity_requirement_mL=(
            current.cartridge_retained_capacity_requirement_mL + 1.0
        ),
    )
    with pytest.raises(
        WasteFluidAccountingError,
        match="retained capacity does not match fluid authority",
    ):
        command_thermal_from_reserved_full_treatment_evidence(
            ThermalCommandInterlock(),
            sweep,
            parameters,
            full,
            **sources,
            budget=stale,
            warm_requested=False,
            cool_requested=True,
        )


def test_reserved_full_treatment_boundary_rejects_untyped_fluid_authority(built):
    sources, parameters, sweep, full = _full(built, reserved=True)
    with pytest.raises(
        WasteFluidAccountingError,
        match="requires exact WasteFluidBudget authority",
    ):
        command_thermal_from_reserved_full_treatment_evidence(
            ThermalCommandInterlock(),
            sweep,
            parameters,
            full,
            **sources,
            budget=object(),
            warm_requested=False,
            cool_requested=True,
        )
