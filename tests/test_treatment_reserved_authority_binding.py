import pytest

from masck_one.thermal_control import ThermalCommandInterlock, ThermalMode
from masck_one.treatment_thermal_handoff import command_thermal_from_reserved_full_treatment_evidence
from masck_one.waste_fluid_accounting import WasteFluidAccountingError
from masck_one.waste_fluid_capacity_reserve import CartridgeCapacityReserve
from tests.test_treatment_full_evidence import _full


def test_reserved_full_treatment_accepts_matching_current_reserve_authority(built):
    sources, parameters, sweep, full = _full(built, reserved=True)
    reserve = full.integrated.recovery.source_capacity_reserve_evidence.reserve

    command = command_thermal_from_reserved_full_treatment_evidence(
        ThermalCommandInterlock(),
        sweep,
        parameters,
        full,
        **sources,
        reserve=reserve,
        warm_requested=False,
        cool_requested=True,
    )

    assert command.mode is ThermalMode.COOL
    assert command.cool_enable


def test_reserved_full_treatment_rejects_stale_self_consistent_reserve_evidence(built):
    sources, parameters, sweep, full = _full(built, reserved=True)
    current_reserve = CartridgeCapacityReserve(fill_sensor_trip_mL=0.25)
    captured_reserve = full.integrated.recovery.source_capacity_reserve_evidence.reserve
    assert current_reserve.evidence_sha256 != captured_reserve.evidence_sha256

    with pytest.raises(WasteFluidAccountingError, match="reserve provenance does not match current authority"):
        command_thermal_from_reserved_full_treatment_evidence(
            ThermalCommandInterlock(),
            sweep,
            parameters,
            full,
            **sources,
            reserve=current_reserve,
            warm_requested=False,
            cool_requested=True,
        )


@pytest.mark.parametrize("reserve", [True, object(), 0.0])
def test_reserved_full_treatment_rejects_untyped_current_reserve_authority(built, reserve):
    sources, parameters, sweep, full = _full(built, reserved=True)

    with pytest.raises(WasteFluidAccountingError, match="exact CartridgeCapacityReserve authority"):
        command_thermal_from_reserved_full_treatment_evidence(
            ThermalCommandInterlock(),
            sweep,
            parameters,
            full,
            **sources,
            reserve=reserve,
            warm_requested=False,
            cool_requested=True,
        )
